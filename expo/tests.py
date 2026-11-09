from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from dashboard.models import ExecMember, ExecRole

from .assignment import SLOT_KEYS, generate_assignments
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
    def test_every_team_gets_three_judges_in_distinct_spread_slots(self):
        for n in range(4):
            make_judge(n, ["7"], SLOT_KEYS, projects=4)
        teams = [make_team(n, "7") for n in range(5)]

        result = generate_assignments()

        self.assertEqual(result.status, "optimal")
        self.assertEqual(result.shortfalls, [])
        for team in teams:
            mine = [a for a in result.assignments if a.student == team]
            self.assertEqual(len(mine), 3)
            self.assertEqual(len({a.judge.id for a in mine}), 3)
            slots = sorted(SLOT_KEYS.index(a.timeslot) for a in mine)
            self.assertEqual(len(set(slots)), 3)
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
        for n in range(3):
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
        self.judges = [make_judge(n, ["7"], SLOT_KEYS, projects=3) for n in range(3)]
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
        self.assertEqual(len(r.data["assignments"]), 6)
        self.assertFalse(JudgeAssignmentModel.objects.filter(pk=stale.pk).exists())
        self.assertEqual(JudgeAssignmentModel.objects.count(), 6)

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
