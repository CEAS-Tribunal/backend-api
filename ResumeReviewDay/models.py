from django.db import models
from django.core.validators import MaxValueValidator
import cuid

from multiselectfield import MultiSelectField
from phonenumber_field.modelfields import PhoneNumberField

MAJOR_CHOICES = (
    ('aero', 'Aerospace Engineering'),
    ('arch', 'Architechtual Engineering'),
    ('bmes', 'Biomedical Engineering'),
    ('chem', 'Chemical Engineering'),
    ('civil', 'Civil Engineering'),
    ('cs', 'Computer Science'),
    ('compe', 'Computer Engineering'),
    ('const', 'Construction Management'),
    ('cyber', 'Cybersecurity Engineering'),
    ('elec', 'Electrical Engineering'),
    ('elect', 'Electrical Engineering Technology'),
    ('ise', 'Industrial & Systems Engineering'),
    ('mech', 'Mechanical Engineering'),
    ('mecht', 'Mechanical Engineering Technology')
)


class ResumeReviewSettings(models.Model):
    """Singleton containing the public availability of each registration page."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    employer_page_open = models.BooleanField(default=True)
    student_page_open = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        self.id = 1
        super().save(*args, **kwargs)

    @classmethod
    def current(cls):
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings

class Employer(models.Model):
    id = models.CharField(primary_key=True, default=cuid.cuid, max_length=25)
    full_name = models.CharField(max_length=30, null=False)
    company_name = models.CharField(max_length=30, null=False)
    email = models.EmailField(null=False)
    phone_number = PhoneNumberField(blank=True, null=True)
    diet_restriction = models.CharField(max_length=None, blank=True, null=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    max_resumes = models.IntegerField(validators=[MaxValueValidator(100)]) 
    uc_alumni = models.BooleanField()
    selected_majors = MultiSelectField(choices=MAJOR_CHOICES, max_length=200)
    
    def __str__(self) -> str:
        return f"{self.full_name} - {self.company_name}"
    
class Student(models.Model):
    id = models.CharField(primary_key=True, default=cuid.cuid, max_length=25)
    full_name = models.CharField(max_length=30, null=False)
    email = models.EmailField(null=False)
    grad_year = models.IntegerField()
    major = models.CharField(max_length=30, choices=MAJOR_CHOICES)
    resume = models.FileField(upload_to='resumes/')
    
    def __str__(self) -> str:
        return f"{self.full_name} - {self.major}"

    def delete(self):
            self.timeslots.all().delete()
            self.resume.delete()
            super().delete()
   
class Timeslot(models.Model):
    id = models.CharField(primary_key=True, default=cuid.cuid, max_length=25)
    employer = models.ForeignKey(Employer, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.SET_NULL, blank=True, null=True)
    timeslot = models.TimeField()

    def __str__(self):
        return f"{self.employer.full_name} - {self.timeslot}"