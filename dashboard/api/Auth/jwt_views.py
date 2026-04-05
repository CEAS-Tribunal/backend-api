from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .jwt_serializers import (
    StaffOnlyTokenObtainPairSerializer,
    StaffOnlyTokenRefreshSerializer,
)


class StaffOnlyTokenObtainPairView(TokenObtainPairView):
    serializer_class = StaffOnlyTokenObtainPairSerializer


class StaffOnlyTokenRefreshView(TokenRefreshView):
    serializer_class = StaffOnlyTokenRefreshSerializer
