import json
import hashlib
import re
from datetime import timedelta
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from apps.accounts.models import VerifiedEmail

from apps.allocations.models import Allocation, AllocationInvitation
from apps.companies.models import Company, CompanyMembership
from apps.estates.models import Estate
from apps.master_layouts.models import EstateMasterPlan, ExtractedParcelCandidate
from apps.parcels.models import Parcel
from apps.platform_admin.models import PlatformAdministrator


User = get_user_model()


class AdministrativeHierarchyTests(TestCase):
    def setUp(self):
        self.platform_user = User.objects.create_user(
            username="platform@example.com", email="platform@example.com", password="Strong-pass-42!"
        )
        PlatformAdministrator.objects.create(user=self.platform_user)
        self.company_one = Company.objects.create(name="First Land Ltd", code="first-land")
        self.company_two = Company.objects.create(name="Second Land Ltd", code="second-land")
        self.admin_one = User.objects.create_user(
            username="one@example.com", email="one@example.com", password="Strong-pass-42!"
        )
        CompanyMembership.objects.create(company=self.company_one, user=self.admin_one)
        self.estate_one = Estate.objects.create(
            company=self.company_one, name="First Estate", code="first-estate", state="Lagos"
        )
        self.estate_two = Estate.objects.create(
            company=self.company_two, name="Second Estate", code="second-estate", state="Oyo"
        )
        self.parcel_one = Parcel.objects.create(estate=self.estate_one, plot_number="A-1")
        self.parcel_two = Parcel.objects.create(estate=self.estate_two, plot_number="B-1")

    def post(self, client, url, payload):
        return client.post(url, data=json.dumps(payload), content_type="application/json")

    def patch(self, client, url, payload):
        return client.patch(url, data=json.dumps(payload), content_type="application/json")

    def estate_payload(self, name="Meridian Gardens", **overrides):
        payload = {
            "name": name,
            "address": "12 Meridian Drive, Lekki",
            "state": "Lagos",
            "local_government_area": "Eti-Osa",
            "description": "A secure planned community.",
        }
        payload.update(overrides)
        return payload

    def master_layout_file(self, plot_number="M-10"):
        payload = {
            "type": "FeatureCollection",
            "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
            "features": [{
                "type": "Feature",
                "properties": {"plot_number": plot_number, "block": "A"},
                "geometry": {"type": "Polygon", "coordinates": [[[3.4, 6.4], [3.5, 6.4], [3.5, 6.5], [3.4, 6.4]]]},
            }],
        }
        return SimpleUploadedFile("meridian.geojson", json.dumps(payload).encode(), content_type="application/geo+json")

    def dxf_layout_file(self):
        pairs = [
            ("0", "SECTION"), ("2", "ENTITIES"),
            ("0", "LWPOLYLINE"), ("8", "Block A"), ("70", "1"),
            ("10", "0"), ("20", "0"), ("10", "10"), ("20", "0"),
            ("10", "10"), ("20", "10"), ("10", "0"), ("20", "10"),
            ("0", "ENDSEC"), ("0", "EOF"),
        ]
        content = "\n".join(value for pair in pairs for value in pair).encode("ascii")
        return SimpleUploadedFile("estate-boundaries.dxf", content, content_type="application/dxf")

    def test_platform_admin_can_register_company_but_company_admin_cannot(self):
        client = Client()
        client.force_login(self.platform_user)
        response = self.post(client, "/api/records/platform/companies/register/", {
            "name": "Third Land Ltd", "email": "info@thirdland.example",
            "contact_person": "Terry Land", "phone": "+2348012345678",
        })
        self.assertEqual(response.status_code, 201)
        company = Company.objects.get(name="Third Land Ltd")
        self.assertEqual(company.setup_status, Company.SetupStatus.PENDING)
        self.assertEqual(company.code, "third-land-ltd")

        client.force_login(self.admin_one)
        denied = self.post(client, "/api/records/platform/companies/register/", {
            "name": "Blocked Ltd", "code": "blocked",
        })
        self.assertEqual(denied.status_code, 403)

    def test_company_admin_queries_are_isolated_to_their_company(self):
        client = Client()
        client.force_login(self.admin_one)
        response = client.get("/api/records/companies/%s/parcels/" % self.company_one.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()["parcels"]], [self.parcel_one.pk])

        denied = client.get("/api/records/companies/%s/parcels/" % self.company_two.pk)
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(client.get("/api/records/platform/dashboard/").status_code, 403)

    def test_first_admin_invitation_reuses_existing_account(self):
        invited_user = User.objects.create_user(
            username="invitee@example.com", email="invitee@example.com", password="Strong-pass-42!"
        )
        client = Client()
        client.force_login(self.platform_user)
        response = self.post(
            client,
            "/api/records/platform/companies/%s/invite-first-admin/" % self.company_two.pk,
            {"email": invited_user.email},
        )
        self.assertEqual(response.status_code, 201)
        token = parse_qs(urlparse(mail.outbox[-1].body.splitlines()[-1]).query)["company_admin_invitation"][0]
        self.assertIn("/property/?company_admin_invitation=", mail.outbox[-1].body)

        client.logout()
        requires_account = self.post(client, "/api/records/company-admin-invitations/accept/", {"token": token})
        self.assertEqual(requires_account.status_code, 409)

        other_user = User.objects.create_user(
            username="other@example.com", email="other@example.com", password="Strong-pass-42!"
        )
        client.force_login(other_user)
        wrong_account = self.post(client, "/api/records/company-admin-invitations/accept/", {"token": token})
        self.assertEqual(wrong_account.status_code, 409)

        client.force_login(invited_user)
        accepted = self.post(client, "/api/records/company-admin-invitations/accept/", {"token": token})
        self.assertEqual(accepted.status_code, 200)
        self.assertTrue(CompanyMembership.objects.filter(company=self.company_two, user=invited_user).exists())
        self.assertFalse(PlatformAdministrator.objects.filter(user=invited_user).exists())
        self.company_two.refresh_from_db()
        self.assertEqual(self.company_two.setup_status, Company.SetupStatus.COMPLETE)

    def test_invitation_validation_prevents_orphaned_account_creation(self):
        client = Client()
        invalid = self.post(client, "/api/records/company-admin-invitations/accept/", {
            "token": "not-a-valid-token", "full_name": "No Account", "password": "Strong-pass-42!",
        })
        self.assertEqual(invalid.status_code, 400)
        self.assertFalse(User.objects.filter(email="invitee@example.com").exists())

    @override_settings(DEBUG=True)
    def test_new_invited_user_is_created_only_by_invitation_acceptance(self):
        client = Client()
        client.force_login(self.platform_user)
        response = self.post(
            client,
            "/api/records/platform/companies/%s/invite-first-admin/" % self.company_two.pk,
            {"email": "new-admin@example.com"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("invitation_url", response.json())
        self.assertIn("/property/?company_admin_invitation=", response.json()["invitation_url"])
        token = parse_qs(urlparse(mail.outbox[-1].body.splitlines()[-1]).query)["company_admin_invitation"][0]

        client.logout()
        invitation = client.get("/api/records/company-admin-invitations/status/", {"token": token})
        self.assertEqual(invitation.status_code, 200)
        self.assertEqual(invitation.json()["email"], "new-admin@example.com")

        # Cached versions of the frontend used to append a slash to this
        # query-value. A fresh invitation must still be recognised.
        legacy_invitation = client.get("/api/records/company-admin-invitations/status/", {"token": f"{token}/"})
        self.assertEqual(legacy_invitation.status_code, 200)

        accepted = self.post(client, "/api/records/company-admin-invitations/accept/", {
            "token": token, "full_name": "New Company Admin", "password": "Strong-pass-42!",
        })
        self.assertEqual(accepted.status_code, 200)
        user = User.objects.get(email="new-admin@example.com")
        self.assertTrue(CompanyMembership.objects.filter(company=self.company_two, user=user).exists())

    def test_property_allocation_cannot_create_company_admin_membership(self):
        property_user = User.objects.create_user(
            username="holder@example.com", email="holder@example.com", password="Strong-pass-42!"
        )
        client = Client()
        client.force_login(self.admin_one)
        response = self.post(client, "/api/records/companies/%s/allocations/" % self.company_one.pk, {
            "parcel_id": self.parcel_one.pk,
            "email": property_user.email,
            "reference": "ALLOC-001",
        })
        self.assertEqual(response.status_code, 201)
        self.assertFalse(CompanyMembership.objects.filter(user=property_user).exists())

    def test_public_registration_does_not_accept_role_fields(self):
        client = Client()
        response = self.post(client, "/api/accounts/register/", {
            "full_name": "Public Person", "email": "public@example.com", "password": "Strong-pass-42!",
            "is_platform_admin": True, "company_id": self.company_one.pk,
        })
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email="public@example.com")
        self.assertFalse(PlatformAdministrator.objects.filter(user=user).exists())
        self.assertFalse(CompanyMembership.objects.filter(user=user).exists())

    def test_company_admin_can_create_and_list_only_own_estates(self):
        client = Client()
        client.force_login(self.admin_one)
        created = self.post(
            client,
            f"/api/records/companies/{self.company_one.pk}/estates/",
            self.estate_payload(company_id=self.company_two.pk, code="attempted-transfer"),
        )
        self.assertEqual(created.status_code, 201)
        estate = Estate.objects.get(pk=created.json()["estate"]["id"])
        self.assertEqual(estate.company, self.company_one)
        self.assertEqual(estate.created_by, self.admin_one)
        self.assertTrue(created.json()["estate"]["public_id"])

        listed = client.get(f"/api/records/companies/{self.company_one.pk}/estates/")
        self.assertEqual(listed.status_code, 200)
        listed_ids = [item["id"] for item in listed.json()["estates"]]
        self.assertIn(estate.pk, listed_ids)
        self.assertNotIn(self.estate_two.pk, listed_ids)
        self.assertEqual(client.get(f"/api/records/companies/{self.company_two.pk}/estates/").status_code, 403)

    def test_company_admin_can_view_update_and_archive_own_estate(self):
        estate = Estate.objects.create(
            company=self.company_one, name="Meridian Gardens", code="first-meridian", state="Lagos",
            address="Old address", local_government_area="Eti-Osa", created_by=self.admin_one,
        )
        client = Client()
        client.force_login(self.admin_one)
        detail_url = f"/api/records/companies/{self.company_one.pk}/estates/{estate.pk}/"
        self.assertEqual(client.get(detail_url).status_code, 200)
        updated = self.patch(client, detail_url, self.estate_payload("Meridian Gardens", address="New address"))
        self.assertEqual(updated.status_code, 200)
        estate.refresh_from_db()
        self.assertEqual(estate.address, "New address")
        archived = self.post(client, f"/api/records/companies/{self.company_one.pk}/estates/{estate.pk}/archived/", {})
        self.assertEqual(archived.status_code, 200)
        estate.refresh_from_db()
        self.assertEqual(estate.status, Estate.Status.ARCHIVED)
        self.assertFalse(estate.is_active)

    def test_company_admin_cannot_access_update_or_archive_another_company_estate(self):
        other_estate = Estate.objects.create(
            company=self.company_two, name="Private Estate", code="second-private", state="Oyo",
            address="Restricted Road", local_government_area="Ibadan North",
        )
        client = Client()
        client.force_login(self.admin_one)
        url = f"/api/records/companies/{self.company_one.pk}/estates/{other_estate.pk}/"
        self.assertEqual(client.get(url).status_code, 404)
        self.assertEqual(self.patch(client, url, self.estate_payload("Hijacked Estate")).status_code, 404)
        archive = self.post(client, f"/api/records/companies/{self.company_one.pk}/estates/{other_estate.pk}/archived/", {})
        self.assertEqual(archive.status_code, 404)
        other_estate.refresh_from_db()
        self.assertEqual(other_estate.status, Estate.Status.ACTIVE)

    def test_duplicate_names_are_rejected_per_company_but_allowed_across_companies(self):
        client = Client()
        client.force_login(self.admin_one)
        endpoint = f"/api/records/companies/{self.company_one.pk}/estates/"
        self.assertEqual(self.post(client, endpoint, self.estate_payload()).status_code, 201)
        self.assertEqual(self.post(client, endpoint, self.estate_payload()).status_code, 409)
        Estate.objects.create(
            company=self.company_two, name="Meridian Gardens", code="second-meridian", state="Oyo",
            address="New Road", local_government_area="Ibadan North",
        )
        self.assertEqual(Estate.objects.filter(name="Meridian Gardens").count(), 2)

    def test_suspended_company_and_anonymous_users_cannot_manage_estates(self):
        client = Client()
        self.assertEqual(client.get(f"/api/records/companies/{self.company_one.pk}/estates/").status_code, 302)
        self.company_one.status = Company.Status.SUSPENDED
        self.company_one.save(update_fields=("status", "updated_at"))
        client.force_login(self.admin_one)
        denied = self.post(client, f"/api/records/companies/{self.company_one.pk}/estates/", self.estate_payload())
        self.assertEqual(denied.status_code, 403)

    def test_company_admin_can_upload_version_and_process_geojson_layout(self):
        client = Client()
        client.force_login(self.admin_one)
        url = f"/api/records/companies/{self.company_one.pk}/estates/{self.estate_one.pk}/master-layouts/"
        uploaded = client.post(url, {"document": self.master_layout_file()})
        self.assertEqual(uploaded.status_code, 201)
        layout_id = uploaded.json()["master_layout"]["id"]
        plan = EstateMasterPlan.objects.get(pk=layout_id)
        self.assertEqual(plan.company, self.company_one)
        self.assertEqual(plan.estate, self.estate_one)
        self.assertEqual(plan.version, 1)

        processed = self.post(client, f"/api/records/companies/{self.company_one.pk}/master-layouts/{layout_id}/process/", {})
        self.assertEqual(processed.status_code, 200)
        self.assertEqual(processed.json()["master_layout"]["processing_status"], EstateMasterPlan.Status.READY_FOR_APPROVAL)
        candidate = ExtractedParcelCandidate.objects.get(master_plan=plan)
        self.assertEqual(candidate.status, ExtractedParcelCandidate.Status.VALIDATED)
        self.assertEqual(candidate.plot_number, "M-10")
        self.assertFalse(Parcel.objects.filter(estate=self.estate_one, plot_number="M-10").exists())

        approved = self.post(client, f"/api/records/companies/{self.company_one.pk}/master-layouts/{layout_id}/approve-candidates/", {})
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.json()["published_count"], 1)
        self.assertTrue(Parcel.objects.filter(estate=self.estate_one, plot_number="M-10").exists())
        plan.refresh_from_db()
        self.assertTrue(plan.is_current)
        self.assertEqual(plan.processing_status, EstateMasterPlan.Status.APPROVED)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    FRONTEND_URL="https://terraledger.example",
    ALLOCATION_INVITATION_EXPIRY_DAYS=7,
)
class AllocationInvitationWorkflowTests(TestCase):
    def setUp(self):
        mail.outbox = []
        self.admin = User.objects.create_user(
            username="company-admin@example.com",
            email="company-admin@example.com",
            password="Admin-password-42!",
        )
        self.company = Company.objects.create(name="Terra Estates", code="terra-estates")
        CompanyMembership.objects.create(company=self.company, user=self.admin)
        self.estate = Estate.objects.create(
            company=self.company, name="Green Valley", code="green-valley", state="Lagos"
        )
        self.parcel = Parcel.objects.create(
            estate=self.estate,
            plot_number="P-101",
            block="B",
            area_sqm="450.00",
            property_type="Residential",
            features=["Corner lot", "Road access"],
        )
        self.admin_client = Client()
        self.admin_client.force_login(self.admin)
        self.allocation_url = f"/api/records/companies/{self.company.pk}/allocations/"

    def post_json(self, client, url, payload):
        return client.post(url, data=json.dumps(payload), content_type="application/json")

    def issue_allocation(self, email="recipient@example.com", parcel=None, name="Ada Recipient", reference=""):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.post_json(self.admin_client, self.allocation_url, {
                "parcel_id": (parcel or self.parcel).pk,
                "email": email,
                "full_name": name,
                "reference": reference,
            })
        return response

    def invitation_token(self, message=None):
        message = message or mail.outbox[-1]
        match = re.search(r"allocation_invitation=([A-Za-z0-9_-]+)", message.body)
        self.assertIsNotNone(match)
        return match.group(1)

    def accept_with_password(self, client, token, *, full_name="Ada Recipient"):
        return self.post_json(client, "/api/records/allocation-invitations/accept/", {
            "token": token,
            "full_name": full_name,
            "password": "Strong-recipient-password-42!",
        })

    def test_allocation_creates_parcel_update_invitation_and_confirmation_email(self):
        response = self.issue_allocation(reference="ALLOC-GV-101")

        self.assertEqual(response.status_code, 201)
        allocation = Allocation.objects.get()
        invitation = AllocationInvitation.objects.get()
        self.parcel.refresh_from_db()
        self.assertEqual(self.parcel.status, Parcel.Status.ALLOCATED)
        self.assertIsNone(allocation.allottee)
        self.assertEqual(allocation.recipient_email, "recipient@example.com")
        self.assertEqual(invitation.status, AllocationInvitation.Status.SENT)
        self.assertIsNotNone(invitation.sent_at)
        raw_token = self.invitation_token()
        self.assertEqual(
            invitation.token_hash,
            hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
        )
        self.assertNotEqual(raw_token, invitation.token_hash)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.subject, "Your Property Allocation on TerraLedger — Green Valley")
        for detail in ("Ada Recipient", "Terra Estates", "P-101", "Block", "450.00 m²", "Residential", "Corner lot"):
            self.assertIn(detail, message.body)
        self.assertIn("does not independently establish legal title", message.body)
        self.assertTrue(message.alternatives)
        self.assertIn("Create Your TerraLedger Account", message.alternatives[0][0])
        self.assertIn("allocation_invitation=", message.body)

        duplicate = self.issue_allocation(reference="ALLOC-GV-101")
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(Allocation.objects.count(), 1)
        self.assertEqual(AllocationInvitation.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_failed_email_is_recorded_and_resend_rotates_single_use_token(self):
        with patch(
            "apps.allocations.services.secrets.token_urlsafe",
            return_value="old-token",
        ), patch(
            "apps.allocations.services.EmailMultiAlternatives.send",
            side_effect=OSError("SMTP is unavailable"),
        ), self.captureOnCommitCallbacks(execute=True):
            created = self.post_json(self.admin_client, self.allocation_url, {
                "parcel_id": self.parcel.pk,
                "email": "recipient@example.com",
                "full_name": "Ada Recipient",
            })
        self.assertEqual(created.status_code, 201)
        allocation = Allocation.objects.get()
        failed_invitation = allocation.invitations.first()
        self.assertEqual(failed_invitation.status, AllocationInvitation.Status.FAILED)
        self.assertIn("SMTP is unavailable", failed_invitation.failure_reason)
        self.assertEqual(allocation.parcel.status, Parcel.Status.ALLOCATED)

        with patch(
            "apps.allocations.services.secrets.token_urlsafe",
            return_value="new-token",
        ), self.captureOnCommitCallbacks(execute=True):
            resent = self.post_json(
                self.admin_client,
                f"/api/records/companies/{self.company.pk}/allocations/{allocation.pk}/resend-invitation/",
                {},
            )
        self.assertEqual(resent.status_code, 200)
        failed_invitation.refresh_from_db()
        self.assertEqual(failed_invitation.status, AllocationInvitation.Status.REVOKED)
        self.assertTrue(
            AllocationInvitation.objects.filter(
                allocation=allocation,
                status=AllocationInvitation.Status.SENT,
            ).exists()
        )
        self.assertEqual(len(mail.outbox), 1)
        old_status = self.admin_client.get(
            "/api/records/allocation-invitations/status/", {"token": "old-token"}
        )
        new_status = self.admin_client.get(
            "/api/records/allocation-invitations/status/", {"token": "new-token"}
        )
        self.assertEqual(old_status.status_code, 400)
        self.assertEqual(new_status.status_code, 200)

    def test_new_and_existing_recipients_can_claim_but_email_mismatch_cannot(self):
        self.issue_allocation()
        token = self.invitation_token()
        anonymous = Client()
        status_response = anonymous.get(
            "/api/records/allocation-invitations/status/", {"token": token}
        )
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.json(), {
            "email": "recipient@example.com",
            "expires_at": AllocationInvitation.objects.get().expires_at.isoformat(),
        })
        self.assertNotIn("parcel", status_response.json())

        accepted = self.accept_with_password(anonymous, token)
        self.assertEqual(accepted.status_code, 200)
        recipient = User.objects.get(email="recipient@example.com")
        self.assertEqual(accepted.json()["allocation"]["allottee"]["id"], recipient.pk)
        self.assertTrue(VerifiedEmail.objects.filter(user=recipient, email=recipient.email).exists())
        self.assertEqual(Allocation.objects.get().status, Allocation.Status.ACTIVE)
        self.assertEqual(anonymous.get("/api/accounts/me/").status_code, 200)
        self.assertEqual(self.accept_with_password(anonymous, token).status_code, 400)

        second_parcel = Parcel.objects.create(estate=self.estate, plot_number="P-102")
        existing = User.objects.create_user(
            username="existing@example.com", email="existing@example.com", password="Existing-password-42!"
        )
        existing_allocation = self.issue_allocation(
            email=existing.email, parcel=second_parcel, name="Existing Recipient"
        )
        self.assertEqual(existing_allocation.status_code, 201)
        existing_client = Client()
        existing_client.force_login(existing)
        existing_token = self.invitation_token()
        claimed = self.post_json(existing_client, "/api/records/allocation-invitations/accept/", {
            "token": existing_token,
        })
        self.assertEqual(claimed.status_code, 200)
        self.assertEqual(User.objects.filter(email__iexact=existing.email).count(), 1)
        self.assertEqual(Allocation.objects.get(parcel=second_parcel).allottee, existing)

        third_parcel = Parcel.objects.create(estate=self.estate, plot_number="P-103")
        third = self.issue_allocation(
            email="different@example.com", parcel=third_parcel, name="Different Recipient"
        )
        self.assertEqual(third.status_code, 201)
        wrong_client = Client()
        wrong_client.force_login(existing)
        wrong = self.post_json(
            wrong_client,
            "/api/records/allocation-invitations/accept/",
            {"token": self.invitation_token()},
        )
        self.assertEqual(wrong.status_code, 409)
        self.assertIn("Sign in with the email address", wrong.json()["detail"])
        self.assertNotIn("P-103", wrong.content.decode())
        self.assertIsNone(Allocation.objects.get(parcel=third_parcel).allottee)

    def test_expired_and_revoked_invitations_are_rejected(self):
        self.issue_allocation()
        expired_token = self.invitation_token()
        invitation = AllocationInvitation.objects.get()
        invitation.expires_at = timezone.now() - timedelta(days=1)
        invitation.save(update_fields=("expires_at",))
        expired = Client().get(
            "/api/records/allocation-invitations/status/", {"token": expired_token}
        )
        self.assertEqual(expired.status_code, 400)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, AllocationInvitation.Status.EXPIRED)

        second_parcel = Parcel.objects.create(estate=self.estate, plot_number="P-102")
        self.issue_allocation(email="second@example.com", parcel=second_parcel)
        revoked_token = self.invitation_token()
        allocation = Allocation.objects.get(parcel=second_parcel)
        revoked = self.post_json(
            self.admin_client,
            f"/api/records/companies/{self.company.pk}/allocations/{allocation.pk}/revoke/",
            {},
        )
        self.assertEqual(revoked.status_code, 200)
        self.assertTrue(Allocation.objects.filter(pk=allocation.pk).exists())
        self.assertEqual(Allocation.objects.get(pk=allocation.pk).status, Allocation.Status.REVOKED)
        self.assertEqual(Parcel.objects.get(pk=second_parcel.pk).status, Parcel.Status.ALLOCATED)
        rejected = Client().get(
            "/api/records/allocation-invitations/status/", {"token": revoked_token}
        )
        self.assertEqual(rejected.status_code, 400)

    def test_recipient_property_scope_multiple_allocations_and_company_scope(self):
        self.issue_allocation()
        first_token = self.invitation_token()
        second_parcel = Parcel.objects.create(estate=self.estate, plot_number="P-102")
        self.issue_allocation(parcel=second_parcel)
        second_token = self.invitation_token()
        recipient_client = Client()
        self.assertEqual(self.accept_with_password(recipient_client, first_token).status_code, 200)
        self.assertEqual(
            self.post_json(
                recipient_client,
                "/api/records/allocation-invitations/accept/",
                {"token": second_token},
            ).status_code,
            200,
        )
        properties = recipient_client.get("/api/records/my-property/").json()["allocations"]
        self.assertEqual(len(properties), 2)
        revoked = self.post_json(
            self.admin_client,
            f"/api/records/companies/{self.company.pk}/allocations/{properties[0]['id']}/revoke/",
            {},
        )
        self.assertEqual(revoked.status_code, 200)
        retained_properties = recipient_client.get("/api/records/my-property/").json()["allocations"]
        self.assertEqual(len(retained_properties), 2)
        self.assertEqual(
            {item["status"] for item in retained_properties},
            {Allocation.Status.ACTIVE, Allocation.Status.REVOKED},
        )

        other_parcel = Parcel.objects.create(estate=self.estate, plot_number="P-103")
        self.issue_allocation(email="other@example.com", parcel=other_parcel, name="Other Recipient")
        other_token = self.invitation_token()
        other_client = Client()
        self.assertEqual(
            self.accept_with_password(other_client, other_token, full_name="Other Recipient").status_code,
            200,
        )
        self.assertEqual(len(other_client.get("/api/records/my-property/").json()["allocations"]), 1)
        self.assertEqual(
            other_client.get(f"/api/records/my-property/{properties[0]['id']}/").status_code,
            404,
        )

        company_two = Company.objects.create(name="Other Estates", code="other-estates")
        estate_two = Estate.objects.create(
            company=company_two, name="Other Estate", code="other-estate", state="Oyo"
        )
        Parcel.objects.create(estate=estate_two, plot_number="O-1")
        self.assertEqual(
            self.admin_client.get(f"/api/records/companies/{company_two.pk}/allocations/").status_code,
            403,
        )

class AdministrativeHierarchyLayoutRemainderTests(TestCase):
    setUp = AdministrativeHierarchyTests.setUp
    post = AdministrativeHierarchyTests.post
    master_layout_file = AdministrativeHierarchyTests.master_layout_file
    dxf_layout_file = AdministrativeHierarchyTests.dxf_layout_file

    def test_company_admin_can_extract_standard_dxf_boundaries_for_review(self):
        client = Client()
        client.force_login(self.admin_one)
        upload_url = f"/api/records/companies/{self.company_one.pk}/estates/{self.estate_one.pk}/master-layouts/"
        uploaded = client.post(upload_url, {"document": self.dxf_layout_file()})
        self.assertEqual(uploaded.status_code, 201)
        layout_id = uploaded.json()["master_layout"]["id"]

        processed = self.post(client, f"/api/records/companies/{self.company_one.pk}/master-layouts/{layout_id}/process/", {})
        self.assertEqual(processed.status_code, 200)
        self.assertEqual(processed.json()["master_layout"]["processing_status"], EstateMasterPlan.Status.REVIEW_REQUIRED)
        candidate = ExtractedParcelCandidate.objects.get(master_plan_id=layout_id)
        self.assertEqual(candidate.status, ExtractedParcelCandidate.Status.NEEDS_REVIEW)
        self.assertEqual(candidate.block, "Block A")
        self.assertEqual(candidate.boundary_coordinates[0], [0.0, 0.0])
        self.assertFalse(Parcel.objects.filter(estate=self.estate_one, source_master_plan_id=layout_id).exists())

    def test_master_layout_upload_validation_versioning_and_tenant_isolation(self):
        client = Client()
        upload_url = f"/api/records/companies/{self.company_one.pk}/estates/{self.estate_one.pk}/master-layouts/"
        self.assertEqual(client.post(upload_url, {"document": self.master_layout_file()}).status_code, 302)
        client.force_login(self.admin_one)
        unsupported = client.post(upload_url, {"document": SimpleUploadedFile("layout.pdf", b"not a layout")})
        self.assertEqual(unsupported.status_code, 400)
        first = client.post(upload_url, {"document": self.master_layout_file("M-11")})
        self.assertEqual(first.status_code, 201)
        second = client.post(upload_url, {"document": self.master_layout_file("M-12")})
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.json()["master_layout"]["version"], 2)
        self.assertEqual(EstateMasterPlan.objects.filter(estate=self.estate_one).count(), 2)

        admin_two = User.objects.create_user(username="two@example.com", email="two@example.com", password="Strong-pass-42!")
        CompanyMembership.objects.create(company=self.company_two, user=admin_two)
        client_two = Client()
        client_two.force_login(admin_two)
        other_upload = client_two.post(
            f"/api/records/companies/{self.company_two.pk}/estates/{self.estate_two.pk}/master-layouts/",
            {"document": self.master_layout_file("O-1")},
        )
        self.assertEqual(other_upload.status_code, 201)
        other_layout_id = other_upload.json()["master_layout"]["id"]
        denied = client.get(f"/api/records/companies/{self.company_one.pk}/master-layouts/{other_layout_id}/")
        self.assertEqual(denied.status_code, 404)
        self.assertEqual(client.post(
            f"/api/records/companies/{self.company_one.pk}/master-layouts/{other_layout_id}/process/", {}
        ).status_code, 404)

    def test_unknown_crs_and_invalid_geometry_require_review_and_never_publish(self):
        layout = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {"plot_number": "M-13"},
                "geometry": {"type": "Polygon", "coordinates": [[[3.4, 6.4], [3.5, 6.4], [3.5, 6.5]]]},
            }],
        }
        client = Client()
        client.force_login(self.admin_one)
        uploaded = client.post(
            f"/api/records/companies/{self.company_one.pk}/estates/{self.estate_one.pk}/master-layouts/",
            {"document": SimpleUploadedFile("unknown-crs.geojson", json.dumps(layout).encode(), content_type="application/geo+json")},
        )
        layout_id = uploaded.json()["master_layout"]["id"]
        processed = self.post(client, f"/api/records/companies/{self.company_one.pk}/master-layouts/{layout_id}/process/", {})
        self.assertEqual(processed.json()["master_layout"]["processing_status"], EstateMasterPlan.Status.REVIEW_REQUIRED)
        candidate = ExtractedParcelCandidate.objects.get(master_plan_id=layout_id)
        self.assertEqual(candidate.status, ExtractedParcelCandidate.Status.NEEDS_REVIEW)
        self.assertTrue(any("CRS" in warning for warning in candidate.validation_warnings))
        approved = self.post(client, f"/api/records/companies/{self.company_one.pk}/master-layouts/{layout_id}/approve-candidates/", {})
        self.assertEqual(approved.json()["published_count"], 0)
        self.assertFalse(Parcel.objects.filter(estate=self.estate_one, plot_number="M-13").exists())

    def test_rejecting_review_candidate_allows_completed_version_to_become_current(self):
        layout = {
            "type": "FeatureCollection",
            "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
            "features": [
                {
                    "type": "Feature", "properties": {"plot_number": "M-14"},
                    "geometry": {"type": "Polygon", "coordinates": [[[3.4, 6.4], [3.5, 6.4], [3.5, 6.5], [3.4, 6.4]]]},
                },
                {
                    "type": "Feature", "properties": {"plot_number": "M-15"},
                    "geometry": {"type": "Polygon", "coordinates": [[[3.6, 6.4], [3.7, 6.4], [3.7, 6.5]]]},
                },
            ],
        }
        client = Client()
        client.force_login(self.admin_one)
        uploaded = client.post(
            f"/api/records/companies/{self.company_one.pk}/estates/{self.estate_one.pk}/master-layouts/",
            {"document": SimpleUploadedFile("mixed.geojson", json.dumps(layout).encode(), content_type="application/geo+json")},
        )
        layout_id = uploaded.json()["master_layout"]["id"]
        self.post(client, f"/api/records/companies/{self.company_one.pk}/master-layouts/{layout_id}/process/", {})
        valid = ExtractedParcelCandidate.objects.get(master_plan_id=layout_id, plot_number="M-14")
        invalid = ExtractedParcelCandidate.objects.get(master_plan_id=layout_id, plot_number="M-15")
        self.assertEqual(self.post(
            client, f"/api/records/companies/{self.company_one.pk}/master-layouts/{layout_id}/approve-candidates/", {"candidate_ids": [str(valid.pk)]}
        ).json()["published_count"], 1)
        plan = EstateMasterPlan.objects.get(pk=layout_id)
        self.assertFalse(plan.is_current)
        self.assertEqual(self.post(
            client, f"/api/records/companies/{self.company_one.pk}/master-layouts/{layout_id}/reject-candidates/", {"candidate_ids": [str(invalid.pk)]}
        ).json()["rejected_count"], 1)
        plan.refresh_from_db()
        self.assertTrue(plan.is_current)
        self.assertEqual(plan.processing_status, EstateMasterPlan.Status.APPROVED)
