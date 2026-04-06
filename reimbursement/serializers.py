from decimal import Decimal

from rest_framework import serializers


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
