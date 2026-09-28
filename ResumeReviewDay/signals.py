from django.db.models.signals import post_save,post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Employer

@receiver([post_save, post_delete], sender=Employer)
def clear_resume_roster_and_employer_list_cache(sender, instance, created, **kwargs):
        cache.delete_pattern('*.admin_resume_roster.*')
        cache.delete_pattern("*.employer_list.*") 