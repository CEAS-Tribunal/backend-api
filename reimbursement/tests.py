from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from dashboard.models import ExecMember, ExecRole

from reimbursement.models import ReimbursementRequest, UserProfile

User = get_user_model()


@override_settings(
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class ReimbursementRequestCreateAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="execuser",
            email="exec@mail.uc.edu",
            password="oldpass123",
        )
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        UserProfile.objects.create(user=self.user, vendor_id="VENDOR-TEST-001")

        # Treasurer recipient (via ExecRole) for notification testing.
        self.treasurer_user = User.objects.create_user(
            username="treasurer1",
            email="treasurer@test.edu",
            password="pass12345",
            first_name="Terry",
            last_name="Treasurer",
        )
        self.treasurer_user.is_staff = True
        self.treasurer_user.save(update_fields=["is_staff"])
        em = ExecMember.objects.create(user=self.treasurer_user, must_change_password=False)
        role = ExecRole.objects.create(
            role="Treasurer",
            description="Finance",
            committee="pres",
        )
        role.ExecMember.add(em)

        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    def _receipt_file(self):
        return SimpleUploadedFile(
            "receipt.pdf",
            b"%PDF-1.4 test receipt bytes",
            content_type="application/pdf",
        )

    def test_create_reimbursement_multipart_201(self):
        payload = {
            "date": "2026-04-06",
            "m_number": "M12345678",
            "vendor_name": "Test Vendor",
            "amount": "12.34",
            "description": "Team supplies",
            "budgeted": "true",
            "reimbursement_type": "Food",
            "itemized_receipt": self._receipt_file(),
        }
        r = self.client.post("/api/reimbursement/", payload, format="multipart")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertIn("id", r.data)
        req = ReimbursementRequest.objects.get(pk=r.data["id"])
        self.assertEqual(req.vendor_id, "VENDOR-TEST-001")
        self.assertEqual(req.m_number, "M12345678")
        self.assertEqual(req.amount, Decimal("12.34"))
        self.assertTrue(req.itemized_receipt.name)

        # Treasurer notification sent and does not include empty optional fields.
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertIn("treasurer@test.edu", msg.to)
        html = msg.alternatives[0][0] if msg.alternatives else msg.body
        self.assertIn("Hello", html)
        self.assertIn("Terry Treasurer", html)
        self.assertIn("M12345678", html)
        self.assertIn("Test Vendor", html)
        self.assertIn("Team supplies", html)
        self.assertNotIn("Mailing address line 2", html)
        self.assertNotIn("IC participant", html)
        self.assertEqual(len(msg.attachments), 2)
        attachment_names = {a[0] for a in msg.attachments}
        self.assertTrue(any(name.startswith("receipt") and name.endswith(".pdf") for name in attachment_names))
        self.assertIn(f"reimbursement_request_{req.id}.pdf", attachment_names)

    def test_create_with_supporting_document_optional(self):
        support = SimpleUploadedFile("extra.png", b"\x89PNG\r\n", content_type="image/png")
        payload = {
            "date": "2026-04-06",
            "m_number": "M87654321",
            "vendor_name": "Other",
            "amount": "5.00",
            "description": "Misc",
            "budgeted": "false",
            "non_budgeted_officer_name": "Officer Name",
            "non_budgeted_officer_position": "Officer Position",
            "reimbursement_type": "Travel",
            "itemized_receipt": self._receipt_file(),
            "supporting_document": support,
        }
        r = self.client.post("/api/reimbursement/", payload, format="multipart")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        req = ReimbursementRequest.objects.get(pk=r.data["id"])
        self.assertTrue(req.supporting_document.name)

        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        attachment_names = {a[0] for a in msg.attachments}
        self.assertTrue(any(name.startswith("receipt") and name.endswith(".pdf") for name in attachment_names))
        self.assertTrue(any(name.startswith("extra") and name.endswith(".png") for name in attachment_names))
        self.assertIn(f"reimbursement_request_{req.id}.pdf", attachment_names)

    def test_no_profile_returns_400(self):
        lone = User.objects.create_user(
            username="noprofile",
            email="n@mail.uc.edu",
            password="x",
        )
        lone.is_staff = True
        lone.save(update_fields=["is_staff"])
        refresh = RefreshToken.for_user(lone)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        payload = {
            "date": "2026-04-06",
            "m_number": "M1",
            "vendor_name": "V",
            "amount": "1.00",
            "description": "d",
            "budgeted": "true",
            "reimbursement_type": "Other",
            "itemized_receipt": self._receipt_file(),
        }
        r = self.client.post("/api/reimbursement/", payload, format="multipart")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", r.data)

    def test_non_staff_forbidden(self):
        self.user.is_staff = False
        self.user.save(update_fields=["is_staff"])
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        payload = {
            "date": "2026-04-06",
            "m_number": "M1",
            "vendor_name": "V",
            "amount": "1.00",
            "description": "d",
            "budgeted": "true",
            "reimbursement_type": "Other",
            "itemized_receipt": self._receipt_file(),
        }
        r = self.client.post("/api/reimbursement/", payload, format="multipart")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class ReimbursementRequestListAndFiledAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user(
            username="staffer",
            email="staff@test.edu",
            password="pass12345",
        )
        self.staff.is_staff = True
        self.staff.save(update_fields=["is_staff"])
        UserProfile.objects.create(user=self.staff, vendor_id="V-STAFF")

        self.treasurer_user = User.objects.create_user(
            username="treasurer1",
            email="t@test.edu",
            password="pass12345",
        )
        self.treasurer_user.is_staff = True
        self.treasurer_user.save(update_fields=["is_staff"])
        em = ExecMember.objects.create(user=self.treasurer_user, must_change_password=False)
        role = ExecRole.objects.create(
            role="Treasurer",
            description="Finance",
            committee="pres",
        )
        role.ExecMember.add(em)

        refresh = RefreshToken.for_user(self.staff)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        self.req = ReimbursementRequest.objects.create(
            name="Pat",
            position="VP",
            email="pat@test.edu",
            m_number="M111",
            vendor_id="V-1",
            date="2026-04-01",
            vendor_name="Store",
            amount=Decimal("10.00"),
            description="Snacks",
            budgeted=True,
            reimbursement_type="Food",
            filed=False,
        )

    def test_list_staff_ok(self):
        r = self.client.get("/api/reimbursement/requests/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data), 1)
        self.assertEqual(r.data[0]["id"], self.req.id)
        self.assertFalse(r.data[0]["filed"])

    def test_list_filter_filed(self):
        self.req.filed = True
        self.req.save(update_fields=["filed"])
        r = self.client.get("/api/reimbursement/requests/?filed=true")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data), 1)
        r2 = self.client.get("/api/reimbursement/requests/?filed=false")
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r2.data), 0)

    def test_patch_filed_treasurer_ok(self):
        refresh = RefreshToken.for_user(self.treasurer_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        r = self.client.patch(
            f"/api/reimbursement/requests/{self.req.id}/filed/",
            {"filed": True},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        self.assertTrue(r.data["filed"])
        self.req.refresh_from_db()
        self.assertTrue(self.req.filed)

    def test_patch_filed_non_treasurer_forbidden(self):
        r = self.client.patch(
            f"/api/reimbursement/requests/{self.req.id}/filed/",
            {"filed": True},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_filed_superuser_ok(self):
        su = User.objects.create_user(
            username="adminx",
            email="a@test.edu",
            password="pass12345",
        )
        su.is_staff = True
        su.is_superuser = True
        su.save(update_fields=["is_staff", "is_superuser"])
        refresh = RefreshToken.for_user(su)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        r = self.client.patch(
            f"/api/reimbursement/requests/{self.req.id}/filed/",
            {"filed": True},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)


class ReimbursementPdfTests(TestCase):
    def test_filled_pdf_flattens_field_values_for_viewers(self):
        from pypdf import PdfReader

        from reimbursement.pdf import build_filled_reimbursement_pdf

        req = ReimbursementRequest.objects.create(
            name="Jane Doe",
            position="President",
            email="jane@test.edu",
            m_number="M87654321",
            vendor_id="VENDOR-TEST-001",
            date="2026-04-06",
            vendor_name="Staples",
            amount=Decimal("99.99"),
            description="Office paper",
            budgeted=False,
            reimbursement_type="check",
            reimbursement_address_line1="123 Main St",
            reimbursement_address_city="Cincinnati",
            reimbursement_address_state="OH",
            reimbursement_address_zip="45221",
            non_budgeted_officer_name="Officer Bob",
            non_budgeted_officer_position="VP Finance",
        )

        filled = build_filled_reimbursement_pdf(req)
        self.assertIsNotNone(filled)
        assert filled is not None

        reader = PdfReader(BytesIO(filled.content))
        page = reader.pages[0]
        self.assertFalse(page.get("/Annots"))

        resources = page["/Resources"].get_object()
        xobjects = resources.get("/XObject")
        self.assertIsNotNone(xobjects)
        xobjects = xobjects.get_object()

        flattened_streams = [
            obj.get_data()
            for key, ref in xobjects.items()
            if str(key).startswith("/Fm_")
            for obj in [ref.get_object()]
        ]
        combined = b"".join(flattened_streams)
        self.assertIn(b"Jane Doe", combined)
        self.assertIn(b"Staples", combined)
        self.assertIn(b"Officer Bob", combined)
