from django.conf import settings
from django.db import models
import uuid

from apps.companies.models import Company


class Estate(models.Model):
    """A development whose approved parcels are managed in the platform."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        ARCHIVED = "archived", "Archived"

    company = models.ForeignKey(
        Company, on_delete=models.PROTECT, related_name="estates"
    )
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=200)
    code = models.SlugField(max_length=40, unique=True)
    state = models.CharField(max_length=100)
    local_government_area = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    description = models.TextField(blank=True)
    image = models.FileField(upload_to="estate-images/%Y/%m/", blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="estates_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "records_estate"
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(fields=("company", "name"), name="unique_estate_name_per_company"),
        ]
        indexes = [
            models.Index(fields=("company", "status", "name"), name="estate_company_status_idx"),
            models.Index(fields=("company", "updated_at"), name="estate_company_updated_idx"),
        ]

    def __str__(self):
        return self.name
