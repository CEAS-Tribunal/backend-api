import re
from decimal import Decimal

from rest_framework import serializers

from .models import EsocDate, EsocRequest


def _upload_leaf_name(storage_name: str) -> str:
    if not storage_name:
        return "document"
    return storage_name.replace("\\", "/").rstrip("/").split("/")[-1] or "document"


# --- Dates -----------------------------------------------------------------


class EsocDateSerializer(serializers.ModelSerializer):
    requests_count = serializers.SerializerMethodField()

    class Meta:
        model = EsocDate
        fields = (
            "id",
            "date",
            "label",
            "notes",
            "capacity",
            "is_open",
            "requests_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "requests_count", "created_at", "updated_at")
        extra_kwargs = {
            "label": {"required": False, "allow_blank": True},
            "notes": {"required": False, "allow_blank": True},
            "capacity": {"required": False, "allow_null": True},
            "is_open": {"required": False},
        }

    def get_requests_count(self, obj) -> int:
        # Uses prefetched/annotated value when available, else counts related rows.
        count = getattr(obj, "requests_count_annotated", None)
        if count is not None:
            return count
        return obj.requests.count()


# --- Requests --------------------------------------------------------------


class EsocRequestCreateSerializer(serializers.Serializer):
    organization_name = serializers.CharField(max_length=255)
    requester_name = serializers.CharField(max_length=255)
    requester_email = serializers.EmailField(max_length=255)
    m_number = serializers.CharField(max_length=255)
    position = serializers.CharField(max_length=255)
    requested_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
        allow_null=True,
    )
    purpose = serializers.CharField(max_length=8000)
    involves_travel = serializers.BooleanField(required=False, default=False)
    funding_date = serializers.PrimaryKeyRelatedField(
        queryset=EsocDate.objects.all(),
        required=False,
        allow_null=True,
    )
    w9 = serializers.FileField()
    application = serializers.FileField()
    slides = serializers.FileField()
    travel_authorization = serializers.FileField(required=False, allow_null=True)

    def _parse_additional_clubs(self):
        data = self.initial_data
        keys = data.keys() if hasattr(data, "keys") else []
        club_indexes = sorted(
            {
                int(match.group(1))
                for key in keys
                if (match := re.fullmatch(r"additional_club_(\d+)_name", key))
            }
        )
        if club_indexes != list(range(len(club_indexes))):
            raise serializers.ValidationError(
                {"additional_contacts": "Club indexes must start at zero and be consecutive."}
            )

        cleaned = []
        for club_index in club_indexes:
            club_name = str(
                data.get(f"additional_club_{club_index}_name", "")
            ).strip()
            person_indexes = sorted(
                {
                    int(match.group(1))
                    for key in keys
                    if (
                        match := re.fullmatch(
                            rf"additional_club_{club_index}_person_(\d+)_name",
                            key,
                        )
                    )
                }
            )
            if not club_name or person_indexes != list(range(len(person_indexes))):
                raise serializers.ValidationError(
                    {"additional_contacts": "Each club needs a name and one or two people."}
                )
            if not 1 <= len(person_indexes) <= 2:
                raise serializers.ValidationError(
                    {"additional_contacts": "Each club needs a name and one or two people."}
                )

            people = []
            for person_index in person_indexes:
                prefix = f"additional_club_{club_index}_person_{person_index}_"
                person = {
                    field: str(data.get(f"{prefix}{field}", "")).strip()
                    for field in ("name", "email", "role")
                }
                if not all(person.values()):
                    raise serializers.ValidationError(
                        {
                            "additional_contacts": (
                                "Each club person needs a name, email, and role."
                            )
                        }
                    )
                try:
                    serializers.EmailField().run_validation(person["email"])
                except serializers.ValidationError:
                    raise serializers.ValidationError(
                        {"additional_contacts": "Each club person needs a valid email."}
                    )
                people.append(person)
            cleaned.append({"clubName": club_name, "people": people})
        return cleaned

    def validate(self, attrs):
        attrs["additional_clubs"] = self._parse_additional_clubs()
        if attrs.get("involves_travel") and not attrs.get("travel_authorization"):
            raise serializers.ValidationError(
                {
                    "detail": "A travel authorization is required when the request involves travel."
                }
            )
        return attrs


class EsocChecklistSerializer(serializers.Serializer):
    w9 = serializers.BooleanField(required=False)
    application = serializers.BooleanField(required=False)
    slides = serializers.BooleanField(required=False)
    travel_authorization = serializers.BooleanField(required=False)


class EsocRequestSerializer(serializers.ModelSerializer):
    """Full read serializer used for chair list + detail responses."""

    funding_date = serializers.SerializerMethodField()
    additional_contacts = serializers.SerializerMethodField()
    checklist = serializers.SerializerMethodField()
    w9_url = serializers.SerializerMethodField()
    w9_filename = serializers.SerializerMethodField()
    application_url = serializers.SerializerMethodField()
    application_filename = serializers.SerializerMethodField()
    slides_url = serializers.SerializerMethodField()
    slides_filename = serializers.SerializerMethodField()
    travel_authorization_url = serializers.SerializerMethodField()
    travel_authorization_filename = serializers.SerializerMethodField()

    class Meta:
        model = EsocRequest
        fields = (
            "id",
            "organization_name",
            "requester_name",
            "requester_email",
            "m_number",
            "position",
            "requested_amount",
            "purpose",
            "involves_travel",
            "status",
            "funding_date",
            "additional_contacts",
            "w9_url",
            "w9_filename",
            "application_url",
            "application_filename",
            "slides_url",
            "slides_filename",
            "travel_authorization_url",
            "travel_authorization_filename",
            "checklist",
            "chair_notes",
            "created_at",
            "updated_at",
        )

    def _abs_url(self, filefield):
        if not filefield:
            return None
        request = self.context.get("request")
        url = filefield.url
        return request.build_absolute_uri(url) if request else url

    def get_funding_date(self, obj):
        if not obj.funding_date:
            return None
        return obj.funding_date.date.isoformat()

    def get_additional_contacts(self, obj):
        return [
            {
                "clubName": club.name,
                "people": [
                    {
                        "name": contact.name,
                        "email": contact.email,
                        "role": contact.role,
                    }
                    for contact in club.contacts.all()
                ],
            }
            for club in obj.additional_clubs.all()
        ]

    def get_checklist(self, obj):
        return {
            "w9": obj.checklist_w9,
            "application": obj.checklist_application,
            "slides": obj.checklist_slides,
            "travel_authorization": obj.checklist_travel_authorization,
        }

    def get_w9_url(self, obj):
        return self._abs_url(obj.w9)

    def get_w9_filename(self, obj):
        return _upload_leaf_name(obj.w9.name) if obj.w9 else None

    def get_application_url(self, obj):
        return self._abs_url(obj.application)

    def get_application_filename(self, obj):
        return _upload_leaf_name(obj.application.name) if obj.application else None

    def get_slides_url(self, obj):
        return self._abs_url(obj.slides)

    def get_slides_filename(self, obj):
        return _upload_leaf_name(obj.slides.name) if obj.slides else None

    def get_travel_authorization_url(self, obj):
        return self._abs_url(obj.travel_authorization)

    def get_travel_authorization_filename(self, obj):
        return (
            _upload_leaf_name(obj.travel_authorization.name)
            if obj.travel_authorization
            else None
        )


class EsocRequestUpdateSerializer(serializers.Serializer):
    """Chair PATCH: status, checklist (partial), and/or notes."""

    status = serializers.ChoiceField(
        choices=EsocRequest.Status.choices, required=False
    )
    checklist = EsocChecklistSerializer(required=False)
    chair_notes = serializers.CharField(
        required=False, allow_blank=True, max_length=8000
    )

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                {"detail": "Provide at least one of status, checklist, or chair_notes."}
            )
        return attrs
