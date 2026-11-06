import uuid
import mimetypes

import django.db.models.deletion
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.validators import MinValueValidator
from django.db import migrations, models

from apps.survey_plans.storage import PrivateSurveyPlanStorage


def migrate_legacy_plans(apps, schema_editor):
    LegacySurveyPlan = apps.get_model("records", "LegacySurveyPlan")
    SurveyPlan = apps.get_model("records", "SurveyPlan")
    database = schema_editor.connection.alias
    source_storage = FileSystemStorage(location=settings.MEDIA_ROOT)
    private_storage = PrivateSurveyPlanStorage()

    for legacy in LegacySurveyPlan.objects.using(database).all().iterator():
        legacy_number = legacy.reference or legacy.name
        if SurveyPlan.objects.using(database).filter(
            company_id=legacy.company_id,
            survey_plan_number=legacy_number,
        ).exists():
            legacy_number = ""
        plan = SurveyPlan.objects.using(database).create(
            id=uuid.uuid4(),
            company_id=legacy.company_id,
            estate_id=legacy.estate_id,
            name=legacy.name,
            reference=legacy.reference,
            survey_plan_number=legacy_number,
            uploaded_by_id=legacy.uploaded_by_id,
            original_filename=(
                legacy.document.name.replace("\\", "/").rsplit("/", 1)[-1]
                if legacy.document else ""
            ),
        )
        SurveyPlan.objects.using(database).filter(pk=plan.pk).update(
            uploaded_at=legacy.uploaded_at,
            created_at=legacy.uploaded_at,
            updated_at=legacy.uploaded_at,
        )
        if legacy.document and source_storage.exists(legacy.document.name):
            with source_storage.open(legacy.document.name, "rb") as document:
                stored_name = private_storage.save(legacy.document.name, document)
            plan.document.name = stored_name
            plan.file_format = mimetypes.guess_type(legacy.document.name)[0] or ""
            plan.file_size = private_storage.size(stored_name)
            plan.save(update_fields=("document", "file_format", "file_size"))
            source_storage.delete(legacy.document.name)


class Migration(migrations.Migration):

    dependencies = [
        ("records", "0008_allocation_invitations"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="surveyplan",
            name="company",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="legacy_survey_plans",
                to="records.company",
            ),
        ),
        migrations.AlterField(
            model_name="surveyplan",
            name="estate",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="legacy_survey_plans",
                to="records.estate",
            ),
        ),
        migrations.RenameModel(
            old_name="SurveyPlan",
            new_name="LegacySurveyPlan",
        ),
        migrations.CreateModel(
            name="SurveyPlan",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("reference", models.CharField(blank=True, max_length=100)),
                ("survey_plan_number", models.CharField(blank=True, max_length=100)),
                ("surveyor_full_name", models.CharField(blank=True, max_length=200)),
                ("surveyor_registration_number", models.CharField(blank=True, max_length=100)),
                ("survey_date", models.DateField(blank=True, null=True)),
                ("state", models.CharField(blank=True, max_length=100)),
                ("local_government_area", models.CharField(blank=True, max_length=100)),
                ("location_description", models.TextField(blank=True)),
                ("stated_area", models.DecimalField(
                    blank=True, decimal_places=4, max_digits=18, null=True,
                    validators=[MinValueValidator(0)],
                )),
                ("area_unit", models.CharField(
                    blank=True,
                    choices=[
                        ("sqm", "Square metres"),
                        ("ha", "Hectares"),
                        ("acres", "Acres"),
                        ("sqft", "Square feet"),
                    ],
                    default="sqm",
                    max_length=8,
                )),
                ("coordinate_reference_system", models.CharField(blank=True, max_length=150)),
                ("datum", models.CharField(blank=True, max_length=100)),
                ("notes", models.TextField(blank=True)),
                ("original_filename", models.CharField(blank=True, max_length=255)),
                ("document", models.FileField(
                    blank=True,
                    storage=PrivateSurveyPlanStorage(),
                    upload_to="survey-plans/%Y/%m/",
                )),
                ("file_format", models.CharField(blank=True, max_length=20)),
                ("file_size", models.PositiveBigIntegerField(default=0)),
                ("checksum", models.CharField(blank=True, max_length=64)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("verification_status", models.CharField(
                    choices=[
                        ("pending", "Pending Verification"),
                        ("under_review", "Under Review"),
                        ("verified", "Verified"),
                        ("rejected", "Rejected"),
                        ("disputed", "Disputed"),
                    ],
                    default="pending",
                    max_length=20,
                )),
                ("verification_notes", models.TextField(blank=True)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("extracted_metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("allocation", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="survey_plans",
                    to="records.allocation",
                )),
                ("company", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="survey_plans",
                    to="records.company",
                )),
                ("estate", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="survey_plans",
                    to="records.estate",
                )),
                ("parcel", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="survey_plans",
                    to="records.parcel",
                )),
                ("uploaded_by", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="survey_plans_uploaded",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("verified_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="survey_plans_verified",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "ordering": ("-uploaded_at",),
                "indexes": [
                    models.Index(fields=["company", "estate", "-uploaded_at"], name="survey_company_estate_idx"),
                    models.Index(fields=["company", "verification_status"], name="survey_company_status_idx"),
                    models.Index(fields=["allocation", "verification_status"], name="survey_alloc_status_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        condition=~models.Q(("survey_plan_number", "")),
                        fields=("company", "survey_plan_number"),
                        name="survey_company_plan_number_uniq",
                    ),
                    models.UniqueConstraint(
                        condition=models.Q(("allocation__isnull", False)) & ~models.Q(("checksum", "")),
                        fields=("allocation", "checksum"),
                        name="survey_allocation_checksum_uniq",
                    ),
                ],
            },
        ),
        migrations.RunPython(migrate_legacy_plans, migrations.RunPython.noop),
        migrations.DeleteModel(name="LegacySurveyPlan"),
        migrations.CreateModel(
            name="SurveyPlanVerificationEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("previous_status", models.CharField(blank=True, max_length=20)),
                ("new_status", models.CharField(
                    choices=[
                        ("pending", "Pending Verification"),
                        ("under_review", "Under Review"),
                        ("verified", "Verified"),
                        ("rejected", "Rejected"),
                        ("disputed", "Disputed"),
                    ],
                    max_length=20,
                )),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="survey_plan_verification_events",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("survey_plan", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="verification_history",
                    to="records.surveyplan",
                )),
            ],
            options={
                "ordering": ("-created_at",),
                "indexes": [
                    models.Index(fields=["survey_plan", "-created_at"], name="survey_verify_plan_date_idx"),
                ],
            },
        ),
    ]
