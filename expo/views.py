from django.db import transaction
from django.db.models import IntegerField
from django.db.models.functions import Cast

from .assignment import generate_assignments
from .models import JudgeAssignmentModel, JudgeModel, StudentModel
from .serializers import (
    GenerateAssignmentsSerializer,
    JudgeAssignmentSerializer,
    JudgeCheckInPatchSerializer,
    JudgeSerializer,
    StudentSerializer,
)
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from dashboard.permissions import IsExpoStaff


class JudgeViewSet(viewsets.ModelViewSet):
    queryset = JudgeModel.objects.all().order_by("last_name", "first_name")
    serializer_class = JudgeSerializer
    permission_classes = [IsAuthenticated, IsExpoStaff]
    pagination_class = None
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['first_name', 'last_name', 'email', 'phone_number', 'employer_name']
    ordering_fields = ['first_name', 'last_name', 'email', 'phone_number', 'employer_name', 'has_checked_in']

    @action(detail=True, methods=["patch"], url_path="check-in")
    def check_in(self, request, pk=None):
        judge = self.get_object()
        serializer = JudgeCheckInPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        judge.has_checked_in = serializer.validated_data["has_checked_in"]
        judge.save(update_fields=["has_checked_in"])
        return Response(JudgeSerializer(judge).data, status=status.HTTP_200_OK)


class StudentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StudentModel.objects.all().order_by("team_name")
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated, IsExpoStaff]
    pagination_class = None


class JudgeAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = JudgeAssignmentSerializer
    permission_classes = [IsAuthenticated, IsExpoStaff]
    pagination_class = None

    def get_queryset(self):
        queryset = JudgeAssignmentModel.objects.select_related("judge", "student").order_by(
            "student__team_name", Cast("timeslot", IntegerField())
        )
        judge_id = self.request.query_params.get("judge")
        student_id = self.request.query_params.get("student")
        if judge_id:
            queryset = queryset.filter(judge_id=judge_id)
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        return queryset

    @action(detail=False, methods=["post"])
    def generate(self, request):
        params = GenerateAssignmentsSerializer(data=request.data)
        params.is_valid(raise_exception=True)
        result = generate_assignments(
            min_judges=params.validated_data["min_judges"],
            max_judges=params.validated_data.get("max_judges"),
        )
        if result.status not in ("optimal", "feasible"):
            return Response(
                {"detail": f"Solver could not produce a schedule (status: {result.status})."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        with transaction.atomic():
            JudgeAssignmentModel.objects.all().delete()
            JudgeAssignmentModel.objects.bulk_create(
                JudgeAssignmentModel(judge=a.judge, student=a.student, timeslot=a.timeslot)
                for a in result.assignments
            )

        return Response(
            {
                "status": result.status,
                "assignments": JudgeAssignmentSerializer(self.get_queryset(), many=True).data,
                "shortfalls": result.shortfalls,
            },
            status=status.HTTP_200_OK,
        )
