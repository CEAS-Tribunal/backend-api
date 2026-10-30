from rest_framework import serializers

from .models import JudgeModel, StudentModel, SubmissionModel


class JudgeSerializer(serializers.ModelSerializer):
    judging_category_display = serializers.SerializerMethodField()
    judging_timeslot_display = serializers.SerializerMethodField()
    lunch_preference_display = serializers.CharField(
        source="get_lunch_preference_display", read_only=True
    )

    class Meta:
        model = JudgeModel
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "employer_name",
            "judging_category",
            "judging_category_display",
            "judging_timeslot",
            "judging_timeslot_display",
            "number_of_projects",
            "is_backup_judge",
            "is_attending_lunch",
            "lunch_preference",
            "lunch_preference_display",
            "dietary_restrictions",
            "judge_pin",
            "has_checked_in",
        ]
        read_only_fields = ["id", "judge_pin", "has_checked_in"]

    def get_judging_category_display(self, obj):
        return list(obj.get_judging_category_list())

    def get_judging_timeslot_display(self, obj):
        return list(obj.get_judging_timeslot_list())


class JudgeCheckInPatchSerializer(serializers.Serializer):
    has_checked_in = serializers.BooleanField()


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentModel
        fields = ["id"]


class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubmissionModel
        fields = "__all__"
