from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from dashboard.models import ExecMember, ExecRole

from .assignment import DEFAULT_MIN_JUDGES, SLOT_KEYS, generate_assignments
from .models import JudgeAssignmentModel, JudgeModel, StudentModel


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


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class JudgeRegistrationAPITests(TestCase):
    url = "/api/expo/judges/register/"

    def setUp(self):
        self.client = APIClient()
        self.payload = {
            "first_name": "Grace",
            "last_name": "Hopper",
            "email": "Grace@Example.com",
            "phone_number": "555-0101",
            "employer_name": "Navy",
            "judging_category": ["7", "2", "1"],
            "judging_timeslot": ["3", "1"],
            "number_of_projects": 4,
            "is_backup_judge": False,
            "is_attending_lunch": True,
            "lunch_preference": "2",
            "dietary_restrictions": "",
        }

    def test_public_registration_creates_judge_without_exposing_pin(self):
        r = self.client.post(self.url, self.payload, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("judge_pin", r.data)
        judge = JudgeModel.objects.get()
        self.assertEqual(judge.email, "grace@example.com")
        # Rank order must be preserved (not sorted by category id).
        self.assertEqual(list(judge.judging_category), ["7", "2", "1"])
        self.assertEqual(list(judge.judging_timeslot), ["1", "3"])
        self.assertEqual(len(judge.judge_pin), 4)
        self.assertFalse(judge.has_checked_in)

    def test_ignores_staff_only_fields(self):
        r = self.client.post(
            self.url, {**self.payload, "has_checked_in": True, "judge_pin": "0000"}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertFalse(JudgeModel.objects.get().has_checked_in)

    def test_rejects_duplicate_email_case_insensitively(self):
        self.client.post(self.url, self.payload, format="json")
        r = self.client.post(
            self.url, {**self.payload, "email": "grace@example.COM"}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", r.data)

    def test_requires_category_and_timeslot(self):
        r = self.client.post(
            self.url, {**self.payload, "judging_category": [], "judging_timeslot": []}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("judging_category", r.data)
        self.assertIn("judging_timeslot", r.data)

    def test_requires_exactly_three_ranked_categories(self):
        r = self.client.post(
            self.url, {**self.payload, "judging_category": ["7", "2"]}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("judging_category", r.data)

        r = self.client.post(
            self.url, {**self.payload, "judging_category": ["7", "2", "1", "3"]}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("judging_category", r.data)

    def test_rejects_duplicate_ranked_categories(self):
        r = self.client.post(
            self.url, {**self.payload, "judging_category": ["7", "2", "7"]}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("judging_category", r.data)

    def test_lunch_preference_required_when_attending(self):
        r = self.client.post(self.url, {**self.payload, "lunch_preference": None}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("lunch_preference", r.data)

    def test_lunch_preference_cleared_when_not_attending(self):
        r = self.client.post(self.url, {**self.payload, "is_attending_lunch": False}, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(JudgeModel.objects.get().lunch_preference)

    def test_rejects_out_of_range_project_count(self):
        r = self.client.post(self.url, {**self.payload, "number_of_projects": 11}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("number_of_projects", r.data)


def make_judge(n, categories, slots, projects=10, backup=False):
    return JudgeModel.objects.create(
        first_name=f"Judge{n}",
        last_name="Test",
        email=f"judge{n}@example.com",
        phone_number="555-0100",
        employer_name="Acme",
        judging_category=categories,
        judging_timeslot=slots,
        number_of_projects=projects,
        is_backup_judge=backup,
    )


def make_team(n, category):
    return StudentModel.objects.create(
        team_name=f"Team {n:02d}", team_category=category, booth_number=str(n)
    )


class JudgeAssignmentSolverTests(TestCase):
    def test_every_team_gets_min_judges_in_distinct_spread_slots(self):
        for n in range(6):
            make_judge(n, ["7"], SLOT_KEYS, projects=5)
        teams = [make_team(n, "7") for n in range(5)]

        result = generate_assignments()

        self.assertEqual(result.status, "optimal")
        self.assertEqual(result.shortfalls, [])
        for team in teams:
            mine = [a for a in result.assignments if a.student == team]
            self.assertEqual(len(mine), DEFAULT_MIN_JUDGES)
            self.assertEqual(len({a.judge.id for a in mine}), DEFAULT_MIN_JUDGES)
            slots = sorted(SLOT_KEYS.index(a.timeslot) for a in mine)
            self.assertEqual(len(set(slots)), DEFAULT_MIN_JUDGES)
            self.assertTrue(all(b - a > 1 for a, b in zip(slots, slots[1:])))

    def test_respects_judge_slots_categories_and_capacity(self):
        judges = [
            make_judge(0, ["1", "7"], ["1", "4", "7"], projects=2),
            make_judge(1, ["7"], ["2", "5", "8", "10"], projects=3),
            make_judge(2, ["1"], ["3", "6", "9"], projects=3),
            make_judge(3, ["7", "1"], SLOT_KEYS, projects=5),
        ]
        make_team(0, "7")
        make_team(1, "1")
        make_team(2, "7")

        result = generate_assignments()

        by_id = {j.id: j for j in judges}
        load = {}
        seen_judge_slot = set()
        for a in result.assignments:
            judge = by_id[a.judge.id]
            self.assertIn(a.timeslot, list(judge.judging_timeslot))
            self.assertIn(a.student.team_category, list(judge.judging_category))
            self.assertNotIn((judge.id, a.timeslot), seen_judge_slot)
            seen_judge_slot.add((judge.id, a.timeslot))
            load[judge.id] = load.get(judge.id, 0) + 1
        for judge_id, count in load.items():
            self.assertLessEqual(count, by_id[judge_id].number_of_projects)

    def test_backup_judges_are_never_assigned(self):
        for n in range(5):
            make_judge(n, ["2"], SLOT_KEYS)
        backup = make_judge(99, ["2"], SLOT_KEYS, backup=True)
        make_team(0, "2")
        make_team(1, "2")

        result = generate_assignments()

        self.assertFalse(any(a.judge.id == backup.id for a in result.assignments))
        self.assertEqual(result.shortfalls, [])

    def test_reports_shortfall_when_category_lacks_judges(self):
        make_judge(0, ["3"], SLOT_KEYS)
        make_judge(1, ["3"], SLOT_KEYS)
        make_judge(2, ["4"], SLOT_KEYS)
        team = make_team(0, "3")

        result = generate_assignments()

        self.assertIn(result.status, ("optimal", "feasible"))
        self.assertEqual(len(result.shortfalls), 1)
        shortfall = result.shortfalls[0]
        self.assertEqual(shortfall["student_id"], team.id)
        self.assertEqual(shortfall["assigned"], 2)
        self.assertIn("Only 2", shortfall["reason"])

    def test_max_judges_allows_extra_judges(self):
        for n in range(5):
            make_judge(n, ["5"], SLOT_KEYS)
        make_team(0, "5")

        result = generate_assignments(min_judges=3, max_judges=5)

        self.assertEqual(len(result.assignments), 5)

    def test_custom_min_judges_overrides_default(self):
        for n in range(5):
            make_judge(n, ["5"], SLOT_KEYS)
        make_team(0, "5")

        result = generate_assignments(min_judges=3)

        self.assertEqual(len(result.assignments), 3)
        self.assertEqual(result.shortfalls, [])


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class JudgeAssignmentAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="expochair", email="expo@test.edu", password="ceastribunal", is_staff=True
        )
        self.exec_member = ExecMember.objects.create(user=self.user)
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        self.judges = [make_judge(n, ["7"], SLOT_KEYS, projects=2) for n in range(5)]
        self.teams = [make_team(n, "7") for n in range(2)]

    def _grant_expo_role(self):
        role = ExecRole.objects.create(role="EXPO Chair", description="", committee="pres")
        role.ExecMember.add(self.exec_member)

    def test_generate_requires_expo_role(self):
        r = self.client.post("/api/expo/assignments/generate/", {}, format="json")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_generate_replaces_existing_assignments(self):
        self._grant_expo_role()
        stale = JudgeAssignmentModel.objects.create(
            judge=self.judges[0], student=self.teams[0], timeslot="1"
        )

        r = self.client.post("/api/expo/assignments/generate/", {}, format="json")

        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["shortfalls"], [])
        expected = DEFAULT_MIN_JUDGES * len(self.teams)
        self.assertEqual(len(r.data["assignments"]), expected)
        self.assertFalse(JudgeAssignmentModel.objects.filter(pk=stale.pk).exists())
        self.assertEqual(JudgeAssignmentModel.objects.count(), expected)

    def test_generate_rejects_max_below_min(self):
        self._grant_expo_role()
        r = self.client.post(
            "/api/expo/assignments/generate/", {"min_judges": 3, "max_judges": 2}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_manual_assignment_rejects_double_booking(self):
        self._grant_expo_role()
        JudgeAssignmentModel.objects.create(
            judge=self.judges[0], student=self.teams[0], timeslot="1"
        )
        r = self.client.post(
            "/api/expo/assignments/",
            {"judge": self.judges[0].id, "student": self.teams[1].id, "timeslot": "1"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_filters_by_student(self):
        self._grant_expo_role()
        JudgeAssignmentModel.objects.create(
            judge=self.judges[0], student=self.teams[0], timeslot="1"
        )
        JudgeAssignmentModel.objects.create(
            judge=self.judges[1], student=self.teams[1], timeslot="1"
        )
        r = self.client.get(f"/api/expo/assignments/?student={self.teams[1].id}")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data), 1)
        self.assertEqual(r.data[0]["team_name"], self.teams[1].team_name)
