import django.db.models.functions.text
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="VerifiedEmail",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=254)),
                ("verified_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="verified_emails",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
        migrations.AddConstraint(
            model_name="verifiedemail",
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower("email"),
                name="unique_verified_email_ci",
            ),
        ),
        migrations.AddIndex(
            model_name="verifiedemail",
            index=models.Index(fields=["user", "email"], name="verified_email_user_idx"),
        ),
    ]
