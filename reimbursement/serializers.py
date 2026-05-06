from decimal import Decimal

from rest_framework import serializers

from .models import ReimbursementRequest


class ReimbursementRequestCreateSerializer(serializers.Serializer):
    date = serializers.DateField()
    m_number = serializers.CharField(max_length=255)
    vendor_name = serializers.CharField(max_length=255)
    amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0.01")
    )
    description = serializers.CharField(max_length=4000)
    budgeted = serializers.BooleanField()
    reimbursement_type = serializers.CharField(max_length=255)
    reimbursement_address_line1 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    reimbursement_address_line2 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    reimbursement_address_city = serializers.CharField(max_length=255, required=False, allow_blank=True)
    reimbursement_address_state = serializers.CharField(max_length=255, required=False, allow_blank=True)
    reimbursement_address_zip = serializers.CharField(max_length=20, required=False, allow_blank=True)
    non_budgeted_officer_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    non_budgeted_officer_position = serializers.CharField(max_length=255, required=False, allow_blank=True)
    ic_competition = serializers.BooleanField(required=False, default=False)
    ic_participant_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    ic_participant_role = serializers.CharField(max_length=255, required=False, allow_blank=True)
    ic_participant_email = serializers.EmailField(max_length=255, required=False, allow_blank=True)
    itemized_receipt = serializers.FileField()
    supporting_document = serializers.FileField(required=False, allow_null=True)

    def validate(self, attrs):
        reimbursement_type = (attrs.get("reimbursement_type") or "").strip().lower()
        budgeted = attrs.get("budgeted")
        ic = attrs.get("ic_competition") is True

        # Address is required when reimbursed by check.
        if reimbursement_type == "check":
            required_addr = (
                "reimbursement_address_line1",
                "reimbursement_address_city",
                "reimbursement_address_state",
                "reimbursement_address_zip",
            )
            missing = [k for k in required_addr if not (attrs.get(k) or "").strip()]
            if missing:
                raise serializers.ValidationError(
                    {"detail": "Mailing address is required when reimbursement method is check."}
                )

        # Non-budgeted officer fields required when budgeted is false.
        if budgeted is False:
            if not (attrs.get("non_budgeted_officer_name") or "").strip():
                raise serializers.ValidationError(
                    {"detail": "Officer name is required when the expense is not budgeted."}
                )
            if not (attrs.get("non_budgeted_officer_position") or "").strip():
                raise serializers.ValidationError(
                    {"detail": "Officer position is required when the expense is not budgeted."}
                )

        # IC competition participant fields required when toggle is on.
        if ic:
            if not (attrs.get("ic_participant_name") or "").strip():
                raise serializers.ValidationError(
                    {"detail": "Participant name is required for IC competition reimbursements."}
                )
            if not (attrs.get("ic_participant_role") or "").strip():
                raise serializers.ValidationError(
                    {"detail": "Participant role is required for IC competition reimbursements."}
                )
            if not (attrs.get("ic_participant_email") or "").strip():
                raise serializers.ValidationError(
                    {"detail": "Participant email is required for IC competition reimbursements."}
                )

        return attrs


def _upload_leaf_name(storage_name: str) -> str:
    if not storage_name:
        return "document"
    return storage_name.replace("\\", "/").rstrip("/").split("/")[-1] or "document"


class ReimbursementRequestListSerializer(serializers.ModelSerializer):
    itemized_receipt_url = serializers.SerializerMethodField()
    supporting_document_url = serializers.SerializerMethodField()
    itemized_receipt_filename = serializers.SerializerMethodField()
    supporting_document_filename = serializers.SerializerMethodField()

    class Meta:
        model = ReimbursementRequest
        fields = (
            "id",
            "name",
            "position",
            "email",
            "m_number",
            "vendor_id",
            "date",
            "vendor_name",
            "amount",
            "description",
            "budgeted",
            "reimbursement_type",
            "reimbursement_address_line1",
            "reimbursement_address_line2",
            "reimbursement_address_city",
            "reimbursement_address_state",
            "reimbursement_address_zip",
            "non_budgeted_officer_name",
            "non_budgeted_officer_position",
            "ic_competition",
            "ic_participant_name",
            "ic_participant_role",
            "ic_participant_email",
            "itemized_receipt_url",
            "itemized_receipt_filename",
            "supporting_document_url",
            "supporting_document_filename",
            "filed",
            "created_at",
            "updated_at",
        )

    def get_itemized_receipt_url(self, obj):
        if not obj.itemized_receipt:
            return None
        request = self.context.get("request")
        url = obj.itemized_receipt.url
        if request:
            return request.build_absolute_uri(url)
        return url

    def get_supporting_document_url(self, obj):
        if not obj.supporting_document:
            return None
        request = self.context.get("request")
        url = obj.supporting_document.url
        if request:
            return request.build_absolute_uri(url)
        return url

    def get_itemized_receipt_filename(self, obj):
        if not obj.itemized_receipt:
            return None
        return _upload_leaf_name(obj.itemized_receipt.name)

    def get_supporting_document_filename(self, obj):
        if not obj.supporting_document:
            return None
        return _upload_leaf_name(obj.supporting_document.name)


class ReimbursementRequestFiledPatchSerializer(serializers.Serializer):
    filed = serializers.BooleanField()
