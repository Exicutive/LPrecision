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
from django.db import transaction
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
    WGS84_COORDINATE_REFERENCE_SYSTEM,
    create_survey_plan,
    validate_boundary_coordinates,
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


@require_GET
@login_required
def recipient_survey_plan_detail(request, allocation_id, survey_plan_id):
    plan = SurveyPlan.objects.select_related(
        "allocation", "parcel", "estate", "uploaded_by"
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


# Save a WGS84 boumdary supplied directly by the active property holder
@require_POST
@login_required
def recipient_boundary_update(request, allocation_id):
    allocation = Allocation.objects.select_related("parcel__estate__company").filter(
        pk=allocation_id,
        allottee=request.user,
        status=Allocation.Status.ACTIVE,
    ).first()
    if not allocation:
        return JsonResponse({"detail": "You can only update the boundary for an active property linked to your account."}, status=404)
    payload = _payload(request)
    if payload is None:
        return JsonResponse({"detail": "Send a valid JSON request."}, status=400)
    try:
        coordinates = validate_boundary_coordinates(
            payload.get("boundary_coordinates"),
            payload.get("coordinate_reference_system"),
        )
    except SurveyPlanUploadError as error:
        return JsonResponse({"detail": str(error)}, status=400)
    allocation.parcel.boundary_coordinates = coordinates
    allocation.parcel.boundary_coordinate_reference_system = WGS84_COORDINATE_REFERENCE_SYSTEM
    allocation.parcel.perimeter_m = None
    allocation.parcel.save(update_fields=(
        "boundary_coordinates", "boundary_coordinate_reference_system", "perimeter_m", "updated_at",
    ))
    log_event(
        actor=request.user,
        action="parcel.boundary_submitted_by_recipient",
        company=allocation.parcel.estate.company,
        details={
            "parcel_id": allocation.parcel_id,
            "allocation_id": allocation.pk,
            "coordinate_reference_system": WGS84_COORDINATE_REFERENCE_SYSTEM,
            "vertex_count": len(coordinates),
        },
    )
    return JsonResponse({"parcel": _parcel_data(allocation.parcel)})


# Allow only the linked property holder to save a plan for their property
@require_POST
@login_required
def recipient_survey_plan_upload(request, allocation_id):
    allocation = Allocation.objects.select_related("parcel__estate__company").filter(
        pk=allocation_id,
        allottee=request.user,
        status=Allocation.Status.ACTIVE,
    ).first()
    if not allocation:
        return JsonResponse(
            {"detail": "You can only upload a survey plan for an active property linked to your account."},
            status=404,
        )
    try:
        plan, created = create_survey_plan(
            company=allocation.parcel.estate.company,
            allocation_id=allocation.pk,
            uploaded_file=request.FILES.get("document"),
            metadata=request.POST,
            user=request.user,
            recipient=request.user,
        )
    except SurveyPlanUploadError as error:
        return JsonResponse({"detail": str(error)}, status=400)
    except ValidationError as error:
        return JsonResponse({"detail": "; ".join(error.messages)}, status=400)
    if created:
        log_event(
            actor=request.user,
            action="survey_plan.uploaded_by_recipient",
            company=allocation.parcel.estate.company,
            details={"survey_plan_id": str(plan.pk), "allocation_id": allocation.pk, "parcel_id": allocation.parcel_id},
        )
        if plan.submitted_boundary_coordinates:
            log_event(
                actor=request.user,
                action="parcel.boundary_updated_by_recipient",
                company=allocation.parcel.estate.company,
                details={"parcel_id": allocation.parcel_id, "survey_plan_id": str(plan.pk)},
            )
    data = _survey_plan_data(plan)
    data["download_path"] = f"my-property/{allocation.pk}/survey-plans/{plan.pk}/download"
    return JsonResponse({"survey_plan": data, "duplicate": not created}, status=201 if created else 200)

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
