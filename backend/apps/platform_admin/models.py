from django.conf import settings
from django.db import models

from apps.companies.models import Company


class PlatformAdministrator(models.Model):
    """An explicit platform role, deliberately separate from company access."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="platform_administrator_role",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Platform administrator: {self.user}"

    class Meta:
        db_table = "records_platformadministrator"


class PlatformSetting(models.Model):
    """Platform-wide configuration, editable only by Platform Administrators."""

    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="platform_settings_updated"
    )

    class Meta:
        db_table = "records_platformsetting"
        ordering = ("key",)


class PlatformAuditEvent(models.Model):
    """Append-only record of material platform and company administration actions."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="platform_audit_events",
    )
    company = models.ForeignKey(
        Company, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_events"
    )
    action = models.CharField(max_length=100)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "records_platformauditevent"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("company", "-created_at"), name="audit_company_created_idx"),
            models.Index(fields=("action", "-created_at"), name="audit_action_created_idx"),
        ]
