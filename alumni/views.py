from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import AlumniProfile
from .serializers import AlumniProfileSerializer


class AlumniProfileListView(generics.ListAPIView):
    queryset = AlumniProfile.objects.all().order_by("-graduation_year")
    serializer_class = AlumniProfileSerializer
    permission_classes = [AllowAny]
    pagination_class = None