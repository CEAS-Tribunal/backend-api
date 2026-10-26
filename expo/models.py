from django.db import models
from cuid import cuid
from multiselectfield import MultiSelectField
import secrets

ProjectCategories = [
    (1, "Human-Centered Research and Design"),
    (2, "Innovation, Creativity, and Entrepreneurship"),
    (3, "Interdisciplinary Collaboration"),
    (4, "Real-World Systems, Solutions, or Process Design"),
    (5, "Student Organization Project"),
    (6, "Sustainability and Environmental Responsibility"),
    (7, "Technical Excellence"),
]

JudgingTimeslots = [
    (1, "9:30 AM - 09:45 AM"),
    (2, "09:50 AM - 10:05 AM"),
    (3, "10:10 AM - 10:25 AM"),
    (4, "10:30 AM - 10:45 AM"),
    (5, "10:50 AM - 11:05 AM"),
    (6, "11:10 AM - 11:25 AM"),
    (7, "11:30 AM - 11:45 AM"),
    (8, "11:50 AM - 12:05 PM"),
    (9, "12:10 PM - 12:25 PM"),
    (10, "12:30 PM - 12:45 PM"),
]

LunchPreferences = [
    "Chicken",
    "Beef",
    "Fish",
    "Vegetarian",
    "Vegan",
]

ScoreRange = (1,10)

TotalScoreRange = (1, 100)

def generate_judge_pin():
    return f"{secrets.randbelow(10_000):04d}"

class JudgeModel(models.Model):
    id = models.CharField(primary_key=True, default=cuid, editable=False, unique=True, db_index=True)
    first_name = models.CharField(max_length=255, null=False, blank=False)
    last_name = models.CharField(max_length=255, null=False, blank=False)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=255, null=False, blank=False)
    employer_name = models.CharField(max_length=255, null=False, blank=False)
    judging_category = MultiSelectField(choices=ProjectCategories, null=False, blank=False)
    judging_timeslot = MultiSelectField(choices=JudgingTimeslots, null=False, blank=False)
    number_of_projects = models.IntegerField(null=False, blank=False, range=(1, 10))
    is_backup_judge = models.BooleanField(default=False, null=False, blank=False)
    is_attending_lunch = models.BooleanField(default=False, null=False, blank=False)
    lunch_preference = models.CharField(choices=LunchPreferences, max_length=255, null=True, blank=True)
    dietary_restrictions = models.CharField(max_length=255, null=True, blank=True)

    judge_pin = models.CharField(max_length=255, null=False, blank=False)

    def save(self, *args, **kwargs):
        if not self.pin:
            self.pin = generate_judge_pin()
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['first_name', 'last_name'], name='judge_name_idx'),
        ]

    def __str__(self):
        return self.first_name + " " + self.last_name

class StudentModel(models.Model):
    id = models.CharField(primary_key=True, default=cuid, editable=False, unique=True, db_index=True)

class SubmissionModel(models.Model):
    id = models.CharField(primary_key=True, default=cuid, editable=False, unique=True, db_index=True)
    student = models.ForeignKey(StudentModel, on_delete=models.CASCADE, null=False, blank=False)
    judge = models.ForeignKey(JudgeModel, on_delete=models.CASCADE, null=False, blank=False)
    project_category = models.CharField(choices=ProjectCategories, max_length=255, null=False, blank=False)
    question_1_score = models.IntegerField(null=False, blank=False, range=ScoreRange)
    question_2_score = models.IntegerField(null=False, blank=False, range=ScoreRange)
    question_3_score = models.IntegerField(null=False, blank=False, range=ScoreRange)
    question_4_score = models.IntegerField(null=False, blank=False, range=ScoreRange)
    question_5_score = models.IntegerField(null=False, blank=False, range=ScoreRange)
    question_6_score = models.IntegerField(null=False, blank=False, range=ScoreRange)
    question_7_score = models.IntegerField(null=False, blank=False, range=ScoreRange)
    question_8_score = models.IntegerField(null=False, blank=False, range=ScoreRange)
    question_9_score = models.IntegerField(null=False, blank=False, range=ScoreRange)
    question_10_score = models.IntegerField(null=False, blank=False, range=ScoreRange)
    total_score = models.IntegerField(null=False, blank=False, range=TotalScoreRange)

    class Meta:
        indexes = [
            models.Index(fields=['student', 'judge'], name='submission_student_judge_idx'),
        ]