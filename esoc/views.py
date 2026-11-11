import logging

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from dashboard.permissions import IsEsocChairOrSuperuserStaff

from .emailing import send_esoc_request_created
from .models import EsocClub, EsocContact, EsocDate, EsocRequest
from .serializers import (
    EsocDateSerializer,
    EsocRequestCreateSerializer,
    EsocRequestSerializer,
    EsocRequestUpdateSerializer,
)

logger = logging.getLogger(__name__)


# --- Requests --------------------------------------------------------------


class EsocRequestCreateView(APIView):
    """Public: an organization submits a funding request with its documents."""

    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = EsocRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            req = EsocRequest.objects.create(
                organization_name=data["organization_name"].strip(),
                requester_name=data["requester_name"].strip(),
                requester_email=data["requester_email"].strip(),
                m_number=data["m_number"].strip(),
                position=data["position"].strip(),
                requested_amount=data.get("requested_amount"),
                purpose=data["purpose"].strip(),
                involves_travel=data.get("involves_travel") is True,
                funding_date=data.get("funding_date"),
                w9=data["w9"],
                application=data["application"],
                slides=data["slides"],
                travel_authorization=data.get("travel_authorization"),
            )
            for club_position, club_data in enumerate(data["additional_clubs"]):
                club = EsocClub.objects.create(
                    request=req,
                    name=club_data["clubName"],
                    position=club_position,
                )
                EsocContact.objects.bulk_create(
                    [
                        EsocContact(
                            club=club,
                            name=person["name"],
                            email=person["email"],
                            role=person["role"],
                            position=person_position,
                        )
                        for person_position, person in enumerate(club_data["people"])
                    ]
                )

        # Notify the chair (and any configured recipients). Never block on email delivery.
        try:
            send_esoc_request_created(req, request=request)
        except Exception:
            logger.exception(
                "ESOC notification email failed",
                extra={"esoc_request_id": req.id},
            )
            if settings.DEBUG:
                raise

        return Response(
            {"message": "Request submitted successfully", "id": req.id},
            status=status.HTTP_201_CREATED,
        )


class EsocRequestListView(APIView):
    """Chair/superuser: list funding requests with optional search + status filters."""

    permission_classes = [IsEsocChairOrSuperuserStaff]

    def get(self, request):
        qs = EsocRequest.objects.select_related("funding_date").prefetch_related(
            "additional_clubs__contacts"
        ).all()

        status_raw = (request.query_params.get("status") or "").strip()
        valid = {c for c, _ in EsocRequest.Status.choices}
        if status_raw in valid:
            qs = qs.filter(status=status_raw)

        search = (request.query_params.get("search") or "").strip()
        if search:
            qs = qs.filter(
                Q(organization_name__icontains=search)
                | Q(requester_name__icontains=search)
                | Q(requester_email__icontains=search)
                | Q(m_number__icontains=search)
                | Q(position__icontains=search)
                | Q(purpose__icontains=search)
            )

        data = EsocRequestSerializer(
            qs, many=True, context={"request": request}
        ).data
        return Response(data, status=status.HTTP_200_OK)


class EsocRequestDetailView(APIView):
    """Chair/superuser: retrieve a request or update its status/checklist/notes."""

    permission_classes = [IsEsocChairOrSuperuserStaff]
    parser_classes = [JSONParser]

    def _get_object(self, pk):
        return (
            EsocRequest.objects.select_related("funding_date")
            .prefetch_related("additional_clubs__contacts")
            .filter(pk=pk)
            .first()
        )

    def get(self, request, pk):
        req = self._get_object(pk)
        if req is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        data = EsocRequestSerializer(req, context={"request": request}).data
        return Response(data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        req = self._get_object(pk)
        if req is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = EsocRequestUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        update_fields = []
        if "status" in validated:
            req.status = validated["status"]
            update_fields.append("status")

        if "chair_notes" in validated:
            req.chair_notes = (validated["chair_notes"] or "").strip()
            update_fields.append("chair_notes")

        checklist = validated.get("checklist") or {}
        field_map = {
            "w9": "checklist_w9",
            "application": "checklist_application",
            "slides": "checklist_slides",
            "travel_authorization": "checklist_travel_authorization",
        }
        for key, model_field in field_map.items():
            if key in checklist:
                setattr(req, model_field, checklist[key])
                update_fields.append(model_field)

        if update_fields:
            update_fields.append("updated_at")
            req.save(update_fields=update_fields)

        data = EsocRequestSerializer(req, context={"request": request}).data
        return Response(data, status=status.HTTP_200_OK)


# --- Dates -----------------------------------------------------------------


class EsocDateListCreateView(APIView):
    """
    GET (public): list open dates for the submission form.
    POST (chair/superuser): create a new date.
    """

    parser_classes = [JSONParser]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsEsocChairOrSuperuserStaff()]
        return [AllowAny()]

    def get(self, request):
        qs = (
            EsocDate.objects.filter(is_open=True)
            .annotate(requests_count_annotated=Count("requests"))
            .order_by("date", "id")
        )
        data = EsocDateSerializer(qs, many=True, context={"request": request}).data
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = EsocDateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EsocDateAllListView(APIView):
    """Chair/superuser: list all dates (open and closed)."""

    permission_classes = [IsEsocChairOrSuperuserStaff]

    def get(self, request):
        qs = EsocDate.objects.annotate(
            requests_count_annotated=Count("requests")
        ).order_by("date", "id")
        data = EsocDateSerializer(qs, many=True, context={"request": request}).data
        return Response(data, status=status.HTTP_200_OK)


class EsocDateDetailView(APIView):
    """Chair/superuser: update or delete an available date."""

    permission_classes = [IsEsocChairOrSuperuserStaff]
    parser_classes = [JSONParser]

    def _get_object(self, pk):
        return EsocDate.objects.filter(pk=pk).first()

    def patch(self, request, pk):
        obj = self._get_object(pk)
        if obj is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = EsocDateSerializer(
            obj, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        obj = self._get_object(pk)
        if obj is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
