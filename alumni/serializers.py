from rest_framework import serializers

from .models import AlumniProfile


class AlumniProfileSerializer(serializers.ModelSerializer):
    graduationYear = serializers.IntegerField(source="graduation_year")
    roleCompany = serializers.CharField(source="role_company")
    imageURL = serializers.CharField(source="image_url", allow_null=True, allow_blank=True)

    class Meta:
        model = AlumniProfile
        fields = [
            "id",
            "name",
            "graduationYear",
            "roleCompany",
            "quote",
            "imageURL",
        ]