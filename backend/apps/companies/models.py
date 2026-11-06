from django.conf import settings
from django.db import models


class Company(models.Model):
    """A customer organisation that owns its own operational records."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"

    class SetupStatus(models.TextChoices):
        PENDING = "pending_setup", "Pending setup"
        COMPLETE = "complete", "Complete"

    name = models.CharField(max_length=200, unique=True)
    code = models.SlugField(max_length=40, unique=True)
    legal_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    contact_person = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    registration_number = models.CharField(max_length=100, blank=True)
    office_address = models.TextField(blank=True)
    logo = models.FileField(upload_to="company-logos/%Y/%m/", blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    setup_status = models.CharField(
        max_length=20, choices=SetupStatus.choices, default=SetupStatus.PENDING
    )
    settings = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "records_company"
        ordering = ("name",)
        indexes = [
            models.Index(fields=("status", "name"), name="company_status_name_idx"),
        ]

    def __str__(self):
        return self.name


class CompanyMembership(models.Model):
    """A user's administrative relationship with one company."""

    class Role(models.TextChoices):
        COMPANY_ADMIN = "company_admin", "Company administrator"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="company_memberships",
    )
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.COMPANY_ADMIN)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "records_companymembership"
        constraints = [
            models.UniqueConstraint(fields=("company", "user", "role"), name="unique_company_role"),
        ]
        indexes = [
            models.Index(fields=("user", "role", "is_active"), name="membership_access_idx"),
            models.Index(fields=("company", "role", "is_active"), name="membership_company_idx"),
        ]

    def __str__(self):
        return f"{self.user} — {self.company} ({self.role})"


class CompanyAdminInvitation(models.Model):
    """One-time, email-bound invitation for an initial company administrator."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REVOKED = "revoked", "Revoked"
        EXPIRED = "expired", "Expired"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="admin_invitations")
    email = models.EmailField()
    token_hash = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="company_admin_invitations_sent",
    )
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "records_companyadmininvitation"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("company", "status", "expires_at"), name="admin_invite_company_idx"),
            models.Index(fields=("email", "status"), name="admin_invite_email_idx"),
        ]
