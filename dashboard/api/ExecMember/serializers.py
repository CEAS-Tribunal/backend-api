from rest_framework import serializers
from django.contrib.auth.models import User
from dashboard.models import ExecMember


class ExecMemberSerializer(serializers.ModelSerializer):
    """Exposes id, name, email, imgURL for API; name and email come from the related User."""
    name = serializers.SerializerMethodField(read_only=True)
    email = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ExecMember
        fields = ['id', 'name', 'email', 'imgURL', 'user']
        read_only_fields = ['id', 'name', 'email']
        extra_kwargs = {'user': {'write_only': True}}

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.get_username()

    def get_email(self, obj):
        return getattr(obj.user, 'email', '') or ''

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.pop('user', None)
        return data