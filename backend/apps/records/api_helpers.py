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


def _payload(request):
    try:
        value = json.loads(request.body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None

def _company_ids_for_user(user):
    return CompanyMembership.objects.filter(
        user=user,
        role=CompanyMembership.Role.COMPANY_ADMIN,
        is_active=True,
        company__status=Company.Status.ACTIVE,
    ).values_list("company_id", flat=True)

def _company_data(company):
    administrator = company.memberships.filter(
        role=CompanyMembership.Role.COMPANY_ADMIN, is_active=True
    ).select_related("user").first()
    pending_invitation = company.admin_invitations.filter(
        status=CompanyAdminInvitation.Status.PENDING
    ).first()
    return {
        "id": company.pk,
        "name": company.name,
        "code": company.code,
        "legal_name": company.legal_name,
        "email": company.email,
        "contact_person": company.contact_person,
        "phone": company.phone,
        "registration_number": company.registration_number,
        "office_address": company.office_address,
        "logo_url": company.logo.url if company.logo else None,
        "status": company.status,
        "setup_status": company.setup_status,
        "settings": company.settings,
        "estate_count": company.estates.count(),
        "member_count": company.memberships.filter(is_active=True).count(),
        "administrator_email": administrator.user.email if administrator else None,
        "pending_admin_email": pending_invitation.email if pending_invitation else None,
        "created_at": company.created_at.isoformat(),
    }

def _estate_data(estate):
    parcels = estate.parcels
    parcel_count = parcels.count()
    allocated_count = parcels.filter(allocation__isnull=False).count()
    return {
        "id": estate.pk,
        "public_id": str(estate.public_id),
        "name": estate.name,
        "company_name": estate.company.name,
        "code": estate.code,
        "state": estate.state,
        "local_government_area": estate.local_government_area,
        "address": estate.address,
        "description": estate.description,
        "image": estate.image.url if estate.image else None,
        "status": estate.status,
        "is_active": estate.is_active,
        "parcel_count": parcel_count,
        "allocated_parcel_count": allocated_count,
        "available_parcel_count": parcels.filter(status=Parcel.Status.AVAILABLE).count(),
        "survey_plan_count": estate.survey_plans.count(),
        "created_by": (
            estate.created_by.get_full_name() or estate.created_by.username
            if estate.created_by_id else None
        ),
        "created_at": estate.created_at.isoformat(),
        "updated_at": estate.updated_at.isoformat(),
        "company_id": estate.company_id,
    }

def _estate_code(company, name, *, exclude_id=None):
    """Generate a stable, global-safe code without accepting it from a client."""
    base = slugify(f"{company.code}-{name}")[:35] or f"estate-{company.pk}"
    candidate = base
    suffix = 2
    queryset = Estate.objects.all()
    if exclude_id:
        queryset = queryset.exclude(pk=exclude_id)
    while queryset.filter(code__iexact=candidate).exists():
        label = f"-{suffix}"
        candidate = f"{base[:40 - len(label)]}{label}"
        suffix += 1
    return candidate

def _estate_values(payload, *, existing=None):
    """Validate editable estate fields; company ownership is deliberately absent."""
    payload = payload or {}
    values = {}
    for key in ("name", "address", "state", "local_government_area", "description"):
        if key in payload:
            values[key] = str(payload.get(key, "")).strip()
        elif existing is not None:
            values[key] = getattr(existing, key)

    required = {"name": "Estate name", "address": "Estate address", "state": "State", "local_government_area": "Local Government Area"}
    missing = [label for key, label in required.items() if not values.get(key)]
    if missing:
        return None, f"{', '.join(missing)} {'is' if len(missing) == 1 else 'are'} required."
    return values, None

def _company_estate(membership, estate_id):
    """Never retrieve an estate outside the authenticated membership's company."""
    return membership.company.estates.select_related("created_by").filter(pk=estate_id).first()

def _parcel_data(parcel):
    return {
        "id": parcel.pk,
        "public_id": str(parcel.public_id),
        "estate": _estate_data(parcel.estate),
        "plot_number": parcel.plot_number,
        "block": parcel.block,
        "area_sqm": str(parcel.area_sqm) if parcel.area_sqm is not None else None,
        "property_type": parcel.property_type,
        "features": parcel.features,
        "status": parcel.status,
        "survey_reference": parcel.survey_reference,
        "boundary_coordinates": parcel.boundary_coordinates,
        "perimeter_m": str(parcel.perimeter_m) if parcel.perimeter_m is not None else None,
        "source_master_plan_id": str(parcel.source_master_plan_id) if parcel.source_master_plan_id else None,
        "extraction_status": parcel.extraction_status,
        "updated_at": parcel.updated_at.isoformat(),
    }

def _master_plan_data(plan):
    candidates = plan.parcel_candidates
    return {
        "id": str(plan.pk),
        "estate_id": plan.estate_id,
        "version": plan.version,
        "original_filename": plan.original_filename,
        "file_format": plan.file_format,
        "file_size": plan.file_size,
        "uploaded_by": plan.uploaded_by.get_full_name() or plan.uploaded_by.username,
        "uploaded_at": plan.uploaded_at.isoformat(),
        "processing_status": plan.processing_status,
        "processing_started_at": plan.processing_started_at.isoformat() if plan.processing_started_at else None,
        "processing_completed_at": plan.processing_completed_at.isoformat() if plan.processing_completed_at else None,
        "processing_error": plan.processing_error or None,
        "coordinate_reference_system": plan.coordinate_reference_system or None,
        "processing_metadata": plan.processing_metadata,
        "is_current": plan.is_current,
        "candidate_count": candidates.count(),
        "approved_candidate_count": candidates.filter(status=ExtractedParcelCandidate.Status.APPROVED).count(),
    }

def _layout_job_data(job):
    return {
        "id": str(job.pk),
        "status": job.status,
        "stage": job.stage,
        "attempt": job.attempt,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error": job.error or None,
        "metadata": job.metadata,
    }

def _survey_plan_data(plan, *, include_internal=False):
    data = {
        "id": str(plan.pk),
        "company_id": plan.company_id,
        "estate_id": plan.estate_id,
        "parcel_id": plan.parcel_id,
        "allocation_id": plan.allocation_id,
        "name": plan.name,
        "reference": plan.reference,
        "survey_plan_number": plan.survey_plan_number,
        "surveyor_full_name": plan.surveyor_full_name,
        "surveyor_registration_number": plan.surveyor_registration_number,
        "survey_date": plan.survey_date.isoformat() if plan.survey_date else None,
        "state": plan.state,
        "local_government_area": plan.local_government_area,
        "location_description": plan.location_description,
        "stated_area": str(plan.stated_area) if plan.stated_area is not None else None,
        "area_unit": plan.area_unit,
        "coordinate_reference_system": plan.coordinate_reference_system,
        "datum": plan.datum,
        "original_filename": plan.original_filename,
        "file_size": plan.file_size,
        "has_document": bool(plan.document),
        "verification_status": plan.verification_status,
        "uploaded_by": plan.uploaded_by.get_full_name() or plan.uploaded_by.username,
        "uploaded_at": plan.uploaded_at.isoformat(),
        "download_path": (
            f"companies/{plan.company_id}/survey-plans/{plan.pk}/download"
            if plan.document else None
        ),
    }
    if include_internal:
        data.update({
            "notes": plan.notes,
            "verification_notes": plan.verification_notes,
            "verified_by": (
                plan.verified_by.get_full_name() or plan.verified_by.username
                if plan.verified_by_id else None
            ),
            "verified_at": plan.verified_at.isoformat() if plan.verified_at else None,
            "file_format": plan.file_format,
            "checksum": plan.checksum,
            "extracted_metadata": plan.extracted_metadata,
            "created_at": plan.created_at.isoformat(),
            "updated_at": plan.updated_at.isoformat(),
            "verification_history": [{
                "previous_status": event.previous_status,
                "new_status": event.new_status,
                "notes": event.notes,
                "actor": (
                    event.actor.get_full_name() or event.actor.username
                    if event.actor_id else None
                ),
                "created_at": event.created_at.isoformat(),
            } for event in plan.verification_history.select_related("actor").all()],
        })
    return data

def _candidate_data(candidate):
    return {
        "id": str(candidate.pk),
        "plot_number": candidate.plot_number or None,
        "block": candidate.block or None,
        "area_sqm": str(candidate.area_sqm) if candidate.area_sqm is not None else None,
        "perimeter_m": str(candidate.perimeter_m) if candidate.perimeter_m is not None else None,
        "boundary_coordinates": candidate.boundary_coordinates,
        "original_boundary_coordinates": candidate.original_boundary_coordinates,
        "status": candidate.status,
        "validation_warnings": candidate.validation_warnings,
        "published_parcel_id": candidate.published_parcel_id,
        "created_at": candidate.created_at.isoformat(),
    }

def _allocation_data(allocation, *, include_delivery_error=False, recipient_view=False):
    invitation = allocation.invitations.first()
    survey_plans = []
    for plan in allocation.survey_plans.all():
        survey_plan = _survey_plan_data(plan)
        if recipient_view:
            survey_plan["download_path"] = (
                f"my-property/{allocation.pk}/survey-plans/{plan.pk}/download"
                if plan.document and allocation.status == Allocation.Status.ACTIVE else None
            )
        survey_plans.append(survey_plan)
    return {
        "id": allocation.pk,
        "reference": allocation.reference,
        "status": allocation.status,
        "allocated_at": allocation.allocated_at.isoformat(),
        "parcel": _parcel_data(allocation.parcel),
        "recipient_name": allocation.recipient_name,
        "recipient_email": allocation.recipient_email,
        "allottee": ({
            "id": allocation.allottee_id,
            "full_name": allocation.allottee.get_full_name() or allocation.allottee.username,
            "email": allocation.allottee.email,
        } if allocation.allottee_id else None),
        "survey_plans": survey_plans,
        "invitation": ({
            "id": str(invitation.pk),
            "status": invitation.status,
            "expires_at": invitation.expires_at.isoformat(),
            "sent_at": invitation.sent_at.isoformat() if invitation.sent_at else None,
            "failure_reason": (invitation.failure_reason or None) if include_delivery_error else None,
        } if invitation else None),
    }

def _admin_membership_data(membership):
    return {
        "id": membership.pk,
        "email": membership.user.email,
        "full_name": membership.user.get_full_name() or membership.user.username,
        "role": membership.role,
        "is_active": membership.is_active,
        "created_at": membership.created_at.isoformat(),
    }

def _invitation_data(invitation):
    return {
        "id": invitation.pk,
        "email": invitation.email,
        "status": invitation.status,
        "expires_at": invitation.expires_at.isoformat(),
        "accepted_at": invitation.accepted_at.isoformat() if invitation.accepted_at else None,
        "created_at": invitation.created_at.isoformat(),
    }

def _company_master_plan(membership, layout_id):
    return EstateMasterPlan.objects.select_related("estate", "company", "uploaded_by").filter(
        pk=layout_id,
        company=membership.company,
        estate__company=membership.company,
    ).first()

def _invitation_request_rate_limited(request, action, *, limit, window_seconds):
    address = request.META.get("REMOTE_ADDR", "unknown")
    digest = hashlib.sha256(f"{action}:{address}".encode("utf-8")).hexdigest()
    cache_key = f"allocation-invitation-rate:{digest}"
    if cache.add(cache_key, 1, timeout=window_seconds):
        return False
    try:
        attempts = cache.incr(cache_key)
    except ValueError:
        cache.add(cache_key, 1, timeout=window_seconds)
        attempts = 1
    return attempts > limit
