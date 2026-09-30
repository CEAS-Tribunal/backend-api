from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .cache import invalidate_resume_review_data, invalidate_resume_review_settings
from .models import Employer, ResumeReviewSettings, Student, Timeslot


@receiver([post_save, post_delete], sender=Employer)
@receiver([post_save, post_delete], sender=Student)
@receiver([post_save, post_delete], sender=Timeslot)
def clear_resume_review_data_cache(sender, **kwargs):
    invalidate_resume_review_data()


@receiver([post_save, post_delete], sender=ResumeReviewSettings)
def clear_resume_review_settings_cache(sender, **kwargs):
    invalidate_resume_review_settings()
