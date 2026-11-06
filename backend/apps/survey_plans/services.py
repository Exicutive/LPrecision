import hashlib
import os
from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.allocations.models import Allocation
from apps.survey_plans.models import SurveyPlan, SurveyPlanVerificationEvent


MAX_SURVEY_PLAN_BYTES = 25 * 1024 * 1024
ALLOWED_SURVEY_PLAN_EXTENSION = ".pdf"


class SurveyPlanUploadError(ValueError):
    pass


def _clean_filename(upload):
    filename = os.path.basename((upload.name or "").replace("\\", "/")).strip()
    if not filename or len(filename) > 255:
        raise SurveyPlanUploadError("Choose a valid survey plan PDF with a filename under 256 characters.")
    return filename


def validate_survey_plan_upload(upload):
    if not upload:
        raise SurveyPlanUploadError("Choose a survey plan PDF to upload.")
    filename = _clean_filename(upload)
    if os.path.splitext(filename)[1].lower() != ALLOWED_SURVEY_PLAN_EXTENSION:
        raise SurveyPlanUploadError("Survey plan documents must be PDF files.")
    if not upload.size or upload.size > MAX_SURVEY_PLAN_BYTES:
        raise SurveyPlanUploadError("Survey plan PDFs must be between 1 byte and 25 MB.")

    digest = hashlib.sha256()
    first_bytes = b""
    for chunk in upload.chunks():
        if len(first_bytes) < 1024:
            first_bytes += chunk[: 1024 - len(first_bytes)]
        digest.update(chunk)
    upload.seek(0)
    if b"%PDF-" not in first_bytes:
        raise SurveyPlanUploadError("The uploaded file does not contain a valid PDF signature.")
    return filename, digest.hexdigest()


def validate_survey_plan_metadata(payload):
    fields = {
        "survey_plan_number": ("Survey plan number", 100),
        "surveyor_full_name": ("Surveyor's full name", 200),
        "surveyor_registration_number": ("Surveyor's registration number", 100),
        "state": ("State", 100),
        "local_government_area": ("LGA", 100),
        "coordinate_reference_system": ("Coordinate reference system", 150),
        "datum": ("Datum", 100),
    }
    values = {}
    for key, (label, max_length) in fields.items():
        value = str(payload.get(key, "")).strip()
        if len(value) > max_length:
            raise SurveyPlanUploadError(f"{label} must be {max_length} characters or fewer.")
        values[key] = value
    for key, label in (
        ("survey_plan_number", "Survey plan number"),
        ("surveyor_full_name", "Surveyor's full name"),
    ):
        if not values[key]:
            raise SurveyPlanUploadError(f"{label} is required.")

    survey_date_value = str(payload.get("survey_date", "")).strip()
    try:
        values["survey_date"] = date.fromisoformat(survey_date_value)
    except ValueError as error:
        raise SurveyPlanUploadError("Enter a valid survey date.") from error

    try:
        area = Decimal(str(payload.get("stated_area", "")).strip())
    except (InvalidOperation, ValueError) as error:
        raise SurveyPlanUploadError("Enter a valid land area greater than zero.") from error
    if not area.is_finite() or area <= 0:
        raise SurveyPlanUploadError("Land area must be a finite number greater than zero.")
    if len(area.as_tuple().digits) > 18 or max(0, -area.as_tuple().exponent) > 4:
        raise SurveyPlanUploadError("Land area supports up to 14 whole digits and 4 decimal places.")
    values["stated_area"] = area

    unit = str(payload.get("area_unit", "")).strip()
    if unit not in SurveyPlan.AreaUnit.values:
        raise SurveyPlanUploadError("Choose a supported land area unit.")
    values["area_unit"] = unit

    for key, max_length, label in (
        ("location_description", 2000, "Location description"),
        ("notes", 4000, "Additional notes"),
    ):
        value = str(payload.get(key, "")).strip()
        if len(value) > max_length:
            raise SurveyPlanUploadError(f"{label} must be {max_length} characters or fewer.")
        values[key] = value
    return values


def create_survey_plan(*, company, allocation_id, uploaded_file, metadata, user):
    filename, checksum = validate_survey_plan_upload(uploaded_file)
    values = validate_survey_plan_metadata(metadata)
    plan = None
    try:
        with transaction.atomic():
            allocation = (
                Allocation.objects.select_for_update()
                .select_related("parcel__estate__company")
                .filter(
                    pk=allocation_id,
                    parcel__estate__company=company,
                )
                .first()
            )
            if not allocation:
                raise SurveyPlanUploadError("Choose an allocation belonging to this company.")
            if allocation.status == Allocation.Status.REVOKED:
                raise SurveyPlanUploadError("A survey plan cannot be uploaded for a revoked allocation.")

            existing = SurveyPlan.objects.filter(
                allocation=allocation,
                checksum=checksum,
            ).first()
            if existing:
                return existing, False

            if SurveyPlan.objects.filter(
                company=company,
                survey_plan_number=values["survey_plan_number"],
            ).exists():
                raise SurveyPlanUploadError("That survey plan number is already recorded for this company.")

            plan = SurveyPlan(
                company=company,
                estate=allocation.parcel.estate,
                parcel=allocation.parcel,
                allocation=allocation,
                name=values["survey_plan_number"],
                reference=values["survey_plan_number"],
                uploaded_by=user,
                original_filename=filename,
                file_format="application/pdf",
                file_size=uploaded_file.size,
                checksum=checksum,
                extracted_metadata={
                    "status": "manual_required",
                    "message": "Automated survey-plan OCR is not configured; metadata must be entered and reviewed manually.",
                },
                **values,
            )
            plan.full_clean(exclude=("document",))
            plan.document = uploaded_file
            plan.save()
            return plan, True
    except IntegrityError as error:
        if plan and plan.document:
            plan.document.delete(save=False)
        if SurveyPlan.objects.filter(company=company, survey_plan_number=values["survey_plan_number"]).exists():
            raise SurveyPlanUploadError("That survey plan number is already recorded for this company.") from error
        existing = SurveyPlan.objects.filter(
            allocation_id=allocation_id,
            checksum=checksum,
        ).first()
        if existing:
            return existing, False
        raise
    except Exception:
        if plan and plan.document:
            plan.document.delete(save=False)
        raise


def record_verification_change(*, plan, status, notes, actor):
    with transaction.atomic():
        plan = SurveyPlan.objects.select_for_update().get(pk=plan.pk)
        previous_status = plan.verification_status
        now = timezone.now()
        plan.verification_status = status
        plan.verification_notes = notes
        plan.verified_by = actor if status == SurveyPlan.VerificationStatus.VERIFIED else None
        plan.verified_at = now if status == SurveyPlan.VerificationStatus.VERIFIED else None
        plan.save(update_fields=(
            "verification_status",
            "verification_notes",
            "verified_by",
            "verified_at",
            "updated_at",
        ))
        SurveyPlanVerificationEvent.objects.create(
            survey_plan=plan,
            actor=actor,
            previous_status=previous_status,
            new_status=status,
            notes=notes,
        )
    return plan
