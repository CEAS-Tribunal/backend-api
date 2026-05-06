from django.db.models import Q
import logging
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings

from dashboard.models import ExecMember
from dashboard.permissions import IsStaffUser, IsTreasurerOrSuperuserStaff

from .models import ReimbursementRequest, UserProfile
from .emailing import send_treasurer_reimbursement_request_created
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


logger = logging.getLogger(__name__)


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
        data = serializer.validated_data
        reimbursement_type = (data.get("reimbursement_type") or "").strip().lower()
        is_check = reimbursement_type == "check"

        profile = None
        if reimbursement_type != "check":
            # For direct deposit (and all non-check methods), vendor ID is required.
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
        else:
            # For check reimbursements, vendor ID is not required.
            try:
                profile = request.user.reimbursement_profile
            except UserProfile.DoesNotExist:
                profile = None

        user = request.user
        if not (user.email or "").strip():
            return Response(
                {"detail": "Your account has no email address; add one before submitting."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        req = ReimbursementRequest.objects.create(
            name=_display_name(user),
            position=_exec_position(user),
            email=user.email.strip(),
            m_number=data["m_number"].strip(),
            vendor_id=(profile.vendor_id if profile else ""),
            date=data["date"],
            vendor_name=data["vendor_name"].strip(),
            amount=data["amount"],
            description=data["description"].strip(),
            budgeted=data["budgeted"],
            reimbursement_type=data["reimbursement_type"],
            reimbursement_address_line1=(
                (data.get("reimbursement_address_line1") or "").strip() if is_check else ""
            ),
            reimbursement_address_line2=(
                (data.get("reimbursement_address_line2") or "").strip() if is_check else ""
            ),
            reimbursement_address_city=(
                (data.get("reimbursement_address_city") or "").strip() if is_check else ""
            ),
            reimbursement_address_state=(
                (data.get("reimbursement_address_state") or "").strip() if is_check else ""
            ),
            reimbursement_address_zip=(
                (data.get("reimbursement_address_zip") or "").strip() if is_check else ""
            ),
            non_budgeted_officer_name=(data.get("non_budgeted_officer_name") or "").strip(),
            non_budgeted_officer_position=(data.get("non_budgeted_officer_position") or "").strip(),
            ic_competition=data.get("ic_competition") is True,
            ic_participant_name=(data.get("ic_participant_name") or "").strip(),
            ic_participant_role=(data.get("ic_participant_role") or "").strip(),
            ic_participant_email=(data.get("ic_participant_email") or "").strip(),
            itemized_receipt=data["itemized_receipt"],
            supporting_document=data.get("supporting_document"),
        )

        # Notify Treasurer(s). Never block request creation on email delivery.
        try:
            send_treasurer_reimbursement_request_created(req, request=request)
        except Exception:
            logger.exception("Treasurer notification email failed", extra={"reimbursement_request_id": req.id})
            if settings.DEBUG:
                raise

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
