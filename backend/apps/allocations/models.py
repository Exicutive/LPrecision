from django.conf import settings
from django.db import models
import uuid

from apps.companies.models import Company
from apps.parcels.models import Parcel


class Allocation(models.Model):
    """The current authenticated-user access relationship for a parcel."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        REVOKED = "revoked", "Revoked"

    reference = models.CharField(max_length=50, unique=True)
    parcel = models.OneToOneField(Parcel, on_delete=models.PROTECT, related_name="allocation")
    recipient_name = models.CharField(max_length=200)
    recipient_email = models.EmailField()
    allottee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="property_allocations",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    allocated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "records_allocation"
        ordering = ("-allocated_at",)
        indexes = [
            models.Index(fields=("allottee", "status"), name="allocation_allottee_idx"),
            models.Index(fields=("status", "-allocated_at"), name="allocation_status_date_idx"),
        ]

    def __str__(self):
        return self.reference


class AllocationInvitation(models.Model):
    """Email-bound, one-time claim link for an allocation."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        ACCEPTED = "accepted", "Accepted"
        EXPIRED = "expired", "Expired"
        REVOKED = "revoked", "Revoked"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    allocation = models.ForeignKey(
        Allocation, on_delete=models.PROTECT, related_name="invitations"
    )
    recipient_email = models.EmailField()
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    sent_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "records_allocationinvitation"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("allocation", "status", "-created_at"), name="allocation_invite_status_idx"),
            models.Index(fields=("recipient_email", "status"), name="allocation_invite_email_idx"),
        ]


class PropertyInvitation(models.Model):
    """A property invitation never creates an administrative membership."""

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="property_invitations")
    parcel = models.ForeignKey(Parcel, on_delete=models.CASCADE, related_name="property_invitations")
    email = models.EmailField()
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "records_propertyinvitation"
        indexes = [
            models.Index(fields=("company", "email", "expires_at"), name="property_invite_lookup_idx"),
        ]
