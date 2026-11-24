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
from apps.survey_plans.models import SurveyPlan


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
        self.recipient_client = Client()
        self.recipient_client.force_login(self.recipient)

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
            "coordinate_reference_system": "EPSG:4326",
            "datum": "WGS 84",
            "notes": "Manual metadata entry",
        }
        values.update(overrides)
        values["document"] = document or SimpleUploadedFile(
            "plot-100.pdf",
            b"%PDF-1.4\nSurvey plan content",
            content_type="application/pdf",
        )
        return values

    def upload_url(self, allocation_id=None):
        return f"/api/records/my-property/{allocation_id or self.allocation.pk}/survey-plans/"

    def track_uploaded_file(self, response):
        plan = SurveyPlan.objects.get(pk=response.json()["survey_plan"]["id"])
        storage = plan.document.storage
        filename = plan.document.name
        self.addCleanup(storage.delete, filename)
        return plan

    def test_property_holder_uploads_pdf_linked_to_own_allocation(self):
        response = self.recipient_client.post(self.upload_url(), self.upload_data())
        self.assertEqual(response.status_code, 201)
        plan = self.track_uploaded_file(response)
        self.assertEqual(plan.allocation_id, self.allocation.pk)
        self.assertEqual(plan.parcel_id, self.parcel.pk)
        self.assertEqual(plan.estate_id, self.estate.pk)
        self.assertEqual(plan.company_id, self.company.pk)
        self.assertEqual(plan.area_unit, SurveyPlan.AreaUnit.SQUARE_METRES)
        self.assertEqual(plan.extracted_metadata["status"], "manual_required")

    def test_upload_requires_authenticated_linked_property_holder(self):
        anonymous = Client().post(self.upload_url(), self.upload_data())
        self.assertEqual(anonymous.status_code, 302)

        forbidden = self.client.post(self.upload_url(), self.upload_data())
        self.assertEqual(forbidden.status_code, 404)

    def test_upload_rejects_unrelated_allocation_and_invalid_or_missing_pdf(self):
        invalid_pdf = self.recipient_client.post(
            self.upload_url(),
            self.upload_data(document=SimpleUploadedFile("image.pdf", b"not a PDF")),
        )
        self.assertEqual(invalid_pdf.status_code, 400)

        missing_metadata = self.recipient_client.post(
            self.upload_url(),
            self.upload_data(survey_plan_number=""),
        )
        self.assertEqual(missing_metadata.status_code, 400)

        missing_file = self.recipient_client.post(
            self.upload_url(),
            {key: value for key, value in self.upload_data().items() if key != "document"},
        )
        self.assertEqual(missing_file.status_code, 400)

    def test_duplicate_upload_for_same_allocation_is_idempotent(self):
        first = self.recipient_client.post(self.upload_url(), self.upload_data())
        self.assertEqual(first.status_code, 201)
        plan = self.track_uploaded_file(first)

        repeated = self.recipient_client.post(self.upload_url(), self.upload_data())
        self.assertEqual(repeated.status_code, 200)
        self.assertTrue(repeated.json()["duplicate"])
        self.assertEqual(repeated.json()["survey_plan"]["id"], str(plan.pk))
        self.assertEqual(SurveyPlan.objects.filter(allocation=self.allocation).count(), 1)

    def test_upload_updates_boundary_immediately_and_company_verification_is_unavailable(self):
        response = self.recipient_client.post(
            self.upload_url(), self.upload_data(boundary_coordinates="[[3.4, 6.4], [3.5, 6.4], [3.5, 6.5]]")
        )
        plan = self.track_uploaded_file(response)

        self.parcel.refresh_from_db()
        self.assertEqual(self.parcel.boundary_coordinates, [[3.4, 6.4], [3.5, 6.4], [3.5, 6.5]])
        self.assertEqual(self.parcel.boundary_coordinate_reference_system, "EPSG:4326")

        result = self.client.post(
            f"/api/records/companies/{self.company.pk}/survey-plans/{plan.pk}/verify/",
            data=json.dumps({"status": "verified", "notes": "Reviewed against submitted document."}),
            content_type="application/json",
        )
        self.assertEqual(result.status_code, 404)

    def test_property_holder_can_submit_wgs84_coordinates_without_a_pdf(self):
        response = self.recipient_client.post(
            f"/api/records/my-property/{self.allocation.pk}/boundary/",
            data=json.dumps({
                "coordinate_reference_system": "EPSG:4326",
                "boundary_coordinates": [[3.4, 6.4], [3.4005, 6.4], [3.4005, 6.4005]],
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.parcel.refresh_from_db()
        self.assertEqual(self.parcel.boundary_coordinate_reference_system, "EPSG:4326")
        self.assertEqual(len(self.parcel.boundary_coordinates), 3)

    def test_boundary_coordinates_require_wgs84_and_a_simple_polygon(self):
        missing_crs = self.recipient_client.post(
            f"/api/records/my-property/{self.allocation.pk}/boundary/",
            data=json.dumps({"boundary_coordinates": [[3.4, 6.4], [3.5, 6.4], [3.5, 6.5]]}),
            content_type="application/json",
        )
        self.assertEqual(missing_crs.status_code, 400)
        self.assertIn("WGS84", missing_crs.json()["detail"])

        crossing = self.recipient_client.post(
            f"/api/records/my-property/{self.allocation.pk}/boundary/",
            data=json.dumps({
                "coordinate_reference_system": "EPSG:4326",
                "boundary_coordinates": [[3.4, 6.4], [3.5, 6.5], [3.4, 6.5], [3.5, 6.4]],
            }),
            content_type="application/json",
        )
        self.assertEqual(crossing.status_code, 400)

    def test_recipient_download_is_scoped(self):
        uploaded = self.recipient_client.post(self.upload_url(), self.upload_data())
        plan = self.track_uploaded_file(uploaded)

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
