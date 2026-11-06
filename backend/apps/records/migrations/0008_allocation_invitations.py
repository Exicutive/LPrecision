import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def populate_allocation_recipients(apps, _schema_editor):
    Allocation = apps.get_model("records", "Allocation")
    for allocation in Allocation.objects.select_related("allottee").iterator():
        recipient = allocation.allottee
        allocation.recipient_name = (
            " ".join(part for part in (recipient.first_name, recipient.last_name) if part)
            or recipient.username
            or "Property recipient"
        )[:200]
        allocation.recipient_email = recipient.email or (
            f"legacy-allocation-{allocation.pk}@invalid.local"
        )
        allocation.save(update_fields=("recipient_name", "recipient_email"))


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("records", "0007_parcel_extraction_status_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="parcel",
            name="property_type",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="parcel",
            name="features",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name="allocation",
            name="allottee",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="property_allocations",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="allocation",
            name="recipient_name",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.AddField(
            model_name="allocation",
            name="recipient_email",
            field=models.EmailField(blank=True, default="", max_length=254),
        ),
        migrations.RunPython(populate_allocation_recipients, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="allocation",
            name="recipient_name",
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name="allocation",
            name="recipient_email",
            field=models.EmailField(max_length=254),
        ),
        migrations.CreateModel(
            name="AllocationInvitation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("recipient_email", models.EmailField(max_length=254)),
                ("token_hash", models.CharField(max_length=64, unique=True)),
                ("expires_at", models.DateTimeField()),
                ("status", models.CharField(
                    choices=[
                        ("pending", "Pending"),
                        ("sent", "Sent"),
                        ("accepted", "Accepted"),
                        ("expired", "Expired"),
                        ("revoked", "Revoked"),
                        ("failed", "Failed"),
                    ],
                    default="pending",
                    max_length=10,
                )),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("accepted_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("failure_reason", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("allocation", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="invitations",
                    to="records.allocation",
                )),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddIndex(
            model_name="allocationinvitation",
            index=models.Index(
                fields=["allocation", "status", "-created_at"],
                name="allocation_invite_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="allocationinvitation",
            index=models.Index(
                fields=["recipient_email", "status"],
                name="allocation_invite_email_idx",
            ),
        ),
    ]
