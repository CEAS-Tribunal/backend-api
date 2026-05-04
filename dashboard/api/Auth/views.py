from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from dashboard.models import ExecMember
from dashboard.permissions import user_is_treasurer

from .serializers import ChangePasswordSerializer


class AuthMeView(APIView):
    """
    Return the current user and whether they must change their password (exec accounts only).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        try:
            em = ExecMember.objects.get(user=user)
            must_change = em.must_change_password
        except ExecMember.DoesNotExist:
            must_change = False

        is_exec = ExecMember.objects.filter(user=user).exists()

        return Response(
            {
                "username": user.username,
                "email": user.email or "",
                "first_name": user.first_name or "",
                "last_name": user.last_name or "",
                "must_change_password": must_change,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "is_exec": is_exec,
                "is_treasurer": user_is_treasurer(user),
            },
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(APIView):
    """
    Change password for authenticated users linked to ExecMember.
    Runs Django password validators (including TribunalPasswordValidator) and clears must_change_password.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        old = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]

        if not user.check_password(old):
            return Response(
                {"old_password": ["Current password is not correct."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            em = ExecMember.objects.get(user=user)
        except ExecMember.DoesNotExist:
            return Response(
                {"detail": "This account is not linked to an executive profile."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as exc:
            return Response(
                {"new_password": list(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])
        em.must_change_password = False
        em.save(update_fields=["must_change_password"])

        return Response(
            {"detail": "Password updated successfully."},
            status=status.HTTP_200_OK,
        )
