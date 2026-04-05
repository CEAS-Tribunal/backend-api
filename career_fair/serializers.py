from rest_framework import serializers

from .models import Representative


class RepresentativeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Representative
        fields = [
            "id",
            "name",
            "company",
            "title",
            "email",
            "booth_location",
            "building_location",
            "signed_in_at",
        ]
        read_only_fields = ["id", "signed_in_at"]
