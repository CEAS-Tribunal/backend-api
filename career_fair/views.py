from django.db.models import Q
from rest_framework import generics, status
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from dashboard.permissions import IsStaffUser

from .models import Representative
from .serializers import RepresentativePrintedPatchSerializer, RepresentativeSerializer


class RepresentativeListCreateView(generics.ListCreateAPIView):
    """
    POST: public — career fair representative sign-in (admin UI calls this after login).
    GET: authenticated — list representatives; optional ?search= filters name and company.
    """

    serializer_class = RepresentativeSerializer

    def get_queryset(self):
        qs = Representative.objects.all()
        search = (self.request.query_params.get("search") or "").strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(company__icontains=search))
        return qs

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]
        return [IsAuthenticated(), IsStaffUser()]


class RepresentativePrintedUpdateView(APIView):
    """Staff: mark whether a representative name tag has been printed."""

    permission_classes = [IsAuthenticated, IsStaffUser]
    parser_classes = [JSONParser]

    def patch(self, request, pk):
        try:
            rep = Representative.objects.get(pk=pk)
        except Representative.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = RepresentativePrintedPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rep.is_printed = serializer.validated_data["is_printed"]
        rep.save(update_fields=["is_printed"])

        return Response(
            RepresentativeSerializer(rep).data,
            status=status.HTTP_200_OK,
        )
