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
def platform_dashboard(request):
    denied = platform_admin_required(request)
    if denied:
        return denied
    return JsonResponse({
        "companies": Company.objects.count(),
        "active_companies": Company.objects.filter(status=Company.Status.ACTIVE).count(),
        "suspended_companies": Company.objects.filter(status=Company.Status.SUSPENDED).count(),
        "company_admins": CompanyMembership.objects.filter(is_active=True).count(),
        "estates": Estate.objects.count(),
        "parcels": Parcel.objects.count(),
    })

@require_GET
@login_required
def platform_companies(request):
    denied = platform_admin_required(request)
    if denied:
        return denied
    return JsonResponse({"companies": [_company_data(item) for item in Company.objects.all()]})

@require_POST
@login_required
def platform_register_company(request):
    denied = platform_admin_required(request)
    if denied:
        return denied
    payload = _payload(request) if request.content_type == "application/json" else request.POST
    if payload is None:
        return JsonResponse({"detail": "Send a valid JSON request."}, status=400)
    name = str(payload.get("name", "")).strip()
    code = str(payload.get("code", "")).strip().lower()
    legal_name = str(payload.get("legal_name", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    contact_person = str(payload.get("contact_person", "")).strip()
    phone = str(payload.get("phone", "")).strip()
    if not name or not email or not contact_person or not phone:
        return JsonResponse({"detail": "Company name, email, contact person, and phone are required."}, status=400)
    if "@" not in email:
        return JsonResponse({"detail": "Enter a valid company email address."}, status=400)
    if Company.objects.filter(name__iexact=name).exists():
        return JsonResponse({"detail": "A company with this name already exists."}, status=400)
    base_code = slugify(code or name)[:40] or "company"
    unique_code = base_code
    suffix = 2
    while Company.objects.filter(code=unique_code).exists():
        suffix_text = f"-{suffix}"
        unique_code = f"{base_code[:40 - len(suffix_text)]}{suffix_text}"
        suffix += 1
    company = Company.objects.create(
        name=name, code=unique_code, legal_name=legal_name or name, email=email,
        contact_person=contact_person, phone=phone,
    )
    log_event(actor=request.user, action="company.registered", company=company)
    return JsonResponse({"company": _company_data(company)}, status=201)

@require_GET
@login_required
def platform_company_detail(request, company_id):
    denied = platform_admin_required(request)
    if denied:
        return denied
    company = Company.objects.filter(pk=company_id).first()
    if not company:
        return JsonResponse({"detail": "Company not found."}, status=404)
    return JsonResponse({
        "company": _company_data(company),
        "administrators": [_admin_membership_data(item) for item in company.memberships.select_related("user")],
        "invitations": [_invitation_data(item) for item in company.admin_invitations.all()],
    })

@require_POST
@login_required
def platform_company_status(request, company_id, status):
    denied = platform_admin_required(request)
    if denied:
        return denied
    company = Company.objects.filter(pk=company_id).first()
    if not company:
        return JsonResponse({"detail": "Company not found."}, status=404)
    if status not in (Company.Status.ACTIVE, Company.Status.SUSPENDED):
        return JsonResponse({"detail": "Invalid company status."}, status=400)
    company.status = status
    company.save(update_fields=("status", "updated_at"))
    log_event(actor=request.user, action=f"company.{status}", company=company)
    return JsonResponse({"company": _company_data(company)})

@require_POST
@login_required
def platform_invite_first_company_admin(request, company_id):
    denied = platform_admin_required(request)
    if denied:
        return denied
    company = Company.objects.filter(pk=company_id).first()
    if not company:
        return JsonResponse({"detail": "Company not found."}, status=404)
    if company.memberships.filter(role=CompanyMembership.Role.COMPANY_ADMIN, is_active=True).exists():
        return JsonResponse({"detail": "This company already has a Company Admin."}, status=409)
    payload = _payload(request)
    email = str((payload or {}).get("email", "")).strip().lower()
    if not email or "@" not in email:
        return JsonResponse({"detail": "Enter a valid email address."}, status=400)
    now = timezone.now()
    raw_token = secrets.token_urlsafe(32)
    with transaction.atomic():
        company.admin_invitations.filter(status=CompanyAdminInvitation.Status.PENDING).update(
            status=CompanyAdminInvitation.Status.REVOKED
        )
        invitation = CompanyAdminInvitation.objects.create(
            company=company,
            email=email,
            token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
            invited_by=request.user,
            expires_at=now + timedelta(days=7),
        )
        acceptance_url = f"{settings.FRONTEND_URL}/property/?company_admin_invitation={raw_token}"
        send_mail(
            f"You're invited to manage {company.name} on TerraLedger",
            (
                f"You have been invited to become an administrator for {company.name}.\n\n"
                f"Accept the invitation to set up your access:\n{acceptance_url}"
            ),
            None,
            [email],
            fail_silently=False,
        )
    log_event(actor=request.user, action="company_admin.invited", company=company, details={"email": email})
    response = {"invitation": _invitation_data(invitation)}
    if settings.DEBUG:
        response["invitation_token"] = raw_token
        # Local development does not have a real outbound email service by
        # default. Returning the same URL shown in the development mail
        # console lets the Platform Admin test the exact, current invitation.
        response["invitation_url"] = acceptance_url
    return JsonResponse(response, status=201)

@require_GET
@login_required
def platform_audit_events(request):
    denied = platform_admin_required(request)
    if denied:
        return denied
    events = PlatformAuditEvent.objects.select_related("actor", "company")[:200]
    return JsonResponse({"events": [{
        "id": event.pk, "action": event.action, "company_id": event.company_id,
        "actor": event.actor.email if event.actor else None, "details": event.details,
        "created_at": event.created_at.isoformat(),
    } for event in events]})

@require_http_methods(["GET", "POST"])
@login_required
def platform_settings(request):
    denied = platform_admin_required(request)
    if denied:
        return denied
    if request.method == "GET":
        return JsonResponse({"settings": [{
            "key": item.key, "value": item.value, "updated_at": item.updated_at.isoformat()
        } for item in PlatformSetting.objects.all()]})
    payload = _payload(request)
    if payload is None:
        return JsonResponse({"detail": "Send a valid JSON request."}, status=400)
    settings_value = payload.get("settings")
    if not isinstance(settings_value, dict):
        return JsonResponse({"detail": "Settings must be an object keyed by setting name."}, status=400)
    saved = []
    for key, value in settings_value.items():
        if not isinstance(key, str) or not key.strip() or len(key) > 100:
            return JsonResponse({"detail": "Each setting name must be 1–100 characters."}, status=400)
        item, _ = PlatformSetting.objects.update_or_create(
            key=key.strip(), defaults={"value": value, "updated_by": request.user}
        )
        saved.append(item.key)
    log_event(actor=request.user, action="platform.settings.updated", details={"keys": sorted(saved)})
    return JsonResponse({"settings": saved})
