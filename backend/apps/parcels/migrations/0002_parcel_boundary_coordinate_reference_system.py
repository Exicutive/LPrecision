from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("parcels", "0001_initial"),
        ("records", "0011_remove_allocation_allocation_allottee_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="parcel",
            name="boundary_coordinate_reference_system",
            field=models.CharField(blank=True, max_length=50),
        ),
    ]
