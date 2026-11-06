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
def company_admin_invitation_status(request):
    """Validate an invitation before the browser offers account creation."""
    # Older frontend builds accidentally appended a slash to the query value.
    # The generated tokens are URL-safe and never contain slashes, so accepting
    # surrounding whitespace/a trailing slash keeps a cached client from making
    # an otherwise valid invitation appear expired.
    token = str(request.GET.get("token", "")).strip().rstrip("/")
    invitation = CompanyAdminInvitation.objects.select_related("company").filter(
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        status=CompanyAdminInvitation.Status.PENDING,
    ).first()
    if not invitation or invitation.expires_at <= timezone.now():
        return JsonResponse({"detail": "This invitation is invalid or has expired."}, status=400)
    if invitation.company.status != Company.Status.ACTIVE:
        return JsonResponse({"detail": "This company is not currently active."}, status=403)
    return JsonResponse({
        "company": {"id": invitation.company_id, "name": invitation.company.name},
        "email": invitation.email,
        "expires_at": invitation.expires_at.isoformat(),
    })

@require_POST
def accept_company_admin_invitation(request):
    payload = _payload(request)
    if payload is None:
        return JsonResponse({"detail": "Send a valid JSON request."}, status=400)
    token = str(payload.get("token", "")).strip().rstrip("/")
    with transaction.atomic():
        invitation = CompanyAdminInvitation.objects.select_for_update().select_related("company").filter(
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            status=CompanyAdminInvitation.Status.PENDING,
        ).first()
        if not invitation or invitation.expires_at <= timezone.now():
            return JsonResponse({"detail": "This invitation is invalid or has expired."}, status=400)
        if invitation.company.status != Company.Status.ACTIVE:
            return JsonResponse({"detail": "This company is not currently active."}, status=403)

        email = invitation.email.lower()
        if request.user.is_authenticated:
            if request.user.email.lower() != email:
                return JsonResponse(
                    {"detail": "Sign in or create an account with the invited email address before accepting this invitation."},
                    status=409,
                )
            user = request.user
        else:
            user = User.objects.filter(email__iexact=email).first()
            if user:
                return JsonResponse({"detail": "Sign in to the invited existing account before accepting this invitation."}, status=409)
            full_name = str(payload.get("full_name", "")).strip()
            password = payload.get("password")
            if not full_name or not isinstance(password, str):
                return JsonResponse({"detail": "Full name and password are required to create the invited account."}, status=400)
            from django.contrib.auth.password_validation import validate_password
            from django.core.exceptions import ValidationError
            candidate = User(username=email, email=email)
            try:
                validate_password(password, user=candidate)
            except ValidationError as error:
                return JsonResponse({"detail": " ".join(error.messages)}, status=400)
            parts = full_name.split(maxsplit=1)
            user = User.objects.create_user(username=email, email=email, password=password,
                                            first_name=parts[0], last_name=parts[1] if len(parts) > 1 else "")
        membership, _ = CompanyMembership.objects.get_or_create(
            company=invitation.company, user=user, role=CompanyMembership.Role.COMPANY_ADMIN,
            defaults={"is_active": True},
        )
        if not membership.is_active:
            membership.is_active = True
            membership.save(update_fields=("is_active", "updated_at"))
        invitation.status = CompanyAdminInvitation.Status.ACCEPTED
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=("status", "accepted_at"))
        invitation.company.setup_status = Company.SetupStatus.COMPLETE
        invitation.company.save(update_fields=("setup_status", "updated_at"))
        log_event(actor=user, action="company_admin.accepted", company=invitation.company)
    if not request.user.is_authenticated:
        login(request, user)
    return JsonResponse({"company": _company_data(invitation.company), "membership": _admin_membership_data(membership)})

@require_GET
@login_required
def company_dashboard(request, company_id):
    membership = company_admin_required(request, company_id)
    if not membership:
        return JsonResponse({"detail": "Company administrator access is required for this company."}, status=403)
    company = membership.company
    parcels = Parcel.objects.filter(estate__company=company)
    return JsonResponse({
        "company": _company_data(company),
        "estates": company.estates.count(),
        "active_estates": company.estates.filter(status=Estate.Status.ACTIVE).count(),
        "parcels": parcels.count(),
        "allocated_parcels": parcels.filter(allocation__isnull=False).count(),
        "available_parcels": parcels.filter(status=Parcel.Status.AVAILABLE).count(),
        "allocations": Allocation.objects.filter(parcel__estate__company=company).count(),
        "survey_plans": company.survey_plans.count(),
    })

@require_http_methods(["GET", "POST"])
@login_required
def company_settings(request, company_id):
    membership = company_admin_required(request, company_id)
    if not membership:
        return JsonResponse({"detail": "Company administrator access is required for this company."}, status=403)
    company = membership.company
    if request.method == "GET":
        preferences = company.settings.get("notification_preferences", {})
        if not isinstance(preferences, dict):
            preferences = {}
        return JsonResponse({
            "settings": company.settings,
            "company": {
                "id": company.pk,
                "name": company.name,
                "email": company.email,
                "phone": company.phone,
                "registration_number": company.registration_number,
                "created_at": company.created_at.isoformat(),
                "status": company.status,
            },
            "notification_preferences": {
                key: preferences.get(key) is True for key in NOTIFICATION_TYPES
            },
        })

    payload = (
        _payload(request)
        if request.content_type.startswith("application/json")
        else request.POST.dict()
    )
    if not isinstance(payload, dict):
        return JsonResponse({"detail": "Send valid company settings."}, status=400)

    if request.FILES:
        return JsonResponse({"detail": "Company logos cannot be changed in Company Settings."}, status=400)

    protected_fields = {"id", "code", "created_at", "status", "setup_status"}
    if protected_fields.intersection(payload):
        return JsonResponse(
            {"detail": "Company ID, registration date, status, and company code are read-only."},
            status=400,
        )

    if "email" in payload:
        return JsonResponse({"detail": "Company email cannot be changed in Company Settings."}, status=400)

    allowed_fields = {
        "name", "phone", "registration_number", "notification_preferences", "settings",
    }
    if set(payload).difference(allowed_fields):
        return JsonResponse({"detail": "One or more company settings cannot be changed."}, status=400)
    if any(
        not isinstance(payload[field], str)
        for field in ("name", "phone", "registration_number")
        if field in payload
    ):
        return JsonResponse({"detail": "Company information fields must contain text values."}, status=400)

    if "settings" in payload:
        settings_value = payload["settings"]
        if not isinstance(settings_value, dict):
            return JsonResponse({"detail": "Settings must be an object."}, status=400)
        company.settings = settings_value

    if "notification_preferences" in payload:
        preferences_value = payload["notification_preferences"]
        if isinstance(preferences_value, str):
            try:
                preferences_value = json.loads(preferences_value)
            except json.JSONDecodeError:
                return JsonResponse({"detail": "Notification preferences must be valid JSON."}, status=400)
        if not isinstance(preferences_value, dict) or set(preferences_value) != set(NOTIFICATION_TYPES):
            return JsonResponse(
                {"detail": "Provide a preference for each supported notification type."},
                status=400,
            )
        if any(type(value) is not bool for value in preferences_value.values()):
            return JsonResponse({"detail": "Notification preferences must be true or false."}, status=400)
        company.settings = {
            **company.settings,
            "notification_preferences": preferences_value,
        }

    for field in ("name", "phone", "registration_number"):
        if field in payload:
            setattr(company, field, str(payload[field]).strip())
    if not company.name or len(company.name) > 200:
        return JsonResponse({"detail": "Company name is required and must be 200 characters or fewer."}, status=400)
    if len(company.phone) > 40:
        return JsonResponse({"detail": "Company phone number must be 40 characters or fewer."}, status=400)
    if len(company.registration_number) > 100:
        return JsonResponse({"detail": "RC number must be 100 characters or fewer."}, status=400)
    try:
        company.full_clean(exclude=("logo",))
        company.save()
    except ValidationError as error:
        return JsonResponse({"detail": "; ".join(error.messages)}, status=400)
    except IntegrityError:
        return JsonResponse({"detail": "A company with that name already exists."}, status=400)

    log_event(
        actor=request.user,
        action="company.settings.updated",
        company=company,
        details={"fields": sorted(set(payload) - {"settings", "notification_preferences"})},
    )
    return JsonResponse({"company": _company_data(company), "settings": company.settings})
