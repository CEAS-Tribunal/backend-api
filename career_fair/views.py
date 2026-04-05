from django.db.models import Q
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated

from dashboard.permissions import IsStaffUser

from .models import Representative
from .serializers import RepresentativeSerializer


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
