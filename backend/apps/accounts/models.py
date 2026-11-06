from django.conf import settings
from django.db import models
from django.db.models.functions import Lower


class VerifiedEmail(models.Model):
    """An email address whose ownership was proven using an emailed token."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="verified_emails",
    )
    email = models.EmailField()
    verified_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="unique_verified_email_ci"),
        ]
        indexes = [
            models.Index(fields=("user", "email"), name="verified_email_user_idx"),
        ]


class EmailChangeRequest(models.Model):
    """Single-use email ownership challenge for an authenticated account change."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_change_requests",
    )
    email = models.EmailField()
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("user", "used_at", "-created_at"), name="email_change_user_idx"),
        ]
