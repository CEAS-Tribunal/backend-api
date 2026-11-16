from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from dashboard.models import ExecMember, ExecRole

from .models import InnovationRoom, Judge, JudgingSubmission, Team
from .serializers import RUBRIC_CRITERIA


def _scores(value=7):
    return {criterion: value for criterion in RUBRIC_CRITERIA}


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class InnovationJudgingAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user(username="judge-admin", password="pass12345")
        self.staff.is_staff = True
        self.staff.save(update_fields=["is_staff"])
        self.exec_member = ExecMember.objects.create(user=self.staff)
        president_role = ExecRole.objects.create(
            role="President",
            description="President",
            committee="pres",
        )
        president_role.ExecMember.add(self.exec_member)
        self.client.force_authenticate(user=self.staff)
        self.judge = Judge.objects.create(name="Alex Smith", room=InnovationRoom.FRONT_OF_KAUTZ_ATTIC)
        self.team = Team.objects.create(name="AeroSense", room=InnovationRoom.FRONT_OF_KAUTZ_ATTIC)

    def test_endpoints_require_staff(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(
            self.client.get("/api/innovation/judges/").status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            self.client.get("/api/innovation/room-configuration/").status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        outsider = User.objects.create_user(username="outsider", password="pass12345")
        self.client.force_authenticate(user=outsider)
        self.assertEqual(
            self.client.get("/api/innovation/judges/").status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_only_approved_staff_roles_can_read_results(self):
        unauthorized_staff = User.objects.create_user(
            username="staff-without-dashboard-role",
            password="pass12345",
            is_staff=True,
        )
        self.client.force_authenticate(user=unauthorized_staff)
        self.assertEqual(
            self.client.get("/api/innovation/results/").status_code,
            status.HTTP_403_FORBIDDEN,
        )

        superuser = User.objects.create_superuser(
            username="unassigned-superuser",
            email="superuser@example.com",
            password="pass12345",
        )
        self.client.force_authenticate(user=superuser)
        self.assertEqual(
            self.client.get("/api/innovation/results/").status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_each_approved_staff_role_can_read_results(self):
        for index, role_name in enumerate(
            (
                "Innovation Challenge Chair",
                "Technology Chair",
                "Chief of Staff",
                "President",
            )
        ):
            with self.subTest(role=role_name):
                user = User.objects.create_user(
                    username=f"approved-dashboard-role-{index}",
                    password="pass12345",
                    is_staff=True,
                )
                member = ExecMember.objects.create(user=user)
                role = ExecRole.objects.create(
                    role=role_name,
                    description=role_name,
                    committee="pres",
                )
                role.ExecMember.add(member)
                self.client.force_authenticate(user=user)
                self.assertEqual(
                    self.client.get("/api/innovation/results/").status_code,
                    status.HTTP_200_OK,
                )

    def test_rooms_endpoint_returns_rooms_for_the_saved_room_count(self):
        response = self.client.get("/api/innovation/rooms/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            [
                {"value": room.value, "label": room.label}
                for room in (
                    InnovationRoom.FRONT_OF_KAUTZ_ATTIC,
                    InnovationRoom.BACK_OF_KAUTZ_ATTIC,
                )
            ],
        )

        configuration = self.client.get("/api/innovation/room-configuration/")
        self.assertEqual(configuration.status_code, status.HTTP_200_OK)
        self.assertEqual(configuration.data, {"room_count": 2})

        updated_configuration = self.client.patch(
            "/api/innovation/room-configuration/",
            {"room_count": 3},
            format="json",
        )
        self.assertEqual(updated_configuration.status_code, status.HTTP_200_OK)
        self.assertEqual(updated_configuration.data, {"room_count": 3})
        self.assertEqual(
            self.client.get("/api/innovation/rooms/").data,
            [
                {"value": room.value, "label": room.label}
                for room in InnovationRoom
            ],
        )

    def test_two_room_mode_retains_existing_lindner_assignments(self):
        self.client.patch(
            "/api/innovation/room-configuration/",
            {"room_count": 3},
            format="json",
        )
        lindner_judge = self.client.post(
            "/api/innovation/judges/",
            {"name": "Lindner Judge", "room": InnovationRoom.LINDNER_4210},
            format="json",
        )
        lindner_team = self.client.post(
            "/api/innovation/teams/",
            {"name": "Lindner Team", "room": InnovationRoom.LINDNER_4210},
            format="json",
        )
        self.assertEqual(lindner_judge.status_code, status.HTTP_201_CREATED)
        self.assertEqual(lindner_team.status_code, status.HTTP_201_CREATED)

        self.client.patch(
            "/api/innovation/room-configuration/",
            {"room_count": 2},
            format="json",
        )

        self.assertEqual(
            self.client.post(
                "/api/innovation/judges/",
                {"name": "New Lindner Judge", "room": InnovationRoom.LINDNER_4210},
                format="json",
            ).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            self.client.post(
                "/api/innovation/teams/",
                {"name": "New Lindner Team", "room": InnovationRoom.LINDNER_4210},
                format="json",
            ).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            self.client.patch(
                f"/api/innovation/judges/{self.judge.id}/",
                {"room": InnovationRoom.LINDNER_4210},
                format="json",
            ).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            self.client.patch(
                f"/api/innovation/judges/{lindner_judge.data['id']}/",
                {"name": "Retained Lindner Judge", "room": InnovationRoom.LINDNER_4210},
                format="json",
            ).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(lindner_team.data["room"], InnovationRoom.LINDNER_4210)
        self.assertEqual(Judge.objects.get(pk=lindner_judge.data["id"]).room, InnovationRoom.LINDNER_4210)
        self.assertEqual(Team.objects.get(pk=lindner_team.data["id"]).room, InnovationRoom.LINDNER_4210)
        self.assertEqual(
            [room["value"] for room in self.client.get("/api/innovation/rooms/").data],
            [
                InnovationRoom.FRONT_OF_KAUTZ_ATTIC,
                InnovationRoom.BACK_OF_KAUTZ_ATTIC,
            ],
        )

    def test_judge_and_team_crud_archives_instead_of_deleting(self):
        judge_response = self.client.post(
            "/api/innovation/judges/",
            {"name": "  Morgan Lee  ", "room": "  Front of Kautz Attic  "},
            format="json",
        )
        self.assertEqual(judge_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(judge_response.data["name"], "Morgan Lee")
        self.assertEqual(judge_response.data["room"], InnovationRoom.FRONT_OF_KAUTZ_ATTIC)
        judge_id = judge_response.data["id"]

        team_response = self.client.post(
            "/api/innovation/teams/",
            {"name": "  RiverBot  ", "room": "  Back of Kautz Attic  "},
            format="json",
        )
        self.assertEqual(team_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(team_response.data["room"], InnovationRoom.BACK_OF_KAUTZ_ATTIC)
        team_id = team_response.data["id"]

        self.client.patch(
            "/api/innovation/room-configuration/",
            {"room_count": 3},
            format="json",
        )
        self.assertEqual(
            self.client.patch(
                f"/api/innovation/judges/{judge_id}/",
                {"name": "Morgan L.", "room": InnovationRoom.LINDNER_4210},
                format="json",
            ).data["room"],
            InnovationRoom.LINDNER_4210,
        )
        self.assertEqual(
            self.client.patch(
                f"/api/innovation/teams/{team_id}/",
                {"room": InnovationRoom.LINDNER_4210},
                format="json",
            ).data["room"],
            InnovationRoom.LINDNER_4210,
        )
        self.assertEqual(
            self.client.delete(f"/api/innovation/judges/{judge_id}/").status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertEqual(
            self.client.delete(f"/api/innovation/teams/{team_id}/").status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(Judge.objects.get(pk=judge_id).is_active)
        self.assertFalse(Team.objects.get(pk=team_id).is_active)

    def test_duplicate_active_names_are_case_insensitive(self):
        judge = self.client.post(
            "/api/innovation/judges/",
            {"name": "aLeX sMiTh", "room": InnovationRoom.FRONT_OF_KAUTZ_ATTIC},
            format="json",
        )
        team = self.client.post(
            "/api/innovation/teams/",
            {"name": "AEROSENSE", "room": InnovationRoom.BACK_OF_KAUTZ_ATTIC},
            format="json",
        )
        self.assertEqual(judge.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", judge.data)
        self.assertEqual(team.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", team.data)

    def test_rooms_must_be_one_of_the_static_choices(self):
        for endpoint, payload in (
            ("/api/innovation/judges/", {"name": "Judge", "room": "Room 1"}),
            ("/api/innovation/teams/", {"name": "Team", "room": "Room 1"}),
        ):
            with self.subTest(endpoint=endpoint):
                response = self.client.post(endpoint, payload, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("room", response.data)

    def test_blank_names_and_rooms_are_rejected(self):
        judge = self.client.post(
            "/api/innovation/judges/",
            {"name": "Judge", "room": "  "},
            format="json",
        )
        team = self.client.post(
            "/api/innovation/teams/",
            {"name": "Team", "room": "  "},
            format="json",
        )
        self.assertEqual(judge.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(team.status_code, status.HTTP_400_BAD_REQUEST)

    def test_judge_requires_room(self):
        response = self.client.post(
            "/api/innovation/judges/",
            {"name": "Taylor Jones"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("room", response.data)

    def test_submission_upserts_pair_and_returns_archived_relationships(self):
        payload = {
            "judge_id": self.judge.id,
            "team_id": self.team.id,
            "scores": _scores(7),
            "feedback": "Good prototype.",
        }
        created = self.client.post(
            "/api/innovation/submissions/",
            payload,
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["room"], InnovationRoom.FRONT_OF_KAUTZ_ATTIC)

        payload["scores"] = _scores(9)
        payload["feedback"] = "Updated."
        updated = self.client.post(
            "/api/innovation/submissions/",
            payload,
            format="json",
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertEqual(updated.data["id"], created.data["id"])
        self.assertEqual(updated.data["scores"], _scores(9))
        self.assertEqual(JudgingSubmission.objects.count(), 1)

        self.assertEqual(
            self.client.delete(f"/api/innovation/judges/{self.judge.id}/").status_code,
            status.HTTP_204_NO_CONTENT,
        )

        updated = self.client.post(
            "/api/innovation/submissions/",
            payload,
            format="json",
        )
        self.assertEqual(updated.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(JudgingSubmission.objects.count(), 1)

        archived_read = self.client.get(
            "/api/innovation/submissions/",
            {"judge_id": self.judge.id, "team_id": self.team.id},
        )
        self.assertEqual(archived_read.status_code, status.HTTP_200_OK)
        self.assertEqual(archived_read.data["judge_name"], "Alex Smith")

    def test_submission_scores_require_all_known_integer_values(self):
        payload = {
            "judge_id": self.judge.id,
            "team_id": self.team.id,
            "scores": _scores(),
        }
        payload["scores"].pop("growth")
        self.assertEqual(
            self.client.post("/api/innovation/submissions/", payload, format="json").status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        payload["scores"] = _scores()
        payload["scores"]["growth"] = True
        self.assertEqual(
            self.client.post("/api/innovation/submissions/", payload, format="json").status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        payload["scores"] = _scores()
        payload["scores"]["overall-rating"] = 11
        self.assertEqual(
            self.client.post("/api/innovation/submissions/", payload, format="json").status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(JudgingSubmission.objects.count(), 0)

    def test_patch_updates_scores_or_feedback(self):
        submission = JudgingSubmission.objects.create(
            judge=self.judge,
            team=self.team,
            scores=_scores(),
        )
        response = self.client.patch(
            f"/api/innovation/submissions/{submission.id}/",
            {"feedback": "Updated feedback"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["feedback"], "Updated feedback")
        self.assertEqual(response.data["scores"], _scores())

    def test_results_aggregate_filter_and_round_scores(self):
        second_judge = Judge.objects.create(name="Taylor Jones", room=InnovationRoom.BACK_OF_KAUTZ_ATTIC)
        second_team = Team.objects.create(name="Beta Team", room=InnovationRoom.BACK_OF_KAUTZ_ATTIC)
        JudgingSubmission.objects.create(
            judge=self.judge,
            team=self.team,
            scores=_scores(8),
        )
        JudgingSubmission.objects.create(
            judge=second_judge,
            team=self.team,
            scores=_scores(9),
        )
        JudgingSubmission.objects.create(
            judge=self.judge,
            team=second_team,
            scores=_scores(6),
        )

        response = self.client.get("/api/innovation/results/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        aero = next(item for item in response.data if item["team_id"] == self.team.id)
        self.assertEqual(aero["submission_count"], 2)
        self.assertEqual(aero["average_score"], 8.5)

        filtered = self.client.get(
            "/api/innovation/results/",
            {"judge_id": self.judge.id, "room": "front of kautz attic"},
        )
        self.assertEqual(len(filtered.data), 1)
        self.assertEqual(filtered.data[0]["team_id"], self.team.id)

    def test_raw_scores_average_every_criterion_per_judge_and_team(self):
        second_judge = Judge.objects.create(
            name="Taylor Jones",
            room=InnovationRoom.BACK_OF_KAUTZ_ATTIC,
        )
        first_scores = _scores(5)
        first_scores["overall-rating"] = 10
        second_scores = _scores(8)
        second_scores["overall-rating"] = 1
        JudgingSubmission.objects.create(
            judge=self.judge,
            team=self.team,
            scores=first_scores,
        )
        JudgingSubmission.objects.create(
            judge=second_judge,
            team=self.team,
            scores=second_scores,
        )

        submissions = self.client.get("/api/innovation/submissions/").data
        raw_scores_by_judge = {
            submission["judge_name"]: submission["raw_score"]
            for submission in submissions
        }
        self.assertEqual(raw_scores_by_judge["Alex Smith"], 5.6)
        self.assertEqual(raw_scores_by_judge["Taylor Jones"], 7.2)
        self.assertTrue(
            all(
                submission["overall_score_correction"] == 0.0
                for submission in submissions
            )
        )

        results = self.client.get("/api/innovation/results/").data
        self.assertEqual(results[0]["average_score"], 6.4)
        self.assertEqual(results[0]["average_z_score"], 0.0)
        self.assertEqual(results[0]["average_corrected_score"], 6.4)

    def test_results_z_score_corrects_for_judge_severity(self):
        lenient_judge = Judge.objects.create(name="Lenient Judge", room=InnovationRoom.FRONT_OF_KAUTZ_ATTIC)
        harsh_judge = Judge.objects.create(name="Harsh Judge", room=InnovationRoom.FRONT_OF_KAUTZ_ATTIC)
        team_a = Team.objects.create(name="Team A", room=InnovationRoom.FRONT_OF_KAUTZ_ATTIC)
        team_b = Team.objects.create(name="Team B", room=InnovationRoom.FRONT_OF_KAUTZ_ATTIC)
        team_c = Team.objects.create(name="Team C", room=InnovationRoom.FRONT_OF_KAUTZ_ATTIC)

        JudgingSubmission.objects.create(
            judge=harsh_judge,
            team=team_a,
            scores=_scores(4),
        )
        JudgingSubmission.objects.create(
            judge=harsh_judge,
            team=team_b,
            scores=_scores(5),
        )
        JudgingSubmission.objects.create(
            judge=lenient_judge,
            team=team_b,
            scores=_scores(9),
        )
        JudgingSubmission.objects.create(
            judge=lenient_judge,
            team=team_c,
            scores=_scores(10),
        )

        response = self.client.get("/api/innovation/results/")
        results = {item["team_name"]: item for item in response.data}

        self.assertEqual(results["Team A"]["average_score"], 4.0)
        self.assertEqual(results["Team A"]["average_z_score"], -1.0)
        self.assertEqual(results["Team A"]["average_corrected_score"], 4.5)
        self.assertEqual(results["Team B"]["average_score"], 7.0)
        self.assertEqual(results["Team B"]["average_z_score"], 0.0)
        self.assertEqual(results["Team B"]["average_corrected_score"], 7.0)
        self.assertEqual(results["Team C"]["average_score"], 10.0)
        self.assertEqual(results["Team C"]["average_z_score"], 1.0)
        self.assertEqual(results["Team C"]["average_corrected_score"], 9.5)

        submissions = self.client.get("/api/innovation/submissions/").data
        corrections = {
            (submission["team_name"], submission["judge_name"]): submission[
                "overall_score_correction"
            ]
            for submission in submissions
        }
        self.assertAlmostEqual(
            corrections[("Team A", "Harsh Judge")], 0.5
        )
        self.assertAlmostEqual(
            corrections[("Team B", "Harsh Judge")], 4.5
        )
        self.assertAlmostEqual(
            corrections[("Team B", "Lenient Judge")], -4.5
        )
        self.assertAlmostEqual(
            corrections[("Team C", "Lenient Judge")], -0.5
        )

    def test_results_fall_back_to_raw_ratings_without_judge_variance(self):
        second_judge = Judge.objects.create(name="Second Judge", room=InnovationRoom.BACK_OF_KAUTZ_ATTIC)
        second_team = Team.objects.create(name="Second Team", room=InnovationRoom.BACK_OF_KAUTZ_ATTIC)
        JudgingSubmission.objects.create(
            judge=self.judge,
            team=self.team,
            scores=_scores(5),
        )
        JudgingSubmission.objects.create(
            judge=second_judge,
            team=second_team,
            scores=_scores(9),
        )

        response = self.client.get("/api/innovation/results/")
        results = {item["team_name"]: item for item in response.data}

        self.assertEqual(results["AeroSense"]["average_corrected_score"], 5.0)
        self.assertEqual(results["Second Team"]["average_corrected_score"], 9.0)
