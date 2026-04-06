from django.contrib import admin
from .models import UserProfile, ReimbursementRequest

admin.site.register(UserProfile)
admin.site.register(ReimbursementRequest)