import hashlib
import json
import math
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
WGS84_COORDINATE_REFERENCE_SYSTEM = "EPSG:4326"


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

# Return the only CRS currently safe for browser GPS guidance
def normalise_coordinate_reference_system(value):
    coordinate_reference_system = str(value or "").strip().upper().replace(" ", "")
    aliases = {"EPSG:4326", "WGS84", "WGS-84"}
    if coordinate_reference_system not in aliases:
        raise SurveyPlanUploadError(
            "Live boundary guidance currently requires WGS84 longitude/latitude coordinates (EPSG:4326). "
            "Convert Minna/NTM or UTM coordinates with a licensed surveyor before submitting them."
        )
    return WGS84_COORDINATE_REFERENCE_SYSTEM


def _orientation(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _segments_intersect(a, b, c, d):
    first = _orientation(a, b, c)
    second = _orientation(a, b, d)
    third = _orientation(c, d, a)
    fourth = _orientation(c, d, b)
    return first * second < 0 and third * fourth < 0

# Validate a simple WGS84 polygon supplied as longitude, latitude pairs
def validate_boundary_coordinates(value, coordinate_reference_system):
    if value in (None, ""):
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as error:
            raise SurveyPlanUploadError(
                "Boundary coordinates must be a JSON list of [x, y] pairs."
            ) from error
    if not isinstance(value, list) or not (3 <= len(value) <= 1000):
        raise SurveyPlanUploadError("Provide between 3 and 1,000 boundary coordinate pairs.")
    normalise_coordinate_reference_system(coordinate_reference_system)
    coordinates = []
    for point in value:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise SurveyPlanUploadError("Each boundary coordinate must be an [x, y] pair.")
        try:
            x, y = float(point[0]), float(point[1])
        except (TypeError, ValueError) as error:
            raise SurveyPlanUploadError("Boundary coordinates must be numbers.") from error
        if not math.isfinite(x) or not math.isfinite(y):
            raise SurveyPlanUploadError("Boundary coordinates must be finite numbers.")
        if not (-180 <= x <= 180 and -90 <= y <= 90):
            raise SurveyPlanUploadError("WGS84 coordinates must use longitude from -180 to 180 and latitude from -90 to 90.")
        coordinates.append([x, y])
    if coordinates[0] == coordinates[-1]:
        coordinates.pop()
    if len({tuple(point) for point in coordinates}) < 3:
        raise SurveyPlanUploadError("A boundary needs at least three different coordinate pairs.")
    signed_area = sum(
        coordinates[index][0] * coordinates[(index + 1) % len(coordinates)][1]
        - coordinates[(index + 1) % len(coordinates)][0] * coordinates[index][1]
        for index in range(len(coordinates))
    )
    if abs(signed_area) < 1e-12:
        raise SurveyPlanUploadError("Boundary coordinates must form an area, not a straight line.")
    for index, start in enumerate(coordinates):
        end = coordinates[(index + 1) % len(coordinates)]
        for other_index in range(index + 1, len(coordinates)):
            if abs(index - other_index) in (0, 1) or {index, other_index} == {0, len(coordinates) - 1}:
                continue
            other_start = coordinates[other_index]
            other_end = coordinates[(other_index + 1) % len(coordinates)]
            if _segments_intersect(start, end, other_start, other_end):
                raise SurveyPlanUploadError("Boundary sides must not cross each other.")
    return coordinates


def create_survey_plan(*, company, allocation_id, uploaded_file, metadata, user, recipient=None):
    filename, checksum = validate_survey_plan_upload(uploaded_file)
    values = validate_survey_plan_metadata(metadata)
    submitted_boundary_coordinates = validate_boundary_coordinates(
        metadata.get("boundary_coordinates"),
        values["coordinate_reference_system"],
    ) if metadata.get("boundary_coordinates") not in (None, "") else []
    plan = None
    try:
        with transaction.atomic():
            allocation_query = Allocation.objects.select_for_update().select_related(
                "parcel__estate__company"
            ).filter(pk=allocation_id, parcel__estate__company=company)
            if recipient is not None:
                allocation_query = allocation_query.filter(
                    allottee=recipient,
                    status=Allocation.Status.ACTIVE,
                )
            allocation = allocation_query.first()
            if not allocation:
                message = (
                    "You can only upload a survey plan for an active property linked to your account."
                    if recipient is not None else "Choose an allocation belonging to this company."
                )
                raise SurveyPlanUploadError(message)
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
                    "message": "Automated survey-plan OCR is not configured; metadata was supplied with the upload.",
                },
                submitted_boundary_coordinates=submitted_boundary_coordinates,
                **values,
            )
            plan.full_clean(exclude=("document",))
            plan.document = uploaded_file
            plan.save()
            if submitted_boundary_coordinates:
                allocation.parcel.boundary_coordinates = submitted_boundary_coordinates
                allocation.parcel.boundary_coordinate_reference_system = WGS84_COORDINATE_REFERENCE_SYSTEM
                allocation.parcel.perimeter_m = None
                allocation.parcel.save(update_fields=(
                    "boundary_coordinates", "boundary_coordinate_reference_system", "perimeter_m", "updated_at",
                ))
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
