import hashlib
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from apps.allocations.models import Allocation, AllocationInvitation
from apps.platform_admin.models import PlatformAuditEvent


logger = logging.getLogger(__name__)


def create_allocation_invitation(allocation):
    raw_token = secrets.token_urlsafe(32)
    expiry_days = settings.ALLOCATION_INVITATION_EXPIRY_DAYS
    invitation = AllocationInvitation.objects.create(
        allocation=allocation,
        recipient_email=allocation.recipient_email,
        token_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
        expires_at=timezone.now() + timedelta(days=expiry_days),
    )
    return invitation, raw_token


def allocation_invitation_url(raw_token):
    return (
        f"{settings.FRONTEND_URL}/property/"
        f"?allocation_invitation={raw_token}"
    )


def deliver_allocation_invitation(invitation_id, raw_token):
    """Deliver after commit and persist a visible outcome without undoing allocation."""
    invitation = (
        AllocationInvitation.objects.select_related(
            "allocation__parcel__estate__company",
            "allocation__allottee",
        )
        .filter(pk=invitation_id)
        .first()
    )
    if not invitation or invitation.status != AllocationInvitation.Status.PENDING:
        return

    allocation = invitation.allocation
    parcel = allocation.parcel
    estate = parcel.estate
    company = estate.company
    try:
        invitation_url = allocation_invitation_url(raw_token)
        context = {
            "recipient_name": allocation.recipient_name,
            "recipient_email": invitation.recipient_email,
            "company_name": company.name,
            "estate_name": estate.name,
            "plot_number": parcel.plot_number,
            "block": parcel.block or "Not specified",
            "plot_size": f"{parcel.area_sqm} m²" if parcel.area_sqm is not None else "Not recorded",
            "property_type": parcel.property_type or "Not specified",
            "features": parcel.features if isinstance(parcel.features, list) else [parcel.features],
            "allocated_at": timezone.localtime(allocation.allocated_at).strftime("%B %d, %Y"),
            "invitation_url": invitation_url,
        }
        subject = f"Your Property Allocation on TerraLedger — {estate.name}"
        text_body = render_to_string(
            "allocations/emails/allocation_invitation.txt", context
        )
        html_body = render_to_string(
            "allocations/emails/allocation_invitation.html", context
        )
        message = EmailMultiAlternatives(
            subject,
            text_body,
            settings.DEFAULT_FROM_EMAIL,
            [invitation.recipient_email],
        )
        message.attach_alternative(html_body, "text/html")
        if message.send(fail_silently=False) != 1:
            raise RuntimeError("The email provider did not accept the message.")
    except Exception as error:
        failure_reason = str(error) or error.__class__.__name__
        logger.exception("Allocation invitation email delivery failed.")
        with transaction.atomic():
            AllocationInvitation.objects.filter(
                pk=invitation.pk,
                status=AllocationInvitation.Status.PENDING,
            ).update(
                status=AllocationInvitation.Status.FAILED,
                failure_reason=failure_reason[:2000],
            )
            PlatformAuditEvent.objects.create(
                actor=None,
                company=company,
                action="allocation_invitation.delivery_failed",
                details={
                    "allocation_id": allocation.pk,
                    "invitation_id": str(invitation.pk),
                    "failure_reason": failure_reason[:500],
                },
            )
        return

    sent_at = timezone.now()
    with transaction.atomic():
        updated = AllocationInvitation.objects.filter(
            pk=invitation.pk,
            status=AllocationInvitation.Status.PENDING,
        ).update(
            status=AllocationInvitation.Status.SENT,
            sent_at=sent_at,
            failure_reason="",
        )
        if updated:
            PlatformAuditEvent.objects.create(
                actor=None,
                company=company,
                action="allocation_invitation.delivered",
                details={
                    "allocation_id": allocation.pk,
                    "invitation_id": str(invitation.pk),
                },
            )


def schedule_allocation_invitation_delivery(invitation, raw_token):
    transaction.on_commit(
        lambda: deliver_allocation_invitation(invitation.pk, raw_token)
    )
