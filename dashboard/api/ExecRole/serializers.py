from rest_framework import serializers
from dashboard.models import ExecRole

class ExecRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExecRole
        fields = '__all__'
        read_only_fields = ['id']