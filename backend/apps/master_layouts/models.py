from django.conf import settings
from django.db import models
from django.db.models import Q
import uuid

from apps.companies.models import Company
from apps.estates.models import Estate
from apps.parcels.models import Parcel


class EstateMasterPlan(models.Model):
    """An immutable, versioned estate-wide source layout; never a resident survey plan."""

    class Format(models.TextChoices):
        GEOJSON = "geojson", "GeoJSON"
        DXF = "dxf", "DXF"
        SHAPEFILE_ZIP = "shapefile_zip", "Shapefile ZIP"

    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        REVIEW_REQUIRED = "review_required", "Review required"
        READY_FOR_APPROVAL = "ready_for_approval", "Ready for approval"
        APPROVED = "approved", "Approved"
        FAILED = "failed", "Failed"
        SUPERSEDED = "superseded", "Superseded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="master_plans")
    estate = models.ForeignKey(Estate, on_delete=models.PROTECT, related_name="master_plans")
    original_filename = models.CharField(max_length=255)
    document = models.FileField(upload_to="estate-master-layouts/%Y/%m/")
    file_format = models.CharField(max_length=20, choices=Format.choices)
    file_size = models.PositiveBigIntegerField()
    checksum = models.CharField(max_length=64)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="master_plans_uploaded")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processing_status = models.CharField(max_length=24, choices=Status.choices, default=Status.UPLOADED)
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processing_completed_at = models.DateTimeField(null=True, blank=True)
    processing_error = models.TextField(blank=True)
    coordinate_reference_system = models.CharField(max_length=150, blank=True)
    processing_metadata = models.JSONField(default=dict, blank=True)
    version = models.PositiveIntegerField()
    is_current = models.BooleanField(default=False)

    class Meta:
        db_table = "records_estatemasterplan"
        ordering = ("estate", "-version")
        constraints = [
            models.UniqueConstraint(fields=("estate", "version"), name="unique_master_plan_version_per_estate"),
            models.UniqueConstraint(fields=("estate",), condition=Q(is_current=True), name="one_current_master_plan_per_estate"),
        ]
        indexes = [
            models.Index(fields=("company", "processing_status", "-uploaded_at"), name="master_plan_company_status_idx"),
            models.Index(fields=("estate", "-version"), name="master_plan_estate_version_idx"),
            models.Index(fields=("estate", "checksum"), name="master_plan_checksum_idx"),
        ]


class MasterLayoutProcessingJob(models.Model):
    """Durable job record; a worker may safely retry the same layout without new candidates."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        REVIEW_REQUIRED = "review_required", "Review required"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="master_layout_jobs")
    estate = models.ForeignKey(Estate, on_delete=models.PROTECT, related_name="master_layout_jobs")
    master_plan = models.ForeignKey(EstateMasterPlan, on_delete=models.PROTECT, related_name="processing_jobs")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    stage = models.CharField(max_length=100, blank=True)
    attempt = models.PositiveIntegerField(default=1)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "records_masterlayoutprocessingjob"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=("master_plan", "attempt"), name="unique_master_plan_job_attempt"),
        ]
        indexes = [
            models.Index(fields=("company", "status", "-created_at"), name="layout_job_company_status_idx"),
            models.Index(fields=("master_plan", "status"), name="layout_job_plan_status_idx"),
        ]


class ExtractedParcelCandidate(models.Model):
    """A reviewable extraction result. It becomes a usable Parcel only after approval."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        VALIDATED = "validated", "Validated"
        NEEDS_REVIEW = "needs_review", "Needs review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="extracted_parcel_candidates")
    estate = models.ForeignKey(Estate, on_delete=models.PROTECT, related_name="extracted_parcel_candidates")
    master_plan = models.ForeignKey(EstateMasterPlan, on_delete=models.PROTECT, related_name="parcel_candidates")
    source_feature_index = models.PositiveIntegerField()
    plot_number = models.CharField(max_length=60, blank=True)
    block = models.CharField(max_length=60, blank=True)
    boundary_coordinates = models.JSONField(default=list, blank=True)
    original_boundary_coordinates = models.JSONField(default=list, blank=True)
    area_sqm = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    perimeter_m = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    validation_warnings = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="parcel_candidates_reviewed")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    published_parcel = models.OneToOneField(Parcel, on_delete=models.SET_NULL, null=True, blank=True, related_name="source_candidate")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "records_extractedparcelcandidate"
        ordering = ("plot_number", "source_feature_index")
        constraints = [
            models.UniqueConstraint(fields=("master_plan", "source_feature_index"), name="unique_layout_source_feature"),
        ]
        indexes = [
            models.Index(fields=("company", "estate", "status"), name="candidate_company_estate_idx"),
            models.Index(fields=("master_plan", "status", "plot_number"), name="candidate_plan_status_idx"),
        ]
