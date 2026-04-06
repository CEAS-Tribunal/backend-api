from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from reimbursement.models import ReimbursementRequest, UserProfile

User = get_user_model()


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
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

    def test_create_with_supporting_document_optional(self):
        support = SimpleUploadedFile("extra.png", b"\x89PNG\r\n", content_type="image/png")
        payload = {
            "date": "2026-04-06",
            "m_number": "M87654321",
            "vendor_name": "Other",
            "amount": "5.00",
            "description": "Misc",
            "budgeted": "false",
            "reimbursement_type": "Travel",
            "itemized_receipt": self._receipt_file(),
            "supporting_document": support,
        }
        r = self.client.post("/api/reimbursement/", payload, format="multipart")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        req = ReimbursementRequest.objects.get(pk=r.data["id"])
        self.assertTrue(req.supporting_document.name)

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
