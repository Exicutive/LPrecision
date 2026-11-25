from django.db import migrations, models
from django.db.models import Q
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("allocations", "0002_initial"),
        ("records", "0011_remove_allocation_allocation_allottee_idx_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="allocation",
            name="parcel",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="allocations",
                to="parcels.parcel",
            ),
        ),
        migrations.AddConstraint(
            model_name="allocation",
            constraint=models.UniqueConstraint(
                condition=~Q(status="revoked"),
                fields=("parcel",),
                name="one_open_allocation_per_parcel",
            ),
        ),
    ]
