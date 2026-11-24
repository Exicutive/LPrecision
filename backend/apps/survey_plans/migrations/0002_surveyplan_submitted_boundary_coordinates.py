from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("survey_plans", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="surveyplan",
            name="submitted_boundary_coordinates",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
