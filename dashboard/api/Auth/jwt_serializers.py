from django.contrib.auth import get_user_model
from rest_framework import exceptions
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.settings import api_settings

User = get_user_model()


class StaffOnlyTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Same as SimpleJWT pair serializer, but rejects users who are not staff.
    Tribunal SPA admin and Django admin are both limited to staff accounts.
    """

    default_error_messages = {
        **TokenObtainPairSerializer.default_error_messages,
        "not_staff": "Staff accounts only. Contact an administrator.",
    }

    def validate(self, attrs):
        data = super().validate(attrs)
        if not self.user.is_staff:
            raise exceptions.PermissionDenied(
                self.error_messages["not_staff"],
                code="not_staff",
            )
        return data


class StaffOnlyTokenRefreshSerializer(TokenRefreshSerializer):
    """Refresh access token only if the user is still staff."""

    default_error_messages = {
        **getattr(TokenRefreshSerializer, "default_error_messages", {}),
        "not_staff": "Staff access required. Your session cannot be refreshed.",
    }

    def validate(self, attrs):
        refresh = self.token_class(attrs["refresh"])
        uid = refresh[api_settings.USER_ID_CLAIM]
        try:
            user = User.objects.get(**{api_settings.USER_ID_FIELD: uid})
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed(
                "User not found for this token.",
                code="user_not_found",
            )
        if not user.is_staff:
            raise exceptions.PermissionDenied(
                self.error_messages["not_staff"],
                code="not_staff",
            )
        return super().validate(attrs)
