from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import AlumniProfile
from .serializers import AlumniProfileSerializer


class AlumniProfileListView(generics.ListAPIView):
    queryset = AlumniProfile.objects.all().order_by("-graduation_year")
    serializer_class = AlumniProfileSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    @method_decorator(cache_page(60 * 60 * 24, key_prefix='alumni_profile_list'))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)