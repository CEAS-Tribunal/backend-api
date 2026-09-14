from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import AlumniProfile


@admin.register(AlumniProfile)
class AlumniProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "graduation_year",
        "role_company",
    )