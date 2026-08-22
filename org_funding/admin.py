from django.contrib import admin

from .models import OrgFundingDate, OrgFundingRequest


@admin.register(OrgFundingDate)
class OrgFundingDateAdmin(admin.ModelAdmin):
    list_display = ("id", "date", "label", "is_open", "capacity", "created_at")
    list_filter = ("is_open",)
    search_fields = ("label", "notes")
    ordering = ("date", "id")
    readonly_fields = ("created_at", "updated_at")


@admin.register(OrgFundingRequest)
class OrgFundingRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "organization_name",
        "requester_name",
        "requester_email",
        "requested_amount",
        "status",
        "involves_travel",
        "created_at",
    )
    list_filter = ("status", "involves_travel")
    search_fields = (
        "organization_name",
        "requester_name",
        "requester_email",
        "m_number",
        "position",
    )
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("funding_date",)
