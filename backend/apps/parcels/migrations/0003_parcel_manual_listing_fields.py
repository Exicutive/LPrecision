from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("parcels", "0002_parcel_boundary_coordinate_reference_system"),
    ]

    operations = [
        migrations.AddField(
            model_name="parcel",
            name="name",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="parcel",
            name="plot_details",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="parcel",
            name="special_requests",
            field=models.TextField(blank=True),
        ),
    ]
