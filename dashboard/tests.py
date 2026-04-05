import os
from unittest import mock

from django.contrib.auth.models import User
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import ExecMember


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class DashboardAuthAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="vishesh6p2",
            email="v@test.edu",
            password="ceastribunal",
        )
        self.exec_member = ExecMember.objects.create(
            user=self.user,
            must_change_password=True,
        )
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])

    def _auth_headers(self, user=None):
        user = user or self.user
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    def test_me_returns_must_change_password_for_exec(self):
        self._auth_headers()
        r = self.client.get("/dashboard/auth/me/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["username"], "vishesh6p2")
        self.assertTrue(r.data["must_change_password"])
        self.assertTrue(r.data["is_staff"])
        self.assertFalse(r.data["is_superuser"])
        self.assertTrue(r.data["is_exec"])

    def test_me_without_exec_member(self):
        lone = User.objects.create_user(username="norole", password="pass12345")
        lone.is_staff = True
        lone.save(update_fields=["is_staff"])
        self._auth_headers(lone)
        r = self.client.get("/dashboard/auth/me/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertFalse(r.data["must_change_password"])
        self.assertTrue(r.data["is_staff"])
        self.assertFalse(r.data["is_exec"])

    def test_post_token_non_staff_forbidden(self):
        outsider = User.objects.create_user(username="outsider", password="pass12345")
        outsider.is_staff = False
        outsider.save(update_fields=["is_staff"])
        r = self.client.post(
            "/api/token/",
            {"username": "outsider", "password": "pass12345"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_token_staff_ok(self):
        r = self.client.post(
            "/api/token/",
            {"username": "vishesh6p2", "password": "ceastribunal"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("access", r.data)
        self.assertIn("refresh", r.data)

    def test_refresh_token_non_staff_forbidden(self):
        outsider = User.objects.create_user(username="outsider2", password="pass12345")
        refresh = str(RefreshToken.for_user(outsider))
        r = self.client.post("/api/token/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_change_password_wrong_old(self):
        self._auth_headers()
        r = self.client.post(
            "/dashboard/auth/change-password/",
            {
                "old_password": "wrong",
                "new_password": "Newpass1",
                "new_password_confirm": "Newpass1",
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("old_password", r.data)

    def test_change_password_non_exec_forbidden(self):
        lone = User.objects.create_user(username="norole2", password="pass12345")
        lone.is_staff = True
        lone.save(update_fields=["is_staff"])
        self._auth_headers(lone)
        r = self.client.post(
            "/dashboard/auth/change-password/",
            {
                "old_password": "pass12345",
                "new_password": "Newpass1",
                "new_password_confirm": "Newpass1",
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_change_password_mismatch_confirm(self):
        self._auth_headers()
        r = self.client.post(
            "/dashboard/auth/change-password/",
            {
                "old_password": "ceastribunal",
                "new_password": "Newpass1",
                "new_password_confirm": "Newpass2",
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_same_as_username_rejected(self):
        self._auth_headers()
        r = self.client.post(
            "/dashboard/auth/change-password/",
            {
                "old_password": "ceastribunal",
                "new_password": "vishesh6p2",
                "new_password_confirm": "vishesh6p2",
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password", r.data)

    def test_change_password_success_clears_flag(self):
        self._auth_headers()
        r = self.client.post(
            "/dashboard/auth/change-password/",
            {
                "old_password": "ceastribunal",
                "new_password": "Tribunal99",
                "new_password_confirm": "Tribunal99",
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.exec_member.refresh_from_db()
        self.assertFalse(self.exec_member.must_change_password)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Tribunal99"))

        r2 = self.client.get("/dashboard/auth/me/")
        self.assertFalse(r2.data["must_change_password"])


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class CreateExecUserCommandTests(TestCase):
    def test_creates_staff_exec_member_with_superuser(self):
        with mock.patch.dict(os.environ, {"TRIBUNAL_INITIAL_PASSWORD": "bootstrap123"}):
            call_command(
                "create_exec_user",
                "abc12345",
                "--email",
                "a@uc.edu",
                "--superuser",
                stdout=StringIO(),
                stderr=StringIO(),
            )
        u = User.objects.get(username="abc12345")
        self.assertTrue(u.is_staff)
        self.assertTrue(u.is_superuser)
        self.assertTrue(u.check_password("bootstrap123"))
        em = ExecMember.objects.get(user=u)
        self.assertTrue(em.must_change_password)

    def test_requires_env_password(self):
        with mock.patch.dict(os.environ, {"TRIBUNAL_INITIAL_PASSWORD": ""}):
            with self.assertRaises(CommandError):
                call_command("create_exec_user", "unique99901", verbosity=0)
