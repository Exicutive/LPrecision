from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
import uuid

from apps.allocations.models import Allocation
from apps.companies.models import Company
from apps.estates.models import Estate
from apps.parcels.models import Parcel
from apps.survey_plans.storage import PrivateSurveyPlanStorage


class SurveyPlan(models.Model):
    """A survey document associated with one allocated parcel."""

    class AreaUnit(models.TextChoices):
        SQUARE_METRES = "sqm", "Square metres"
        HECTARES = "ha", "Hectares"
        ACRES = "acres", "Acres"
        SQUARE_FEET = "sqft", "Square feet"

    class VerificationStatus(models.TextChoices):
        PENDING = "pending", "Pending Verification"
        UNDER_REVIEW = "under_review", "Under Review"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"
        DISPUTED = "disputed", "Disputed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="survey_plans")
    estate = models.ForeignKey(Estate, on_delete=models.PROTECT, related_name="survey_plans")
    parcel = models.ForeignKey(
        Parcel, on_delete=models.PROTECT, related_name="survey_plans", null=True, blank=True
    )
    allocation = models.ForeignKey(
        Allocation, on_delete=models.PROTECT, related_name="survey_plans", null=True, blank=True
    )
    name = models.CharField(max_length=255)
    reference = models.CharField(max_length=100, blank=True)
    survey_plan_number = models.CharField(max_length=100, blank=True)
    surveyor_full_name = models.CharField(max_length=200, blank=True)
    surveyor_registration_number = models.CharField(max_length=100, blank=True)
    survey_date = models.DateField(null=True, blank=True)
    state = models.CharField(max_length=100, blank=True)
    local_government_area = models.CharField(max_length=100, blank=True)
    location_description = models.TextField(blank=True)
    stated_area = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    area_unit = models.CharField(
        max_length=8, choices=AreaUnit.choices, default=AreaUnit.SQUARE_METRES, blank=True
    )
    coordinate_reference_system = models.CharField(max_length=150, blank=True)
    datum = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    original_filename = models.CharField(max_length=255, blank=True)
    document = models.FileField(
        upload_to="survey-plans/%Y/%m/", storage=PrivateSurveyPlanStorage(), blank=True
    )
    file_format = models.CharField(max_length=20, blank=True)
    file_size = models.PositiveBigIntegerField(default=0)
    checksum = models.CharField(max_length=64, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="survey_plans_uploaded"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    verification_notes = models.TextField(blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="survey_plans_verified",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    extracted_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "records_surveyplan"
        ordering = ("-uploaded_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("company", "survey_plan_number"),
                condition=~Q(survey_plan_number=""),
                name="survey_company_plan_number_uniq",
            ),
            models.UniqueConstraint(
                fields=("allocation", "checksum"),
                condition=Q(allocation__isnull=False) & ~Q(checksum=""),
                name="survey_allocation_checksum_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=("company", "estate", "-uploaded_at"), name="survey_company_estate_idx"),
            models.Index(fields=("company", "verification_status"), name="survey_company_status_idx"),
            models.Index(fields=("allocation", "verification_status"), name="survey_alloc_status_idx"),
        ]

    def clean(self):
        super().clean()
        if self.estate_id and self.company_id and self.estate.company_id != self.company_id:
            raise ValidationError("The survey plan estate must belong to its company.")
        if self.parcel_id and self.estate_id and self.parcel.estate_id != self.estate_id:
            raise ValidationError("The survey plan parcel must belong to its estate.")
        if self.allocation_id:
            if self.allocation.parcel_id != self.parcel_id:
                raise ValidationError("The survey plan allocation must match its parcel.")
            if self.allocation.parcel.estate_id != self.estate_id:
                raise ValidationError("The survey plan allocation must belong to its estate.")
            if self.allocation.parcel.estate.company_id != self.company_id:
                raise ValidationError("The survey plan allocation must belong to its company.")

    def save(self, *args, **kwargs):
        self.full_clean(exclude=("document",))
        return super().save(*args, **kwargs)


class SurveyPlanVerificationEvent(models.Model):
    survey_plan = models.ForeignKey(
        SurveyPlan, on_delete=models.PROTECT, related_name="verification_history"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="survey_plan_verification_events",
    )
    previous_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, choices=SurveyPlan.VerificationStatus.choices)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "records_surveyplanverificationevent"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("survey_plan", "-created_at"), name="survey_verify_plan_date_idx"),
        ]
