from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from dashboard.models import ExecMember
from dashboard.permissions import IsStaffUser

from .models import ReimbursementRequest, UserProfile
from .serializers import ReimbursementRequestCreateSerializer


def _display_name(user) -> str:
    name = user.get_full_name().strip()
    if name:
        return name[:255]
    return (user.username or "")[:255]


def _exec_position(user) -> str:
    try:
        em = ExecMember.objects.get(user=user)
    except ExecMember.DoesNotExist:
        return ""
    roles = em.execrole_set.order_by("role").values_list("role", flat=True)
    joined = ", ".join(roles)
    return joined[:255]


class ReimbursementRequestCreateView(APIView):
    """
    Staff-only: create a reimbursement row from multipart form data.
    Member identity fields come from the JWT user and reimbursement UserProfile;
    M number is supplied by the client per request.
    """

    permission_classes = [IsStaffUser]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = ReimbursementRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            profile = request.user.reimbursement_profile
        except UserProfile.DoesNotExist:
            return Response(
                {
                    "detail": "No reimbursement profile for this account. "
                    "Ask the treasurer to add your vendor ID."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        if not (user.email or "").strip():
            return Response(
                {"detail": "Your account has no email address; add one before submitting."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        req = ReimbursementRequest.objects.create(
            name=_display_name(user),
            position=_exec_position(user),
            email=user.email.strip(),
            m_number=data["m_number"].strip(),
            vendor_id=profile.vendor_id,
            date=data["date"],
            vendor_name=data["vendor_name"].strip(),
            amount=data["amount"],
            description=data["description"].strip(),
            budgeted=data["budgeted"],
            reimbursement_type=data["reimbursement_type"],
            itemized_receipt=data["itemized_receipt"],
            supporting_document=data.get("supporting_document"),
        )

        return Response(
            {
                "message": "Request created successfully",
                "id": req.id,
            },
            status=status.HTTP_201_CREATED,
        )
