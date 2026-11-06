import json
import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase

from apps.allocations.models import Allocation
from apps.companies.models import Company, CompanyMembership
from apps.estates.models import Estate
from apps.parcels.models import Parcel
from apps.survey_plans.models import SurveyPlan, SurveyPlanVerificationEvent


User = get_user_model()


class SurveyPlanWorkflowTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Survey Company", code="survey-company")
        self.other_company = Company.objects.create(name="Other Survey Co", code="other-survey")
        self.admin = User.objects.create_user(
            username="survey-admin@example.com",
            email="survey-admin@example.com",
            password="Secure-pass-482!",
        )
        self.other_admin = User.objects.create_user(
            username="other-admin@example.com",
            email="other-admin@example.com",
            password="Secure-pass-482!",
        )
        self.recipient = User.objects.create_user(
            username="survey-recipient@example.com",
            email="survey-recipient@example.com",
            password="Secure-pass-482!",
        )
        CompanyMembership.objects.create(company=self.company, user=self.admin)
        CompanyMembership.objects.create(company=self.other_company, user=self.other_admin)
        self.estate = Estate.objects.create(
            company=self.company, name="Survey Estate", code="survey-estate", state="Lagos"
        )
        self.other_estate = Estate.objects.create(
            company=self.other_company, name="Other Estate", code="other-estate", state="Oyo"
        )
        self.parcel = Parcel.objects.create(
            estate=self.estate, plot_number="P-100", block="B", status=Parcel.Status.ALLOCATED
        )
        self.other_parcel = Parcel.objects.create(
            estate=self.other_estate, plot_number="P-200", status=Parcel.Status.ALLOCATED
        )
        self.allocation = Allocation.objects.create(
            parcel=self.parcel,
            reference="SURVEY-ALLOC-100",
            recipient_name="Survey Recipient",
            recipient_email=self.recipient.email,
            allottee=self.recipient,
            status=Allocation.Status.ACTIVE,
        )
        self.other_allocation = Allocation.objects.create(
            parcel=self.other_parcel,
            reference="SURVEY-ALLOC-200",
            recipient_name="Survey Recipient",
            recipient_email=self.recipient.email,
            allottee=self.recipient,
            status=Allocation.Status.ACTIVE,
        )
        self.client = Client()
        self.client.force_login(self.admin)

    def upload_data(self, *, allocation_id=None, document=None, **overrides):
        values = {
            "allocation_id": str(allocation_id or self.allocation.pk),
            "survey_plan_number": "SP-100",
            "surveyor_full_name": "A. Surveyor",
            "surveyor_registration_number": "REG-100",
            "survey_date": "2026-10-20",
            "stated_area": "650.2500",
            "area_unit": SurveyPlan.AreaUnit.SQUARE_METRES,
            "state": "Lagos",
            "local_government_area": "Eti-Osa",
            "location_description": "Plot 100, Survey Estate",
            "coordinate_reference_system": "",
            "datum": "",
            "notes": "Manual metadata entry",
        }
        values.update(overrides)
        values["document"] = document or SimpleUploadedFile(
            "plot-100.pdf",
            b"%PDF-1.4\nSurvey plan content",
            content_type="application/pdf",
        )
        return values

    def upload_url(self, company_id=None):
        return f"/api/records/companies/{company_id or self.company.pk}/survey-plans/"

    def track_uploaded_file(self, response):
        plan = SurveyPlan.objects.get(pk=response.json()["survey_plan"]["id"])
        storage = plan.document.storage
        filename = plan.document.name
        self.addCleanup(storage.delete, filename)
        return plan

    def test_company_admin_uploads_pdf_linked_to_allocation(self):
        response = self.client.post(self.upload_url(), self.upload_data())
        self.assertEqual(response.status_code, 201)
        plan = self.track_uploaded_file(response)
        self.assertEqual(plan.allocation_id, self.allocation.pk)
        self.assertEqual(plan.parcel_id, self.parcel.pk)
        self.assertEqual(plan.estate_id, self.estate.pk)
        self.assertEqual(plan.company_id, self.company.pk)
        self.assertEqual(plan.verification_status, SurveyPlan.VerificationStatus.PENDING)
        self.assertEqual(plan.area_unit, SurveyPlan.AreaUnit.SQUARE_METRES)
        self.assertEqual(plan.extracted_metadata["status"], "manual_required")

    def test_upload_requires_authentication_and_company_membership(self):
        anonymous = Client().post(self.upload_url(), self.upload_data())
        self.assertEqual(anonymous.status_code, 302)

        forbidden = self.client.post(
            self.upload_url(self.other_company.pk), self.upload_data()
        )
        self.assertEqual(forbidden.status_code, 403)

    def test_upload_rejects_unrelated_allocation_and_invalid_or_missing_pdf(self):
        unrelated = self.client.post(
            self.upload_url(), self.upload_data(allocation_id=self.other_allocation.pk)
        )
        self.assertEqual(unrelated.status_code, 400)
        self.assertIn("allocation", unrelated.json()["detail"].lower())

        invalid_pdf = self.client.post(
            self.upload_url(),
            self.upload_data(document=SimpleUploadedFile("image.pdf", b"not a PDF")),
        )
        self.assertEqual(invalid_pdf.status_code, 400)

        missing_metadata = self.client.post(
            self.upload_url(),
            self.upload_data(survey_plan_number=""),
        )
        self.assertEqual(missing_metadata.status_code, 400)

        missing_file = self.client.post(
            self.upload_url(),
            {key: value for key, value in self.upload_data().items() if key != "document"},
        )
        self.assertEqual(missing_file.status_code, 400)

    def test_duplicate_upload_for_same_allocation_is_idempotent(self):
        first = self.client.post(self.upload_url(), self.upload_data())
        self.assertEqual(first.status_code, 201)
        plan = self.track_uploaded_file(first)

        repeated = self.client.post(self.upload_url(), self.upload_data())
        self.assertEqual(repeated.status_code, 200)
        self.assertTrue(repeated.json()["duplicate"])
        self.assertEqual(repeated.json()["survey_plan"]["id"], str(plan.pk))
        self.assertEqual(SurveyPlan.objects.filter(allocation=self.allocation).count(), 1)

    def test_verification_history_records_each_company_admin_change(self):
        response = self.client.post(self.upload_url(), self.upload_data())
        plan = self.track_uploaded_file(response)

        result = self.client.post(
            f"/api/records/companies/{self.company.pk}/survey-plans/{plan.pk}/verify/",
            data=json.dumps({"status": "verified", "notes": "Reviewed against submitted document."}),
            content_type="application/json",
        )
        self.assertEqual(result.status_code, 200)
        plan.refresh_from_db()
        self.assertEqual(plan.verification_status, SurveyPlan.VerificationStatus.VERIFIED)
        self.assertEqual(plan.verified_by_id, self.admin.pk)
        self.assertEqual(SurveyPlanVerificationEvent.objects.filter(survey_plan=plan).count(), 1)

        reopened = self.client.post(
            f"/api/records/companies/{self.company.pk}/survey-plans/{plan.pk}/verify/",
            data=json.dumps({"status": "under_review", "notes": "Reopened for follow-up."}),
            content_type="application/json",
        )
        self.assertEqual(reopened.status_code, 200)
        self.assertEqual(SurveyPlanVerificationEvent.objects.filter(survey_plan=plan).count(), 2)

    def test_company_and_recipient_downloads_are_scoped(self):
        uploaded = self.client.post(self.upload_url(), self.upload_data())
        plan = self.track_uploaded_file(uploaded)

        other_admin_client = Client()
        other_admin_client.force_login(self.other_admin)
        denied_admin_download = other_admin_client.get(
            f"/api/records/companies/{self.company.pk}/survey-plans/{plan.pk}/download/"
        )
        self.assertEqual(denied_admin_download.status_code, 403)

        correct_recipient_client = Client()
        correct_recipient_client.force_login(self.recipient)
        permitted = correct_recipient_client.get(
            f"/api/records/my-property/{self.allocation.pk}/survey-plans/{plan.pk}/download/"
        )
        self.assertEqual(permitted.status_code, 200)
        self.assertEqual(b"".join(permitted.streaming_content), b"%PDF-1.4\nSurvey plan content")

        inline_permitted = correct_recipient_client.get(
            f"/api/records/my-property/{self.allocation.pk}/survey-plans/{plan.pk}/download/?inline=1"
        )
        self.assertEqual(inline_permitted.status_code, 200)
        self.assertEqual(inline_permitted["Content-Type"], "application/pdf")
        self.assertIn("inline", inline_permitted["Content-Disposition"])
        self.assertEqual(
            inline_permitted["Content-Security-Policy"],
            "sandbox; default-src 'none'",
        )
        b"".join(inline_permitted.streaming_content)

        unrelated_allocation = correct_recipient_client.get(
            f"/api/records/my-property/{self.other_allocation.pk}/survey-plans/{plan.pk}/download/"
        )
        self.assertEqual(unrelated_allocation.status_code, 404)

        another_user = User.objects.create_user(
            username="another-recipient@example.com",
            email="another-recipient@example.com",
            password="Secure-pass-482!",
        )
        wrong_recipient_client = Client()
        wrong_recipient_client.force_login(another_user)
        denied_recipient = wrong_recipient_client.get(
            f"/api/records/my-property/{self.allocation.pk}/survey-plans/{plan.pk}/"
        )
        self.assertEqual(denied_recipient.status_code, 404)

    def test_model_rejects_cross_estate_parcel_relationship(self):
        plan = SurveyPlan(
            company=self.company,
            estate=self.estate,
            parcel=self.other_parcel,
            allocation=self.other_allocation,
            name="Invalid association",
            survey_plan_number="SP-CROSS",
            uploaded_by=self.admin,
        )
        with self.assertRaises(ValidationError):
            plan.full_clean(exclude=("document",))
