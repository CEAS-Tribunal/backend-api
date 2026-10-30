from .models import JudgeModel
from .serializers import JudgeCheckInPatchSerializer, JudgeSerializer
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
