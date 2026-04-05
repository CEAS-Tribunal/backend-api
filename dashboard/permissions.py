from rest_framework.permissions import BasePermission


class IsStaffUser(BasePermission):
    """
    Allows access only to authenticated users with is_staff=True.
    Used for Tribunal SPA admin APIs and JWT issuance.
    """

    message = "Staff access required."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_staff)
