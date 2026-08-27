from django.contrib import admin
from . import models

admin.site.register(models.Employer)
admin.site.register(models.Student)
admin.site.register(models.Timeslot)
admin.site.register(models.ResumeReviewSettings)