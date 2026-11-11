from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower


class InnovationRoom(models.TextChoices):
    FRONT_OF_KAUTZ_ATTIC = "Front of Kautz Attic", "Front of Kautz Attic"
    BACK_OF_KAUTZ_ATTIC = "Back of Kautz Attic", "Back of Kautz Attic"
    LINDNER_4210 = "Lindner 4210", "Lindner 4210"


class Judge(models.Model):
    name = models.CharField(max_length=120)
    room = models.CharField(max_length=120, choices=InnovationRoom.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = [Lower("name")]
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                condition=Q(is_active=True),
                name="innovation_active_judge_name_ci_unique",
            ),
        ]

    def __str__(self):
        return self.name


class Team(models.Model):
    name = models.CharField(max_length=160)
    room = models.CharField(max_length=120, choices=InnovationRoom.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = [Lower("name")]
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                condition=Q(is_active=True),
                name="innovation_active_team_name_ci_unique",
            ),
        ]

    def __str__(self):
        return self.name


class JudgingSubmission(models.Model):
    judge = models.ForeignKey(
        Judge,
        on_delete=models.PROTECT,
        related_name="submissions",
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        related_name="submissions",
    )
    scores = models.JSONField()
    feedback = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["judge", "team"],
                name="innovation_unique_judge_team_submission",
            ),
        ]

    def __str__(self):
        return f"{self.judge} - {self.team}"
