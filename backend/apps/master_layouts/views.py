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
def company_estate_master_layouts(request, company_id, estate_id):
    membership = company_admin_required(request, company_id)
    if not membership:
        return JsonResponse({"detail": "Company administrator access is required for this company."}, status=403)
    estate = _company_estate(membership, estate_id)
    if not estate:
        return JsonResponse({"detail": "Estate not found."}, status=404)
    if request.method == "GET":
        plans = estate.master_plans.select_related("uploaded_by")
        return JsonResponse({"master_layouts": [_master_plan_data(plan) for plan in plans]})
    try:
        plan, job, created = MasterLayoutUploadService.create(
            estate=estate, user=request.user, uploaded_file=request.FILES.get("document")
        )
    except LayoutUploadError as error:
        return JsonResponse({"detail": str(error)}, status=400)
    log_event(
        actor=request.user,
        action="master_layout.uploaded" if created else "master_layout.upload_reused",
        company=membership.company,
        details={"estate_id": estate.pk, "layout_id": str(plan.pk), "version": plan.version},
    )
    return JsonResponse({"master_layout": _master_plan_data(plan), "job": _layout_job_data(job)}, status=201 if created else 200)

@require_GET
@login_required
def company_master_layout_detail(request, company_id, layout_id):
    membership = company_admin_required(request, company_id)
    if not membership:
        return JsonResponse({"detail": "Company administrator access is required for this company."}, status=403)
    plan = _company_master_plan(membership, layout_id)
    if not plan:
        return JsonResponse({"detail": "Master layout not found."}, status=404)
    job = plan.processing_jobs.order_by("-created_at").first()
    return JsonResponse({"master_layout": _master_plan_data(plan), "job": _layout_job_data(job) if job else None})

@require_POST
@login_required
def company_master_layout_process(request, company_id, layout_id):
    membership = company_admin_required(request, company_id)
    if not membership:
        return JsonResponse({"detail": "Company administrator access is required for this company."}, status=403)
    plan = _company_master_plan(membership, layout_id)
    if not plan:
        return JsonResponse({"detail": "Master layout not found."}, status=404)
    job = plan.processing_jobs.order_by("-created_at").first()
    if not job:
        job = MasterLayoutProcessingJob.objects.create(
            company=membership.company, estate=plan.estate, master_plan=plan, attempt=1, stage="Waiting for processing"
        )
    if plan.parcel_candidates.exists() and plan.processing_status in {
        EstateMasterPlan.Status.REVIEW_REQUIRED, EstateMasterPlan.Status.READY_FOR_APPROVAL, EstateMasterPlan.Status.APPROVED,
    }:
        return JsonResponse({"master_layout": _master_plan_data(plan), "job": _layout_job_data(job), "detail": "This layout has already been processed."})
    plan, job = MasterLayoutProcessingService.process(plan=plan, job=job)
    log_event(actor=request.user, action="master_layout.processed", company=membership.company, details={"layout_id": str(plan.pk)})
    schedule_company_notification(
        company_id=membership.company_id,
        notification_type="master_layout_processing",
        subject=f"Master layout processing {job.get_status_display().lower()} — {plan.estate.name}",
        message=(
            f"Master layout {plan.original_filename} for {plan.estate.name} "
            f"finished processing with status: {job.get_status_display()}."
        ),
    )
    return JsonResponse({"master_layout": _master_plan_data(plan), "job": _layout_job_data(job)})

@require_GET
@login_required
def company_master_layout_status(request, company_id, layout_id):
    return company_master_layout_detail(request, company_id, layout_id)

@require_GET
@login_required
def company_master_layout_download(request, company_id, layout_id):
    membership = company_admin_required(request, company_id)
    if not membership:
        return JsonResponse({"detail": "Company administrator access is required for this company."}, status=403)
    plan = _company_master_plan(membership, layout_id)
    if not plan or not plan.document:
        return JsonResponse({"detail": "Master layout not found."}, status=404)
    response = FileResponse(plan.document.open("rb"), as_attachment=True, filename=plan.original_filename)
    response["X-Content-Type-Options"] = "nosniff"
    return response

@require_GET
@login_required
def company_master_layout_candidates(request, company_id, layout_id):
    membership = company_admin_required(request, company_id)
    if not membership:
        return JsonResponse({"detail": "Company administrator access is required for this company."}, status=403)
    plan = _company_master_plan(membership, layout_id)
    if not plan:
        return JsonResponse({"detail": "Master layout not found."}, status=404)
    candidates = plan.parcel_candidates.select_related("published_parcel")
    query = request.GET.get("search", "").strip()
    block = request.GET.get("block", "").strip()
    status = request.GET.get("status", "").strip()
    if query:
        candidates = candidates.filter(models.Q(plot_number__icontains=query) | models.Q(block__icontains=query))
    if block:
        candidates = candidates.filter(block__iexact=block)
    if status in ExtractedParcelCandidate.Status.values:
        candidates = candidates.filter(status=status)
    return JsonResponse({"candidates": [_candidate_data(candidate) for candidate in candidates]})

@require_POST
@login_required
def company_master_layout_approve_candidates(request, company_id, layout_id):
    membership = company_admin_required(request, company_id)
    if not membership:
        return JsonResponse({"detail": "Company administrator access is required for this company."}, status=403)
    plan = _company_master_plan(membership, layout_id)
    if not plan:
        return JsonResponse({"detail": "Master layout not found."}, status=404)
    payload = _payload(request) or {}
    candidate_ids = payload.get("candidate_ids")
    candidates = plan.parcel_candidates.filter(status=ExtractedParcelCandidate.Status.VALIDATED)
    if candidate_ids is not None:
        if not isinstance(candidate_ids, list):
            return JsonResponse({"detail": "candidate_ids must be a list."}, status=400)
        candidates = candidates.filter(pk__in=candidate_ids)
    published = ParcelGenerationService.approve(plan=plan, candidates=candidates, user=request.user)
    log_event(actor=request.user, action="master_layout.candidates_approved", company=membership.company,
              details={"layout_id": str(plan.pk), "published_count": len(published)})
    plan.refresh_from_db()
    return JsonResponse({"published_count": len(published), "master_layout": _master_plan_data(plan)})

@require_POST
@login_required
def company_master_layout_reject_candidates(request, company_id, layout_id):
    membership = company_admin_required(request, company_id)
    if not membership:
        return JsonResponse({"detail": "Company administrator access is required for this company."}, status=403)
    plan = _company_master_plan(membership, layout_id)
    if not plan:
        return JsonResponse({"detail": "Master layout not found."}, status=404)
    payload = _payload(request) or {}
    candidate_ids = payload.get("candidate_ids")
    if not isinstance(candidate_ids, list) or not candidate_ids:
        return JsonResponse({"detail": "Select one or more candidates to reject."}, status=400)
    rejected = ParcelGenerationService.reject(candidates=plan.parcel_candidates.filter(pk__in=candidate_ids), user=request.user)
    log_event(actor=request.user, action="master_layout.candidates_rejected", company=membership.company,
              details={"layout_id": str(plan.pk), "rejected_count": rejected})
    return JsonResponse({"rejected_count": rejected})
