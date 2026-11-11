from rest_framework import serializers

from .models import InnovationRoom, Judge, JudgingSubmission, Team


class InnovationRoomField(serializers.ChoiceField):
    def to_internal_value(self, data):
        if isinstance(data, str):
            data = data.strip()
        return super().to_internal_value(data)


class JudgeSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=120, trim_whitespace=True)
    room = InnovationRoomField(choices=InnovationRoom.choices)

    class Meta:
        model = Judge
        fields = ["id", "name", "room", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "is_active", "created_at", "updated_at"]

    def validate_name(self, value):
        duplicates = Judge.objects.filter(name__iexact=value, is_active=True)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("A judge with this name already exists.")
        return value


class TeamSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=160, trim_whitespace=True)
    room = InnovationRoomField(choices=InnovationRoom.choices)

    class Meta:
        model = Team
        fields = ["id", "name", "room", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "is_active", "created_at", "updated_at"]

    def validate_name(self, value):
        duplicates = Team.objects.filter(name__iexact=value, is_active=True)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("A team with this name already exists.")
        return value


RUBRIC_CRITERIA = (
    "presentation-quality",
    "business-model-clarity",
    "value-proposition",
    "competitive-analysis",
    "market-analysis",
    "product-prototype-understanding",
    "growth",
    "qa-effectiveness",
    "overall-rating",
)


class JudgingSubmissionSerializer(serializers.ModelSerializer):
    judge_id = serializers.PrimaryKeyRelatedField(
        source="judge",
        queryset=Judge.objects.filter(is_active=True),
        required=False,
    )
    team_id = serializers.PrimaryKeyRelatedField(
        source="team",
        queryset=Team.objects.filter(is_active=True),
        required=False,
    )
    judge_name = serializers.CharField(source="judge.name", read_only=True)
    team_name = serializers.CharField(source="team.name", read_only=True)
    room = serializers.CharField(source="team.room", read_only=True)

    class Meta:
        model = JudgingSubmission
        fields = [
            "id",
            "judge_id",
            "judge_name",
            "team_id",
            "team_name",
            "room",
            "scores",
            "feedback",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "scores": {"required": True},
            "feedback": {"required": False, "allow_blank": True},
        }

    def validate_scores(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Scores must be an object.")

        received = set(value)
        required = set(RUBRIC_CRITERIA)
        errors = {}
        missing = sorted(required - received)
        unknown = sorted(received - required)
        if missing:
            errors["missing"] = [f"Missing required criteria: {', '.join(missing)}."]
        if unknown:
            errors["unknown"] = [f"Unknown criteria: {', '.join(unknown)}."]
        for criterion in sorted(required & received):
            score = value[criterion]
            if isinstance(score, bool) or not isinstance(score, int) or not 1 <= score <= 10:
                errors[criterion] = ["Score must be an integer from 1 through 10."]
        if errors:
            raise serializers.ValidationError(errors)
        return value

    def validate(self, attrs):
        if not self.instance:
            if "judge" not in attrs:
                raise serializers.ValidationError({"judge_id": ["This field is required."]})
            if "team" not in attrs:
                raise serializers.ValidationError({"team_id": ["This field is required."]})

        if self.instance:
            judge = attrs.get("judge", self.instance.judge)
            team = attrs.get("team", self.instance.team)
            if "judge" not in attrs and not judge.is_active:
                raise serializers.ValidationError(
                    {"judge_id": ["Submissions for inactive judges cannot be updated."]}
                )
            if "team" not in attrs and not team.is_active:
                raise serializers.ValidationError(
                    {"team_id": ["Submissions for inactive teams cannot be updated."]}
                )

        return attrs
