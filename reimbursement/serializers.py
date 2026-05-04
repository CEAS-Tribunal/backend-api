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
    itemized_receipt = serializers.FileField()
    supporting_document = serializers.FileField(required=False, allow_null=True)


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
