from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from .models import Representative


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class RepresentativeAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="exec1", password="pass12345")
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])

    def test_post_creates_representative_without_auth(self):
        payload = {
            "name": "Jane Doe",
            "company": "Acme Corp",
            "title": "Recruiter",
            "email": "jane@acme.test",
            "booth_location": "A15",
            "building_location": "rec-center",
        }
        r = self.client.post("/api/career-fair/representatives/", payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Representative.objects.count(), 1)
        self.assertEqual(r.data["company"], "Acme Corp")
        self.assertIn("id", r.data)
        self.assertIn("signed_in_at", r.data)

    def test_get_requires_authentication(self):
        Representative.objects.create(
            name="X",
            company="Y",
            title="T",
            email="x@y.test",
            booth_location="B1",
            building_location="tuc-great-hall",
        )
        r = self.client.get("/api/career-fair/representatives/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_list_with_auth_and_search(self):
        Representative.objects.create(
            name="Alice",
            company="Beta LLC",
            title="HR",
            email="a@b.test",
            booth_location="B1",
            building_location="rec-center",
        )
        Representative.objects.create(
            name="Bob",
            company="Gamma Inc",
            title="Lead",
            email="b@g.test",
            booth_location="B2",
            building_location="rec-center",
        )
        self.client.force_authenticate(user=self.user)
        r = self.client.get("/api/career-fair/representatives/", {"search": "Gamma"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        results = r.data["results"] if isinstance(r.data, dict) else r.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["company"], "Gamma Inc")

    def test_get_list_non_staff_forbidden(self):
        Representative.objects.create(
            name="X",
            company="Y",
            title="T",
            email="x@y.test",
            booth_location="B1",
            building_location="tuc-great-hall",
        )
        outsider = User.objects.create_user(username="nostaff", password="pass12345")
        self.client.force_authenticate(user=outsider)
        r = self.client.get("/api/career-fair/representatives/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
