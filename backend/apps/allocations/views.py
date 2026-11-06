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
def allocations(request):
    queryset = Allocation.objects.select_related("parcel__estate", "allottee")
    if not is_platform_admin(request.user):
        company_ids = _company_ids_for_user(request.user)
        if CompanyMembership.objects.filter(user=request.user, is_active=True).exists():
            queryset = queryset.filter(parcel__estate__company_id__in=company_ids)
        else:
            queryset = queryset.filter(allottee=request.user)
    return JsonResponse({"allocations": [_allocation_data(item) for item in queryset]})

@require_GET
@login_required
def my_property(request):
    allocations = list(
        Allocation.objects.select_related(
            "parcel__estate__company", "allottee"
        ).filter(allottee=request.user)
    )
    serialized = [_allocation_data(item, recipient_view=True) for item in allocations]
    return JsonResponse({
        "allocations": serialized,
        "allocation": serialized[0] if serialized else None,
    })

@require_GET
@login_required
def my_property_detail(request, allocation_id):
    allocation = (
        Allocation.objects.select_related("parcel__estate__company", "allottee")
        .filter(pk=allocation_id, allottee=request.user)
        .first()
    )
    if not allocation:
        return JsonResponse({"detail": "Property allocation not found."}, status=404)
    return JsonResponse({"allocation": _allocation_data(allocation, recipient_view=True)})

@require_http_methods(["GET", "POST"])
@login_required
def company_allocations(request, company_id):
    membership = company_admin_required(request, company_id)
    if not membership:
        return JsonResponse({"detail": "Company administrator access is required for this company."}, status=403)
    queryset = Allocation.objects.select_related("parcel__estate", "allottee").filter(
        parcel__estate__company=membership.company
    )
    if request.method == "GET":
        return JsonResponse({
            "allocations": [_allocation_data(item, include_delivery_error=True) for item in queryset]
        })
    payload = _payload(request)
    if payload is None:
        return JsonResponse({"detail": "Send a valid JSON request."}, status=400)

    parcel_id = payload.get("parcel_id")
    email = str(payload.get("email", "")).strip().lower()
    recipient_name = str(payload.get("full_name", "")).strip()
    reference = str(payload.get("reference", "")).strip()
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({"detail": "Enter a valid recipient email address."}, status=400)
    existing_recipient = User.objects.filter(email__iexact=email).first()
    if not recipient_name and existing_recipient:
        recipient_name = existing_recipient.get_full_name() or existing_recipient.username
    if len(email) > 150 or not recipient_name or len(recipient_name) > 200:
        return JsonResponse(
            {"detail": "Recipient full name and a valid email address are required."},
            status=400,
        )
    if reference and len(reference) > 50:
        return JsonResponse({"detail": "Allocation reference must be 50 characters or fewer."}, status=400)

    try:
        with transaction.atomic():
            parcel = Parcel.objects.select_for_update().select_related(
                "estate__company"
            ).filter(pk=parcel_id, estate__company=membership.company).first()
            if not parcel:
                return JsonResponse({"detail": "Company parcel not found."}, status=404)
            existing = Allocation.objects.select_for_update().filter(parcel=parcel).first()
            if existing:
                if existing.recipient_email.casefold() == email.casefold():
                    existing = Allocation.objects.select_related(
                        "parcel__estate__company", "allottee"
                    ).get(pk=existing.pk)
                    return JsonResponse({"allocation": _allocation_data(existing)}, status=200)
                return JsonResponse({"detail": "This parcel has already been allocated."}, status=409)
            if (
                parcel.status != Parcel.Status.AVAILABLE
                or parcel.extraction_status != "approved"
                or parcel.estate.status != Estate.Status.ACTIVE
                or not parcel.estate.is_active
                or parcel.estate.company.status != Company.Status.ACTIVE
            ):
                return JsonResponse(
                    {"detail": "Only available, approved parcels in an active estate can be allocated."},
                    status=409,
                )
            if not reference:
                reference = f"ALLOC-{uuid.uuid4().hex[:12].upper()}"
            if Allocation.objects.filter(reference=reference).exists():
                return JsonResponse({"detail": "This allocation reference is already in use."}, status=409)

            allocation = Allocation.objects.create(
                reference=reference,
                parcel=parcel,
                recipient_name=recipient_name,
                recipient_email=email,
            )
            parcel.status = Parcel.Status.ALLOCATED
            parcel.save(update_fields=("status", "updated_at"))
            invitation, raw_token = create_allocation_invitation(allocation)
            log_event(
                actor=request.user,
                action="parcel.allocated",
                company=membership.company,
                details={
                    "parcel_id": parcel.pk,
                    "allocation_id": allocation.pk,
                    "recipient_email": email,
                },
            )
            log_event(
                actor=request.user,
                action="allocation_invitation.created",
                company=membership.company,
                details={"allocation_id": allocation.pk, "invitation_id": str(invitation.pk)},
            )
            schedule_allocation_invitation_delivery(invitation, raw_token)
            schedule_company_notification(
                company_id=membership.company_id,
                notification_type="property_allocation",
                subject=f"Property allocation created — {parcel.estate.name}",
                message=(
                    f"{parcel.plot_number} in {parcel.estate.name} was allocated to "
                    f"{recipient_name} ({email}) by {request.user.get_full_name() or request.user.email}."
                ),
            )
    except IntegrityError:
        existing = Allocation.objects.select_related(
            "parcel__estate__company", "allottee"
        ).filter(parcel_id=parcel_id, recipient_email__iexact=email).first()
        if existing:
            return JsonResponse({"allocation": _allocation_data(existing)}, status=200)
        return JsonResponse(
            {"detail": "The parcel or allocation reference was allocated by another request."},
            status=409,
        )

    allocation = Allocation.objects.select_related(
        "parcel__estate__company", "allottee"
    ).get(pk=allocation.pk)
    return JsonResponse({"allocation": _allocation_data(allocation)}, status=201)

@require_GET
def allocation_invitation_status(request):
    if _invitation_request_rate_limited(
        request, "validate", limit=20, window_seconds=60
    ):
        return JsonResponse(
            {"detail": "Too many invitation checks. Please wait and try again."},
            status=429,
        )
    token = str(request.GET.get("token", "")).strip()
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    invitation = AllocationInvitation.objects.filter(
        token_hash=token_hash,
        status__in=(AllocationInvitation.Status.PENDING, AllocationInvitation.Status.SENT),
    ).first()
    if not invitation:
        return JsonResponse({"detail": "This invitation is invalid, expired, or already used."}, status=400)
    if invitation.expires_at <= timezone.now():
        invitation.status = AllocationInvitation.Status.EXPIRED
        invitation.save(update_fields=("status",))
        log_event(
            actor=None,
            action="allocation_invitation.expired",
            company=invitation.allocation.parcel.estate.company,
            details={"allocation_id": invitation.allocation_id, "invitation_id": str(invitation.pk)},
        )
        return JsonResponse({"detail": "This invitation has expired. Ask the company to resend it."}, status=400)
    return JsonResponse({
        "email": invitation.recipient_email,
        "expires_at": invitation.expires_at.isoformat(),
    })

@require_POST
def accept_allocation_invitation(request):
    if _invitation_request_rate_limited(
        request, "accept", limit=10, window_seconds=3600
    ):
        return JsonResponse(
            {"detail": "Too many invitation attempts. Please wait before trying again."},
            status=429,
        )
    payload = _payload(request)
    if payload is None:
        return JsonResponse({"detail": "Send a valid JSON request."}, status=400)

    token = str(payload.get("token", "")).strip()
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    created_user = None
    with transaction.atomic():
        invitation = AllocationInvitation.objects.select_for_update().select_related(
            "allocation__parcel__estate__company"
        ).filter(
            token_hash=token_hash,
            status__in=(AllocationInvitation.Status.PENDING, AllocationInvitation.Status.SENT),
        ).first()
        if not invitation:
            return JsonResponse(
                {"detail": "This invitation is invalid, expired, revoked, or already used."},
                status=400,
            )
        if invitation.expires_at <= timezone.now():
            invitation.status = AllocationInvitation.Status.EXPIRED
            invitation.save(update_fields=("status",))
            log_event(
                actor=None,
                action="allocation_invitation.expired",
                company=invitation.allocation.parcel.estate.company,
                details={"allocation_id": invitation.allocation_id, "invitation_id": str(invitation.pk)},
            )
            return JsonResponse(
                {"detail": "This invitation has expired. Ask the company to resend it."},
                status=400,
            )

        allocation = Allocation.objects.select_for_update().get(pk=invitation.allocation_id)
        if allocation.status == Allocation.Status.REVOKED:
            invitation.status = AllocationInvitation.Status.REVOKED
            invitation.revoked_at = timezone.now()
            invitation.save(update_fields=("status", "revoked_at"))
            return JsonResponse({"detail": "This allocation invitation is no longer available."}, status=400)
        if allocation.allottee_id:
            return JsonResponse(
                {"detail": "This allocation has already been linked to an account."},
                status=409,
            )

        email = invitation.recipient_email.strip().lower()
        if request.user.is_authenticated:
            user = request.user
            if user.email.strip().casefold() != email.casefold():
                return JsonResponse(
                    {"detail": "This allocation is tied to a different email. Sign in with the email address that received the invitation."},
                    status=409,
                )
        else:
            existing_user = User.objects.filter(email__iexact=email).first()
            if existing_user:
                return JsonResponse(
                    {"detail": "An account already exists for this email. Sign in to that account to claim the allocation."},
                    status=409,
                )
            full_name = str(payload.get("full_name", "")).strip()
            password = payload.get("password")
            if not full_name or len(full_name) > 200 or not isinstance(password, str):
                return JsonResponse(
                    {"detail": "Full name and password are required to create your account."},
                    status=400,
                )
            from django.contrib.auth.password_validation import validate_password

            candidate = User(username=email, email=email)
            try:
                validate_password(password, user=candidate)
            except ValidationError as error:
                return JsonResponse({"detail": " ".join(error.messages)}, status=400)
            parts = full_name.split(maxsplit=1)
            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=email,
                        email=email,
                        password=password,
                        first_name=parts[0],
                        last_name=parts[1] if len(parts) > 1 else "",
                    )
            except IntegrityError:
                return JsonResponse(
                    {"detail": "An account already exists for this email. Sign in to that account to claim the allocation."},
                    status=409,
                )
            created_user = user

        email_record = VerifiedEmail.objects.filter(email__iexact=email).first()
        if email_record and email_record.user_id != user.pk:
            return JsonResponse(
                {"detail": "This email address is verified on a different account. Contact support for assistance."},
                status=409,
            )
        VerifiedEmail.objects.get_or_create(
            email=email,
            defaults={"user": user},
        )
        allocation.allottee = user
        allocation.status = Allocation.Status.ACTIVE
        allocation.save(update_fields=("allottee", "status", "updated_at"))
        invitation.status = AllocationInvitation.Status.ACCEPTED
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=("status", "accepted_at"))
        log_event(
            actor=user,
            action="allocation_invitation.accepted",
            company=allocation.parcel.estate.company,
            details={"allocation_id": allocation.pk, "invitation_id": str(invitation.pk)},
        )

    if created_user is not None:
        login(request, created_user)
    allocation = Allocation.objects.select_related(
        "parcel__estate__company", "allottee"
    ).get(pk=allocation.pk)
    return JsonResponse({"allocation": _allocation_data(allocation)})

@require_POST
@login_required
def resend_allocation_invitation(request, company_id, allocation_id):
    membership = company_admin_required(request, company_id)
    if not membership:
        return JsonResponse({"detail": "Company administrator access is required for this company."}, status=403)
    with transaction.atomic():
        allocation = Allocation.objects.select_for_update().select_related(
            "parcel__estate__company"
        ).filter(pk=allocation_id, parcel__estate__company=membership.company).first()
        if not allocation:
            return JsonResponse({"detail": "Company allocation not found."}, status=404)
        if allocation.status == Allocation.Status.REVOKED:
            return JsonResponse({"detail": "A revoked allocation cannot be re-invited."}, status=409)
        if allocation.allottee_id:
            return JsonResponse({"detail": "This allocation is already linked to a recipient account."}, status=409)
        now = timezone.now()
        allocation.invitations.filter(status__in=(
            AllocationInvitation.Status.PENDING,
            AllocationInvitation.Status.SENT,
            AllocationInvitation.Status.FAILED,
        )).update(status=AllocationInvitation.Status.REVOKED, revoked_at=now)
        invitation, raw_token = create_allocation_invitation(allocation)
        log_event(
            actor=request.user,
            action="allocation_invitation.resent",
            company=membership.company,
            details={"allocation_id": allocation.pk, "invitation_id": str(invitation.pk)},
        )
        schedule_allocation_invitation_delivery(invitation, raw_token)
    allocation = Allocation.objects.select_related(
        "parcel__estate__company", "allottee"
    ).get(pk=allocation.pk)
    return JsonResponse({"allocation": _allocation_data(allocation)})

@require_POST
@login_required
def revoke_allocation(request, company_id, allocation_id):
    membership = company_admin_required(request, company_id)
    if not membership:
        return JsonResponse({"detail": "Company administrator access is required for this company."}, status=403)
    with transaction.atomic():
        allocation = Allocation.objects.select_for_update().filter(
            pk=allocation_id, parcel__estate__company=membership.company
        ).first()
        if not allocation:
            return JsonResponse({"detail": "Company allocation not found."}, status=404)
        if allocation.status != Allocation.Status.REVOKED:
            allocation.status = Allocation.Status.REVOKED
            allocation.save(update_fields=("status", "updated_at"))
            now = timezone.now()
            allocation.invitations.filter(status__in=(
                AllocationInvitation.Status.PENDING,
                AllocationInvitation.Status.SENT,
                AllocationInvitation.Status.FAILED,
            )).update(status=AllocationInvitation.Status.REVOKED, revoked_at=now)
            log_event(
                actor=request.user,
                action="allocation.revoked",
                company=membership.company,
                details={"allocation_id": allocation.pk, "parcel_id": allocation.parcel_id},
            )
    return JsonResponse({"detail": "Allocation revoked. Its historical record was retained."})

@require_POST
@login_required
def company_property_invitation(request, company_id):
    membership = company_admin_required(request, company_id)
    if not membership:
        return JsonResponse({"detail": "Company administrator access is required for this company."}, status=403)
    payload = _payload(request)
    parcel = Parcel.objects.filter(
        pk=(payload or {}).get("parcel_id"), estate__company=membership.company
    ).first()
    email = str((payload or {}).get("email", "")).strip().lower()
    if not parcel or not email or "@" not in email:
        return JsonResponse({"detail": "A company parcel and valid email are required."}, status=400)
    invitation = PropertyInvitation.objects.create(
        company=membership.company, parcel=parcel, email=email, invited_by=request.user,
        expires_at=timezone.now() + timedelta(days=7),
    )
    log_event(actor=request.user, action="property.invited", company=membership.company,
              details={"parcel_id": parcel.pk, "email": email})
    return JsonResponse({"invitation": {"id": invitation.pk, "email": invitation.email,
                                         "expires_at": invitation.expires_at.isoformat()}}, status=201)
