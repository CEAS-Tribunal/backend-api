from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from dashboard.models import ExecMember, ExecRole

from .models import JudgeModel


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class JudgeCheckInAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="expochair", email="expo@test.edu", password="ceastribunal", is_staff=True
        )
        self.exec_member = ExecMember.objects.create(user=self.user)
        self.judge = JudgeModel.objects.create(
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            phone_number="555-0100",
            employer_name="Analytical Engines",
            judging_category=["1", "7"],
            judging_timeslot=["2"],
            number_of_projects=3,
            is_attending_lunch=True,
            lunch_preference="4",
        )

    def _auth(self, user=None):
        refresh = RefreshToken.for_user(user or self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    def _grant_role(self, role_name):
        role = ExecRole.objects.create(role=role_name, description="", committee="pres")
        role.ExecMember.add(self.exec_member)

    def test_list_requires_expo_role(self):
        self._auth()
        r = self.client.get("/api/expo/judges/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_returns_judges_with_display_labels(self):
        self._grant_role("EXPO Chair")
        self._auth()
        r = self.client.get("/api/expo/judges/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data), 1)
        judge = r.data[0]
        self.assertEqual(
            judge["judging_category_display"],
            ["Human-Centered Research and Design", "Technical Excellence"],
        )
        self.assertEqual(judge["judging_timeslot_display"], ["09:50 AM - 10:05 AM"])
        self.assertEqual(judge["lunch_preference_display"], "Vegetarian")
        self.assertFalse(judge["has_checked_in"])

    def test_check_in_toggles_status(self):
        self._grant_role("EXPO Chair")
        self._auth()
        url = f"/api/expo/judges/{self.judge.id}/check-in/"

        r = self.client.patch(url, {"has_checked_in": True}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.data["has_checked_in"])
        self.judge.refresh_from_db()
        self.assertTrue(self.judge.has_checked_in)

        r = self.client.patch(url, {"has_checked_in": False}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.judge.refresh_from_db()
        self.assertFalse(self.judge.has_checked_in)

    def test_check_in_requires_value(self):
        self._grant_role("EXPO Chair")
        self._auth()
        r = self.client.patch(f"/api/expo/judges/{self.judge.id}/check-in/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_check_in_denied_without_expo_role(self):
        self._auth()
        r = self.client.patch(
            f"/api/expo/judges/{self.judge.id}/check-in/", {"has_checked_in": True}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
