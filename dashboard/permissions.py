from rest_framework.permissions import BasePermission

from dashboard.models import ExecMember


def user_is_treasurer(user) -> bool:
    """Superusers or staff exec members with the Treasurer role."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not user.is_staff:
        return False
    try:
        em = ExecMember.objects.get(user=user)
    except ExecMember.DoesNotExist:
        return False
    for role_name in em.execrole_set.values_list("role", flat=True):
        if (role_name or "").strip().lower() == "treasurer":
            return True
    return False


def user_is_org_funding_chair(user) -> bool:
    """Superusers or staff exec members holding the Org Funding chair role."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not user.is_staff:
        return False
    try:
        em = ExecMember.objects.get(user=user)
    except ExecMember.DoesNotExist:
        return False
    for role_name in em.execrole_set.values_list("role", flat=True):
        name = (role_name or "").strip().lower()
        if "funding" in name and ("org" in name or "organization" in name):
            return True
    return False


class IsTreasurerOrSuperuserStaff(BasePermission):
    """
    Allows staff treasurers (ExecRole) or superusers to update reimbursement filing status.
    """

    message = "Treasurer access required to update filing status."

    def has_permission(self, request, view):
        return user_is_treasurer(request.user)


class IsOrgFundingChairOrSuperuserStaff(BasePermission):
    """
    Allows staff Org Funding chairs (ExecRole) or superusers to manage org funding
    submissions and available dates.
    """

    message = "Org Funding chair access required."

    def has_permission(self, request, view):
        return user_is_org_funding_chair(request.user)


class IsStaffUser(BasePermission):
    """
    Allows access only to authenticated users with is_staff=True.
    Used for Tribunal SPA admin APIs and JWT issuance.
    """

    message = "Staff access required."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_staff)
