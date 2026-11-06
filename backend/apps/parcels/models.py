from django.core.validators import MinValueValidator
from django.db import models
import uuid

from apps.estates.models import Estate


class Parcel(models.Model):
    """An approved parcel record. Boundary data is optional until imported."""

    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        RESERVED = "reserved", "Reserved"
        ALLOCATED = "allocated", "Allocated"
        ARCHIVED = "archived", "Archived"

    estate = models.ForeignKey(Estate, on_delete=models.PROTECT, related_name="parcels")
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    plot_number = models.CharField(max_length=60)
    block = models.CharField(max_length=60, blank=True)
    area_sqm = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    property_type = models.CharField(max_length=100, blank=True)
    features = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.AVAILABLE)
    survey_reference = models.CharField(max_length=100, blank=True)
    boundary_coordinates = models.JSONField(default=list, blank=True)
    original_boundary_coordinates = models.JSONField(default=list, blank=True)
    perimeter_m = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    source_master_plan = models.ForeignKey(
        "master_layouts.EstateMasterPlan", on_delete=models.PROTECT, null=True, blank=True, related_name="published_parcels"
    )
    extraction_status = models.CharField(max_length=16, default="approved")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "records_parcel"
        ordering = ("estate__name", "block", "plot_number")
        constraints = [
            models.UniqueConstraint(
                fields=("estate", "plot_number"),
                name="unique_plot_number_per_estate",
            )
        ]
        indexes = [
            models.Index(fields=("estate", "status"), name="parcel_estate_status_idx"),
            models.Index(fields=("status", "updated_at"), name="parcel_status_updated_idx"),
        ]

    def __str__(self):
        return f"{self.estate.name} — {self.plot_number}"
