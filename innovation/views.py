from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from statistics import fmean, pstdev

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from dashboard.permissions import IsStaffUser

from .models import InnovationRoom, Judge, JudgingSubmission, Team
from .serializers import JudgeSerializer, JudgingSubmissionSerializer, TeamSerializer


def _round_score(value):
    return float(Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def _judge_z_score(score, judge_scores, overall_mean, overall_stddev):
    """Normalize within a judge when possible; otherwise retain the cohort-relative score."""
    if len(judge_scores) >= 2:
        judge_stddev = pstdev(judge_scores)
        if judge_stddev > 0:
            return (score - fmean(judge_scores)) / judge_stddev

    if overall_stddev == 0:
        return 0
    return (score - overall_mean) / overall_stddev


class StaffAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStaffUser]


class RoomListView(StaffAPIView):
    def get(self, request):
        return Response(
            [
                {"value": room.value, "label": room.label}
                for room in InnovationRoom
            ]
        )


class JudgeListCreateView(StaffAPIView):
    def get(self, request):
        judges = Judge.objects.filter(is_active=True)
        return Response(JudgeSerializer(judges, many=True).data)

    def post(self, request):
        serializer = JudgeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        judge = serializer.save()
        return Response(JudgeSerializer(judge).data, status=status.HTTP_201_CREATED)


class JudgeDetailView(StaffAPIView):
    def patch(self, request, pk):
        judge = get_object_or_404(Judge, pk=pk, is_active=True)
        serializer = JudgeSerializer(judge, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(JudgeSerializer(serializer.save()).data)

    def delete(self, request, pk):
        judge = get_object_or_404(Judge, pk=pk, is_active=True)
        judge.is_active = False
        judge.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class TeamListCreateView(StaffAPIView):
    def get(self, request):
        teams = Team.objects.filter(is_active=True)
        return Response(TeamSerializer(teams, many=True).data)

    def post(self, request):
        serializer = TeamSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        team = serializer.save()
        return Response(TeamSerializer(team).data, status=status.HTTP_201_CREATED)


class TeamDetailView(StaffAPIView):
    def patch(self, request, pk):
        team = get_object_or_404(Team, pk=pk, is_active=True)
        serializer = TeamSerializer(team, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(TeamSerializer(serializer.save()).data)

    def delete(self, request, pk):
        team = get_object_or_404(Team, pk=pk, is_active=True)
        team.is_active = False
        team.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


def _query_id(request, field):
    value = request.query_params.get(field)
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise serializers.ValidationError({field: ["A valid integer is required."]})
    if parsed < 1:
        raise serializers.ValidationError({field: ["A valid integer is required."]})
    return parsed


class SubmissionListCreateView(StaffAPIView):
    def get(self, request):
        judge_id = _query_id(request, "judge_id")
        team_id = _query_id(request, "team_id")
        submissions = JudgingSubmission.objects.select_related("judge", "team")
        if judge_id is not None:
            submissions = submissions.filter(judge_id=judge_id)
        if team_id is not None:
            submissions = submissions.filter(team_id=team_id)
        if judge_id is not None and team_id is not None:
            submission = submissions.first()
            if submission is None:
                return Response(status=status.HTTP_404_NOT_FOUND)
            return Response(JudgingSubmissionSerializer(submission).data)
        return Response(JudgingSubmissionSerializer(submissions, many=True).data)

    def post(self, request):
        serializer = JudgingSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        judge = serializer.validated_data["judge"]
        team = serializer.validated_data["team"]

        try:
            with transaction.atomic():
                existing = (
                    JudgingSubmission.objects.select_for_update()
                    .filter(judge=judge, team=team)
                    .first()
                )
                if existing:
                    serializer.instance = existing
                    submission = serializer.save()
                    response_status = status.HTTP_200_OK
                else:
                    submission = serializer.save()
                    response_status = status.HTTP_201_CREATED
        except IntegrityError:
            submission = JudgingSubmission.objects.get(judge=judge, team=team)
            serializer.instance = submission
            submission = serializer.save()
            response_status = status.HTTP_200_OK

        return Response(
            JudgingSubmissionSerializer(submission).data,
            status=response_status,
        )


class SubmissionDetailView(StaffAPIView):
    def patch(self, request, pk):
        submission = get_object_or_404(
            JudgingSubmission.objects.select_related("judge", "team"),
            pk=pk,
        )
        serializer = JudgingSubmissionSerializer(
            submission,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        return Response(JudgingSubmissionSerializer(serializer.save()).data)


class ResultsListView(StaffAPIView):
    def get(self, request):
        """Calculate judge normalization across all submissions before applying filters."""
        judge_id = _query_id(request, "judge_id")
        room = (request.query_params.get("room") or "").strip()
        all_submissions = list(
            JudgingSubmission.objects.select_related("judge", "team")
        )
        overall_scores = [
            submission.scores["overall-rating"] for submission in all_submissions
        ]
        overall_mean = fmean(overall_scores) if overall_scores else 0
        overall_stddev = pstdev(overall_scores) if len(overall_scores) > 1 else 0

        scores_by_judge = defaultdict(list)
        for submission in all_submissions:
            scores_by_judge[submission.judge_id].append(
                submission.scores["overall-rating"]
            )

        filtered_submissions = [
            submission
            for submission in all_submissions
            if (judge_id is None or submission.judge_id == judge_id)
            and (not room or submission.team.room.casefold() == room.casefold())
        ]

        results = {}
        for submission in filtered_submissions:
            score = submission.scores["overall-rating"]
            result = results.setdefault(
                submission.team_id,
                {
                    "team_id": submission.team_id,
                    "team_name": submission.team.name,
                    "room": submission.team.room,
                    "submission_count": 0,
                    "score_total": 0,
                    "z_score_total": 0,
                },
            )
            result["submission_count"] += 1
            result["score_total"] += score
            result["z_score_total"] += _judge_z_score(
                score,
                scores_by_judge[submission.judge_id],
                overall_mean,
                overall_stddev,
            )

        response_data = []
        for result in results.values():
            submission_count = result["submission_count"]
            average_z_score = result.pop("z_score_total") / submission_count
            corrected_score = overall_mean + overall_stddev * average_z_score
            result["average_score"] = _round_score(
                result.pop("score_total") / submission_count
            )
            result["average_z_score"] = round(average_z_score, 3)
            result["average_corrected_score"] = _round_score(
                min(10, max(1, corrected_score))
            )
            response_data.append(result)
        response_data.sort(key=lambda result: result["team_name"].casefold())
        return Response(response_data)
