from django.db import models
from cuid import cuid
from multiselectfield import MultiSelectField
from django.core.validators import MinValueValidator, MaxValueValidator
import secrets

ProjectCategories = [
    ("1", "Human-Centered Research and Design"),
    ("2", "Innovation, Creativity, and Entrepreneurship"),
    ("3", "Interdisciplinary Collaboration"),
    ("4", "Real-World Systems, Solutions, or Process Design"),
    ("5", "Student Organization Project"),
    ("6", "Sustainability and Environmental Responsibility"),
    ("7", "Technical Excellence"),
]

JudgingTimeslots = [
    ("1", "9:30 AM - 09:45 AM"),
    ("2", "09:50 AM - 10:05 AM"),
    ("3", "10:10 AM - 10:25 AM"),
    ("4", "10:30 AM - 10:45 AM"),
    ("5", "10:50 AM - 11:05 AM"),
    ("6", "11:10 AM - 11:25 AM"),
    ("7", "11:30 AM - 11:45 AM"),
    ("8", "11:50 AM - 12:05 PM"),
    ("9", "12:10 PM - 12:25 PM"),
    ("10", "12:30 PM - 12:45 PM"),
]

LunchPreferences = [
    ("1", "Chicken"),
    ("2", "Beef"),
    ("3", "Fish"),
    ("4", "Vegetarian"),
    ("5", "Vegan"),
]

def generate_judge_pin():
    return f"{secrets.randbelow(10_000):04d}"

class RangeField(models.IntegerField):
    """A reusable integer field restricted to an inclusive min-max range."""
    def __init__(self, *args, min_value=1, max_value=10, **kwargs):
        self.min_value = min_value
        self.max_value = max_value
        kwargs["validators"] = [MinValueValidator(min_value), MaxValueValidator(max_value)]
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs.pop("validators", None)
        kwargs["min_value"] = self.min_value
        kwargs["max_value"] = self.max_value
        return name, path, args, kwargs

class JudgeModel(models.Model):
    id = models.CharField(primary_key=True, default=cuid, editable=False, unique=True, db_index=True)
    first_name = models.CharField(max_length=255, null=False, blank=False)
    last_name = models.CharField(max_length=255, null=False, blank=False)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=255, null=False, blank=False)
    employer_name = models.CharField(max_length=255, null=False, blank=False)
    judging_category = MultiSelectField(choices=ProjectCategories, null=False, blank=False)
    judging_timeslot = MultiSelectField(choices=JudgingTimeslots, null=False, blank=False)
    number_of_projects = RangeField(null=False, blank=False)
    is_backup_judge = models.BooleanField(default=False, null=False, blank=False)
    is_attending_lunch = models.BooleanField(default=False, null=False, blank=False)
    lunch_preference = models.CharField(choices=LunchPreferences, max_length=255, null=True, blank=True)
    dietary_restrictions = models.CharField(max_length=255, null=True, blank=True)

    judge_pin = models.CharField(max_length=255, null=False, blank=False, editable=False)

    def save(self, *args, **kwargs):
        if not self.judge_pin:
            self.judge_pin = generate_judge_pin()
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
    question_1_score = RangeField(null=False, blank=False)
    question_2_score = RangeField(null=False, blank=False)
    question_3_score = RangeField(null=False, blank=False)
    question_4_score = RangeField(null=False, blank=False)
    question_5_score = RangeField(null=False, blank=False)
    question_6_score = RangeField(null=False, blank=False)
    question_7_score = RangeField(null=False, blank=False)
    question_8_score = RangeField(null=False, blank=False)
    question_9_score = RangeField(null=False, blank=False)
    question_10_score = RangeField(null=False, blank=False)
    total_score = RangeField(min_value=0, max_value=100, null=False, blank=False) # Range 0-100 for total score only

    class Meta:
        indexes = [
            models.Index(fields=['student', 'judge'], name='submission_student_judge_idx'),
        ]