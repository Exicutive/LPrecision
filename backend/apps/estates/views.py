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


@require_GET
@login_required
def estates(request):
    if is_platform_admin(request.user):
        queryset = Estate.objects.all()
    elif CompanyMembership.objects.filter(user=request.user, is_active=True).exists():
        queryset = Estate.objects.filter(company_id__in=_company_ids_for_user(request.user))
    else:
        estate_ids = Estate.objects.filter(
            parcels__allocation__allottee=request.user,
            parcels__allocation__status=Allocation.Status.ACTIVE,
        ).values_list("id", flat=True)
        queryset = Estate.objects.filter(id__in=estate_ids).distinct()
    return JsonResponse({"estates": [_estate_data(estate) for estate in queryset]})

@require_http_methods(["GET", "POST"])
@login_required
def company_estates(request, company_id):
    membership = company_admin_required(request, company_id)
    if not membership:
        return JsonResponse({"detail": "Company administrator access is required for this company."}, status=403)
    company = membership.company
    if request.method == "GET":
        queryset = company.estates.select_related("created_by")
        search = request.GET.get("search", "").strip()
        status_value = request.GET.get("status", "").strip().lower()
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search)
                | models.Q(address__icontains=search)
                | models.Q(state__icontains=search)
                | models.Q(local_government_area__icontains=search)
            )
        if status_value in Estate.Status.values:
            queryset = queryset.filter(status=status_value)
        return JsonResponse({"estates": [_estate_data(item) for item in queryset]})

    payload = _payload(request) if request.content_type == "application/json" else request.POST
    values, error = _estate_values(payload)
    if error:
        return JsonResponse({"detail": error}, status=400)
    if company.estates.filter(name__iexact=values["name"]).exists():
        return JsonResponse({"detail": "An estate with this name already exists for this company."}, status=409)
    estate = Estate.objects.create(
        company=company,
        code=_estate_code(company, values["name"]),
        created_by=request.user,
        image=request.FILES.get("image"),
        **values,
    )
    log_event(actor=request.user, action="estate.created", company=company, details={"estate_id": estate.pk})
    return JsonResponse({"estate": _estate_data(estate)}, status=201)

@require_GET
@login_required
def company_estates_overview(request, company_id):
    membership = company_admin_required(request, company_id)
    if not membership:
        return JsonResponse({"detail": "Company administrator access is required for this company."}, status=403)
    estates = membership.company.estates
    parcels = Parcel.objects.filter(estate__company=membership.company)
    return JsonResponse({
        "total_estates": estates.count(),
        "active_estates": estates.filter(status=Estate.Status.ACTIVE).count(),
        "inactive_estates": estates.filter(status=Estate.Status.INACTIVE).count(),
        "archived_estates": estates.filter(status=Estate.Status.ARCHIVED).count(),
        "total_parcels": parcels.count(),
        "allocated_parcels": parcels.filter(allocation__isnull=False).count(),
    })

@require_http_methods(["GET", "PATCH", "POST"])
@login_required
def company_estate_detail(request, company_id, estate_id):
    membership = company_admin_required(request, company_id)
    if not membership:
        return JsonResponse({"detail": "Company administrator access is required for this company."}, status=403)
    estate = _company_estate(membership, estate_id)
    if not estate:
        return JsonResponse({"detail": "Estate not found."}, status=404)
    if request.method == "GET":
        return JsonResponse({"estate": _estate_data(estate)})

    payload = request.POST if request.method == "POST" else _payload(request)
    values, error = _estate_values(payload, existing=estate)
    if error:
        return JsonResponse({"detail": error}, status=400)
    duplicate = membership.company.estates.filter(name__iexact=values["name"]).exclude(pk=estate.pk).exists()
    if duplicate:
        return JsonResponse({"detail": "An estate with this name already exists for this company."}, status=409)
    for key, value in values.items():
        setattr(estate, key, value)
    if request.FILES.get("image"):
        estate.image = request.FILES["image"]
    estate.code = _estate_code(membership.company, values["name"], exclude_id=estate.pk)
    estate.save()
    log_event(actor=request.user, action="estate.updated", company=membership.company, details={"estate_id": estate.pk})
    return JsonResponse({"estate": _estate_data(estate)})

@require_POST
@login_required
def company_estate_status(request, company_id, estate_id, status):
    membership = company_admin_required(request, company_id)
    if not membership:
        return JsonResponse({"detail": "Company administrator access is required for this company."}, status=403)
    estate = _company_estate(membership, estate_id)
    if not estate:
        return JsonResponse({"detail": "Estate not found."}, status=404)
    if status not in Estate.Status.values:
        return JsonResponse({"detail": "Invalid estate status."}, status=400)
    estate.status = status
    estate.is_active = status == Estate.Status.ACTIVE
    estate.save(update_fields=("status", "is_active", "updated_at"))
    log_event(actor=request.user, action=f"estate.{status}", company=membership.company, details={"estate_id": estate.pk})
    return JsonResponse({"estate": _estate_data(estate)})
