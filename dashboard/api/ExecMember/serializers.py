from rest_framework import serializers
from dashboard.models import ExecMember

class ExecMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExecMember
        fields = '__all__'
        read_only_fields = ['id']