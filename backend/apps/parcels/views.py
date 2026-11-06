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
def parcels(request):
    queryset = Parcel.objects.select_related("estate")
    if is_platform_admin(request.user):
        estate_id = request.GET.get("estate")
        if estate_id:
            queryset = queryset.filter(estate_id=estate_id)
    elif CompanyMembership.objects.filter(user=request.user, is_active=True).exists():
        queryset = queryset.filter(estate__company_id__in=_company_ids_for_user(request.user))
    else:
        queryset = queryset.filter(
            allocation__allottee=request.user,
            allocation__status=Allocation.Status.ACTIVE,
        )
    return JsonResponse({"parcels": [_parcel_data(parcel) for parcel in queryset]})

@require_http_methods(["GET", "POST"])
@login_required
def company_parcels(request, company_id):
    membership = company_admin_required(request, company_id)
    if not membership:
        return JsonResponse({"detail": "Company administrator access is required for this company."}, status=403)
    queryset = Parcel.objects.select_related("estate").filter(estate__company=membership.company)
    if request.method == "GET":
        return JsonResponse({"parcels": [_parcel_data(item) for item in queryset]})
    payload = _payload(request) or {}
    estate_id = payload.get("estate_id")
    estate = membership.company.estates.filter(pk=estate_id).first()
    plot_number = str(payload.get("plot_number", "")).strip()
    if not estate or not plot_number:
        return JsonResponse({"detail": "A company estate and plot number are required."}, status=400)
    if Parcel.objects.filter(estate=estate, plot_number=plot_number).exists():
        return JsonResponse({"detail": "This plot number already exists in the estate."}, status=400)
    area = payload.get("area_sqm")
    try:
        area = Decimal(str(area)) if area not in (None, "") else None
    except (InvalidOperation, ValueError):
        return JsonResponse({"detail": "Area must be a number."}, status=400)
    property_type = str(payload.get("property_type", "")).strip()
    features = payload.get("features", [])
    if len(property_type) > 100 or not isinstance(features, list) or not all(
        isinstance(feature, str) for feature in features
    ):
        return JsonResponse(
            {"detail": "Property type must be 100 characters or fewer and features must be a list of text values."},
            status=400,
        )
    parcel = Parcel.objects.create(
        estate=estate, plot_number=plot_number, block=str(payload.get("block", "")).strip(),
        area_sqm=area, property_type=property_type, features=features,
        survey_reference=str(payload.get("survey_reference", "")).strip(),
        boundary_coordinates=payload.get("boundary_coordinates", []),
    )
    log_event(actor=request.user, action="parcel.created", company=membership.company, details={"parcel_id": parcel.pk})
    return JsonResponse({"parcel": _parcel_data(parcel)}, status=201)
