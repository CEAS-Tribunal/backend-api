from django.db.models import Q
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from dashboard.models import ExecMember
from dashboard.permissions import IsStaffUser, IsTreasurerOrSuperuserStaff

from .models import ReimbursementRequest, UserProfile
from .serializers import (
    ReimbursementRequestCreateSerializer,
    ReimbursementRequestFiledPatchSerializer,
    ReimbursementRequestListSerializer,
)


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


class ReimbursementRequestListView(APIView):
    """
    Staff-only: list reimbursement requests with optional filters.
    """

    permission_classes = [IsStaffUser]

    def get(self, request):
        qs = ReimbursementRequest.objects.all().order_by("-created_at", "-id")

        filed_raw = request.query_params.get("filed")
        if filed_raw is not None:
            s = filed_raw.strip().lower()
            if s in ("1", "true", "yes"):
                qs = qs.filter(filed=True)
            elif s in ("0", "false", "no"):
                qs = qs.filter(filed=False)

        reimbursement_type = (request.query_params.get("reimbursement_type") or "").strip()
        if reimbursement_type:
            qs = qs.filter(reimbursement_type__icontains=reimbursement_type)

        search = (request.query_params.get("search") or "").strip()
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(email__icontains=search)
                | Q(vendor_name__icontains=search)
                | Q(m_number__icontains=search)
                | Q(vendor_id__icontains=search)
                | Q(description__icontains=search)
            )

        data = ReimbursementRequestListSerializer(
            qs,
            many=True,
            context={"request": request},
        ).data
        return Response(data, status=status.HTTP_200_OK)


class ReimbursementRequestFiledUpdateView(APIView):
    """
    Treasurer or superuser: set whether a reimbursement has been filed.
    """

    permission_classes = [IsTreasurerOrSuperuserStaff]
    parser_classes = [JSONParser]

    def patch(self, request, pk):
        try:
            req = ReimbursementRequest.objects.get(pk=pk)
        except ReimbursementRequest.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = ReimbursementRequestFiledPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req.filed = serializer.validated_data["filed"]
        req.save(update_fields=["filed", "updated_at"])

        out = ReimbursementRequestListSerializer(req, context={"request": request}).data
        return Response(out, status=status.HTTP_200_OK)
