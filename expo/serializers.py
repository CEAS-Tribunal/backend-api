from rest_framework import serializers

from rest_framework.validators import UniqueValidator

from .assignment import DEFAULT_MIN_JUDGES
from .models import (
    JudgeAssignmentModel,
    JudgeModel,
    JudgingTimeslots,
    ProjectCategories,
    StudentModel,
    SubmissionModel,
)


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


class JudgeRegistrationSerializer(serializers.ModelSerializer):
    """Public judge sign-up. Excludes staff-only fields such as the PIN and check-in status."""

    email = serializers.EmailField(
        validators=[
            UniqueValidator(
                queryset=JudgeModel.objects.all(),
                lookup="iexact",
                message="A judge with this email is already registered.",
            )
        ]
    )
    # ListField (not MultipleChoiceField) so 1st/2nd/3rd preference order is preserved.
    judging_category = serializers.ListField(
        child=serializers.ChoiceField(choices=ProjectCategories),
        min_length=3,
        max_length=3,
        allow_empty=False,
    )
    judging_timeslot = serializers.MultipleChoiceField(choices=JudgingTimeslots, allow_empty=False)

    class Meta:
        model = JudgeModel
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "employer_name",
            "judging_category",
            "judging_timeslot",
            "number_of_projects",
            "is_backup_judge",
            "is_attending_lunch",
            "lunch_preference",
            "dietary_restrictions",
        ]

    def validate_email(self, value):
        return value.strip().lower()

    def validate_judging_category(self, value):
        # Preference order is significant: index 0 = 1st, 1 = 2nd, 2 = 3rd.
        if len(value) != 3:
            raise serializers.ValidationError(
                "Choose exactly three ranked categories (1st, 2nd, and 3rd)."
            )
        if len(set(value)) != 3:
            raise serializers.ValidationError(
                "Each ranked category must be different."
            )
        return list(value)

    def validate_judging_timeslot(self, value):
        return sorted(value, key=int)

    def validate(self, attrs):
        if attrs.get("is_attending_lunch"):
            if not attrs.get("lunch_preference"):
                raise serializers.ValidationError(
                    {"lunch_preference": "Choose a lunch option if you are attending lunch."}
                )
        else:
            attrs["lunch_preference"] = None
        return attrs


class JudgeCheckInPatchSerializer(serializers.Serializer):
    has_checked_in = serializers.BooleanField()


class StudentSerializer(serializers.ModelSerializer):
    team_category_display = serializers.CharField(
        source="get_team_category_display", read_only=True
    )

    class Meta:
        model = StudentModel
        fields = ["id", "team_name", "team_category", "team_category_display", "booth_number"]


class JudgeAssignmentSerializer(serializers.ModelSerializer):
    judge_name = serializers.SerializerMethodField()
    team_name = serializers.CharField(source="student.team_name", read_only=True)
    booth_number = serializers.CharField(source="student.booth_number", read_only=True)
    team_category = serializers.CharField(source="student.team_category", read_only=True)
    timeslot_display = serializers.CharField(source="get_timeslot_display", read_only=True)
    is_backup_judge = serializers.BooleanField(source="judge.is_backup_judge", read_only=True)

    class Meta:
        model = JudgeAssignmentModel
        fields = [
            "id",
            "judge",
            "judge_name",
            "is_backup_judge",
            "student",
            "team_name",
            "booth_number",
            "team_category",
            "timeslot",
            "timeslot_display",
        ]
        read_only_fields = ["id"]

    def get_judge_name(self, obj):
        return f"{obj.judge.first_name} {obj.judge.last_name}"

    def validate(self, attrs):
        judge = attrs.get("judge", getattr(self.instance, "judge", None))
        student = attrs.get("student", getattr(self.instance, "student", None))
        timeslot = attrs.get("timeslot", getattr(self.instance, "timeslot", None))
        others = JudgeAssignmentModel.objects.all()
        if self.instance is not None:
            others = others.exclude(pk=self.instance.pk)
        if others.filter(judge=judge, timeslot=timeslot).exists():
            raise serializers.ValidationError("This judge is already assigned in that timeslot.")
        if others.filter(student=student, timeslot=timeslot).exists():
            raise serializers.ValidationError("This team already has a judge in that timeslot.")
        if others.filter(judge=judge, student=student).exists():
            raise serializers.ValidationError("This judge is already assigned to this team.")
        return attrs


class GenerateAssignmentsSerializer(serializers.Serializer):
    min_judges = serializers.IntegerField(min_value=1, max_value=10, default=DEFAULT_MIN_JUDGES)
    max_judges = serializers.IntegerField(min_value=1, max_value=10, required=False, allow_null=True)

    def validate(self, attrs):
        max_judges = attrs.get("max_judges")
        if max_judges is not None and max_judges < attrs["min_judges"]:
            raise serializers.ValidationError("max_judges must be at least min_judges.")
        return attrs


class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubmissionModel
        fields = "__all__"
