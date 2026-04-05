from django.contrib import admin

from .models import Representative


@admin.register(Representative)
class RepresentativeAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "email", "booth_location", "building_location", "signed_in_at")
    list_filter = ("building_location",)
    search_fields = ("name", "company", "email")
    readonly_fields = ("id", "signed_in_at")
