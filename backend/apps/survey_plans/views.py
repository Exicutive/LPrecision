import json
import hashlib
import os
import secrets
import uuid
from decimal import Decimal, InvalidOperation
from datetime import timedelta

from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.core.mail import send_mail
from django.db import IntegrityError, models, transaction
from django.http import FileResponse, JsonResponse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from apps.allocations.models import Allocation, AllocationInvitation, PropertyInvitation
from apps.companies.models import Company, CompanyAdminInvitation, CompanyMembership
from apps.estates.models import Estate
from apps.master_layouts.models import (
    EstateMasterPlan,
    ExtractedParcelCandidate,
    MasterLayoutProcessingJob,
)
from apps.parcels.models import Parcel
from apps.platform_admin.models import PlatformAuditEvent, PlatformSetting
from apps.survey_plans.models import SurveyPlan
from apps.allocations.services import (
    create_allocation_invitation,
    schedule_allocation_invitation_delivery,
)
from apps.companies.notifications import (
    NOTIFICATION_TYPES,
    schedule_company_notification,
)
from apps.platform_admin.permissions import (
    company_admin_required,
    is_platform_admin,
    log_event,
    platform_admin_required,
)
from apps.master_layouts.services import (
    LayoutUploadError, MasterLayoutProcessingService, MasterLayoutUploadService, ParcelGenerationService,
)
from apps.survey_plans.services import (
    SurveyPlanUploadError,
    create_survey_plan,
    record_verification_change,
    validate_survey_plan_metadata,
)
from apps.accounts.models import VerifiedEmail


User = get_user_model()


from apps.records.api_helpers import (
    _payload,
    _company_ids_for_user,
    _company_data,
    _estate_data,
    _estate_code,
    _estate_values,
    _company_estate,
    _parcel_data,
    _master_plan_data,
    _layout_job_data,
    _survey_plan_data,
    _candidate_data,
    _allocation_data,
    _admin_membership_data,
    _invitation_data,
    _company_master_plan,
    _invitation_request_rate_limited,
)


@require_http_methods(["GET", "POST"])
@login_required
def company_survey_plans(request, company_id):
    membership = company_admin_required(request, company_id)
    if not membership:
        return JsonResponse({"detail": "Company administrator access is required for this company."}, status=403)
    company = membership.company
    if request.method == "GET":
        plans = company.survey_plans.select_related(
            "estate", "parcel", "allocation", "allocation__allottee", "uploaded_by"
        )
        status_filter = request.GET.get("status", "").strip()
        estate_filter = request.GET.get("estate", "").strip()
        block_filter = request.GET.get("block", "").strip()
        date_filter = request.GET.get("survey_date", "").strip()
        search = request.GET.get("search", "").strip()
        if status_filter in SurveyPlan.VerificationStatus.values:
            plans = plans.filter(verification_status=status_filter)
        if estate_filter.isdigit():
            plans = plans.filter(estate_id=int(estate_filter))
        if block_filter:
            plans = plans.filter(parcel__block__icontains=block_filter)
        if date_filter:
            plans = plans.filter(survey_date=date_filter)
        if search:
            plans = plans.filter(
                models.Q(survey_plan_number__icontains=search)
                | models.Q(parcel__plot_number__icontains=search)
                | models.Q(allocation__recipient_name__icontains=search)
                | models.Q(surveyor_full_name__icontains=search)
            )
        all_plans = company.survey_plans.all()
        summary = {
            "total": all_plans.count(),
            "pending": all_plans.filter(
                verification_status=SurveyPlan.VerificationStatus.PENDING
            ).count(),
            "verified": all_plans.filter(
                verification_status=SurveyPlan.VerificationStatus.VERIFIED
            ).count(),
            "disputed": all_plans.filter(
                verification_status=SurveyPlan.VerificationStatus.DISPUTED
            ).count(),
        }
        return JsonResponse({
            "survey_plans": [_survey_plan_data(plan) for plan in plans],
            "summary": summary,
        })

    allocation_id = request.POST.get("allocation_id", "").strip()
    if not allocation_id.isdigit():
        return JsonResponse({"detail": "Select an allocation for this survey plan."}, status=400)
    try:
        plan, created = create_survey_plan(
            company=company,
            allocation_id=int(allocation_id),
            uploaded_file=request.FILES.get("document"),
            metadata=request.POST,
            user=request.user,
        )
    except SurveyPlanUploadError as error:
        return JsonResponse({"detail": str(error)}, status=400)
    except ValidationError as error:
        return JsonResponse({"detail": "; ".join(error.messages)}, status=400)
    if created:
        log_event(
            actor=request.user,
            action="survey_plan.uploaded",
            company=company,
            details={
                "survey_plan_id": str(plan.pk),
                "allocation_id": plan.allocation_id,
                "parcel_id": plan.parcel_id,
                "checksum": plan.checksum,
            },
        )
        schedule_company_notification(
            company_id=company.pk,
            notification_type="survey_plan_upload",
            subject=f"Survey plan uploaded — {plan.survey_plan_number or plan.name}",
            message=(
                f"{request.user.get_full_name() or request.user.email} uploaded survey plan "
                f"{plan.survey_plan_number or plan.name} for {plan.parcel.plot_number} "
                f"in {plan.estate.name}."
            ),
        )
    return JsonResponse(
        {"survey_plan": _survey_plan_data(plan, include_internal=True), "duplicate": not created},
        status=201 if created else 200,
    )

@require_http_methods(["GET", "PATCH"])
@login_required
def company_survey_plan_detail(request, company_id, survey_plan_id):
    membership = company_admin_required(request, company_id)
    if not membership:
        return JsonResponse({"detail": "Company administrator access is required for this company."}, status=403)
    plan = SurveyPlan.objects.select_related(
        "company", "estate", "parcel", "allocation", "uploaded_by", "verified_by"
    ).filter(company=membership.company, pk=survey_plan_id).first()
    if not plan:
        return JsonResponse({"detail": "Survey plan not found."}, status=404)
    if request.method == "GET":
        return JsonResponse({"survey_plan": _survey_plan_data(plan, include_internal=True)})

    payload = _payload(request)
    if payload is None:
        return JsonResponse({"detail": "Send a valid JSON request."}, status=400)
    current = {
        "survey_plan_number": plan.survey_plan_number,
        "surveyor_full_name": plan.surveyor_full_name,
        "surveyor_registration_number": plan.surveyor_registration_number,
        "survey_date": plan.survey_date.isoformat() if plan.survey_date else "",
        "stated_area": str(plan.stated_area or ""),
        "area_unit": plan.area_unit,
        "state": plan.state,
        "local_government_area": plan.local_government_area,
        "location_description": plan.location_description,
        "coordinate_reference_system": plan.coordinate_reference_system,
        "datum": plan.datum,
        "notes": plan.notes,
    }
    current.update(payload)
    try:
        values = validate_survey_plan_metadata(current)
        plan.survey_plan_number = values["survey_plan_number"]
        plan.name = values["survey_plan_number"]
        plan.reference = values["survey_plan_number"]
        for key in (
            "surveyor_full_name", "surveyor_registration_number", "survey_date", "stated_area",
            "area_unit", "state", "local_government_area", "location_description",
            "coordinate_reference_system", "datum", "notes",
        ):
            setattr(plan, key, values[key])
        plan.full_clean(exclude=("document",))
        plan.save()
    except (SurveyPlanUploadError, ValidationError) as error:
        messages = error.messages if isinstance(error, ValidationError) else [str(error)]
        return JsonResponse({"detail": "; ".join(messages)}, status=400)
    except IntegrityError:
        return JsonResponse({"detail": "That survey plan number is already recorded for this company."}, status=400)
    log_event(
        actor=request.user,
        action="survey_plan.metadata_updated",
        company=membership.company,
        details={"survey_plan_id": str(plan.pk)},
    )
    return JsonResponse({"survey_plan": _survey_plan_data(plan, include_internal=True)})

@require_POST
@login_required
def company_survey_plan_verify(request, company_id, survey_plan_id):
    membership = company_admin_required(request, company_id)
    if not membership:
        return JsonResponse({"detail": "Company administrator access is required for this company."}, status=403)
    plan = SurveyPlan.objects.filter(company=membership.company, pk=survey_plan_id).first()
    if not plan:
        return JsonResponse({"detail": "Survey plan not found."}, status=404)
    payload = _payload(request)
    if payload is None:
        return JsonResponse({"detail": "Send a valid JSON request."}, status=400)
    status = str(payload.get("status", "")).strip()
    allowed_statuses = {
        SurveyPlan.VerificationStatus.PENDING,
        SurveyPlan.VerificationStatus.UNDER_REVIEW,
        SurveyPlan.VerificationStatus.VERIFIED,
        SurveyPlan.VerificationStatus.REJECTED,
        SurveyPlan.VerificationStatus.DISPUTED,
    }
    notes = str(payload.get("notes", "")).strip()
    if status not in allowed_statuses or len(notes) > 4000:
        return JsonResponse({"detail": "Choose a valid verification status and provide notes under 4,000 characters."}, status=400)
    previous_status = plan.verification_status
    plan = record_verification_change(
        plan=plan,
        status=status,
        notes=notes,
        actor=request.user,
    )
    if previous_status != status:
        schedule_company_notification(
            company_id=membership.company_id,
            notification_type="survey_plan_verification",
            subject=f"Survey plan {status.replace('_', ' ')} — {plan.survey_plan_number or plan.name}",
            message=(
                f"{request.user.get_full_name() or request.user.email} changed survey plan "
                f"{plan.survey_plan_number or plan.name} for "
                f"{plan.parcel.plot_number if plan.parcel else 'an estate-level plan'} "
                f"in {plan.estate.name} to {status.replace('_', ' ')}."
            ),
        )
    log_event(
        actor=request.user,
        action=f"survey_plan.{status}",
        company=membership.company,
        details={"survey_plan_id": str(plan.pk), "notes": notes},
    )
    return JsonResponse({"survey_plan": _survey_plan_data(plan, include_internal=True)})

@require_GET
@login_required
def company_survey_plan_download(request, company_id, survey_plan_id):
    membership = company_admin_required(request, company_id)
    if not membership:
        return JsonResponse({"detail": "Company administrator access is required for this company."}, status=403)
    plan = SurveyPlan.objects.filter(company=membership.company, pk=survey_plan_id).first()
    if not plan or not plan.document:
        return JsonResponse({"detail": "Survey plan document not found."}, status=404)
    inline = request.GET.get("inline") == "1" and plan.file_format == "application/pdf"
    response = FileResponse(
        plan.document.open("rb"),
        as_attachment=not inline,
        filename=plan.original_filename or f"survey-plan-{plan.pk}.pdf",
        content_type=plan.file_format if inline else "application/octet-stream",
    )
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    if inline:
        response["Content-Security-Policy"] = "sandbox; default-src 'none'"
    return response

@require_GET
@login_required
def recipient_survey_plan_detail(request, allocation_id, survey_plan_id):
    plan = SurveyPlan.objects.select_related(
        "allocation", "parcel", "estate", "uploaded_by", "verified_by"
    ).filter(
        pk=survey_plan_id,
        allocation_id=allocation_id,
        allocation__allottee=request.user,
        allocation__status=Allocation.Status.ACTIVE,
    ).first()
    if not plan:
        return JsonResponse({"detail": "Survey plan not found."}, status=404)
    data = _survey_plan_data(plan)
    data["download_path"] = (
        f"my-property/{allocation_id}/survey-plans/{plan.pk}/download"
        if plan.document else None
    )
    return JsonResponse({"survey_plan": data})

@require_GET
@login_required
def recipient_survey_plan_download(request, allocation_id, survey_plan_id):
    plan = SurveyPlan.objects.filter(
        pk=survey_plan_id,
        allocation_id=allocation_id,
        allocation__allottee=request.user,
        allocation__status=Allocation.Status.ACTIVE,
    ).first()
    if not plan or not plan.document:
        return JsonResponse({"detail": "Survey plan document not found."}, status=404)
    inline = request.GET.get("inline") == "1" and plan.file_format == "application/pdf"
    response = FileResponse(
        plan.document.open("rb"),
        as_attachment=not inline,
        filename=plan.original_filename or f"survey-plan-{plan.pk}.pdf",
        content_type=plan.file_format if inline else "application/octet-stream",
    )
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    if inline:
        response["Content-Security-Policy"] = "sandbox; default-src 'none'"
    return response
