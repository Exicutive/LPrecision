import json

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase

from apps.companies.notifications import schedule_company_notification
from apps.companies.models import Company, CompanyMembership


User = get_user_model()
NOTIFICATION_TYPES = (
    "property_allocation",
    "survey_plan_upload",
    "survey_plan_verification",
    "master_layout_processing",
)


class CompanySettingsApiTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name="Terra Company",
            code="terra-company",
            email="office@terra.example",
            office_address="Existing office address",
        )
        self.other_company = Company.objects.create(
            name="Other Company",
            code="other-company",
        )
        self.admin = User.objects.create_user(
            username="admin@terra.example",
            email="admin@terra.example",
            password="A-strong-password-42!",
            first_name="Ada",
            last_name="Admin",
        )
        CompanyMembership.objects.create(company=self.company, user=self.admin)
        self.client = Client()
        self.client.force_login(self.admin)
        self.settings_url = f"/api/records/companies/{self.company.pk}/settings/"

    def post_json(self, url, payload):
        return self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_company_admin_reads_and_updates_only_company_information(self):
        viewed = self.client.get(self.settings_url)
        self.assertEqual(viewed.status_code, 200)
        self.assertEqual(viewed.json()["company"]["id"], self.company.pk)
        self.assertEqual(viewed.json()["company"]["name"], "Terra Company")
        self.assertEqual(viewed.json()["company"]["status"], Company.Status.ACTIVE)
        self.assertNotIn("office_address", viewed.json()["company"])
        self.assertNotIn("logo_url", viewed.json()["company"])

        updated = self.post_json(self.settings_url, {
            "name": "Terra Company Updated",
            "phone": "+234 800 123 4567",
            "registration_number": "RC-12345",
        })
        self.assertEqual(updated.status_code, 200)
        self.company.refresh_from_db()
        self.assertEqual(self.company.name, "Terra Company Updated")
        self.assertEqual(self.company.email, "office@terra.example")
        self.assertEqual(self.company.registration_number, "RC-12345")
        self.assertEqual(self.company.office_address, "Existing office address")
        self.assertEqual(self.other_company.name, "Other Company")

    def test_company_admin_cannot_change_company_email(self):
        response = self.post_json(
            self.settings_url,
            {"email": "different@terra.example"},
        )
        self.assertEqual(response.status_code, 400)
        self.company.refresh_from_db()
        self.assertEqual(self.company.email, "office@terra.example")

    def test_company_id_and_status_are_read_only_and_other_company_is_forbidden(self):
        protected = self.post_json(self.settings_url, {
            "name": "Changed",
            "id": self.other_company.pk,
            "status": Company.Status.SUSPENDED,
        })
        self.assertEqual(protected.status_code, 400)
        self.company.refresh_from_db()
        self.assertEqual(self.company.status, Company.Status.ACTIVE)
        self.assertEqual(self.company.name, "Terra Company")

        other = self.client.get(
            f"/api/records/companies/{self.other_company.pk}/settings/"
        )
        self.assertEqual(other.status_code, 403)

        unauthorized = Client().get(self.settings_url)
        self.assertEqual(unauthorized.status_code, 302)

    def test_company_admin_cannot_change_office_address_or_upload_logo(self):
        email_change = self.post_json(self.settings_url, {"email": "not-an-email"})
        self.assertEqual(email_change.status_code, 400)
        address_change = self.post_json(
            self.settings_url,
            {"office_address": "New office address"},
        )
        self.assertEqual(address_change.status_code, 400)
        logo_upload = self.client.post(
            self.settings_url,
            {"logo": SimpleUploadedFile("logo.png", b"not a PNG", content_type="image/png")},
        )
        self.assertEqual(logo_upload.status_code, 400)
        self.company.refresh_from_db()
        self.assertEqual(self.company.office_address, "Existing office address")
        self.assertFalse(self.company.logo)

    def test_notification_preferences_persist_and_gate_delivery(self):
        preferences = {key: key == "property_allocation" for key in NOTIFICATION_TYPES}
        saved = self.post_json(
            self.settings_url,
            {"notification_preferences": preferences},
        )
        self.assertEqual(saved.status_code, 200)
        self.company.refresh_from_db()
        self.assertEqual(
            self.company.settings["notification_preferences"],
            preferences,
        )

        with self.captureOnCommitCallbacks(execute=True):
            schedule_company_notification(
                company_id=self.company.pk,
                notification_type="property_allocation",
                subject="Allocation alert",
                message="A property was allocated.",
            )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.admin.email])

        with self.captureOnCommitCallbacks(execute=True):
            schedule_company_notification(
                company_id=self.company.pk,
                notification_type="survey_plan_upload",
                subject="Survey upload alert",
                message="A survey plan was uploaded.",
            )
        self.assertEqual(len(mail.outbox), 1)
