import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def assign_estate_public_ids_and_statuses(apps, schema_editor):
    Estate = apps.get_model("records", "Estate")
    for estate in Estate.objects.filter(public_id__isnull=True).iterator():
        estate.public_id = uuid.uuid4()
        estate.status = "active" if estate.is_active else "inactive"
        estate.save(update_fields=("public_id", "status"))


class Migration(migrations.Migration):
    dependencies = [("records", "0004_company_contact_person_company_email_company_phone_and_more")]

    operations = [
        migrations.AddField(
            model_name="estate",
            name="created_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="estates_created", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(model_name="estate", name="description", field=models.TextField(blank=True)),
        migrations.AddField(model_name="estate", name="image", field=models.FileField(blank=True, upload_to="estate-images/%Y/%m/")),
        migrations.AddField(model_name="estate", name="public_id", field=models.UUIDField(editable=False, null=True)),
        migrations.AddField(
            model_name="estate",
            name="status",
            field=models.CharField(choices=[("active", "Active"), ("inactive", "Inactive"), ("archived", "Archived")], default="active", max_length=12),
        ),
        migrations.RunPython(assign_estate_public_ids_and_statuses, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="estate",
            name="company",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="estates", to="records.company"),
        ),
        migrations.AlterField(
            model_name="estate",
            name="public_id",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AddConstraint(
            model_name="estate",
            constraint=models.UniqueConstraint(fields=("company", "name"), name="unique_estate_name_per_company"),
        ),
    ]
