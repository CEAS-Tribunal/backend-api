from django.contrib import admin

from .models import EsocClub, EsocContact, EsocDate, EsocRequest


@admin.register(EsocDate)
class EsocDateAdmin(admin.ModelAdmin):
    list_display = ("id", "date", "label", "is_open", "capacity", "created_at")
    list_filter = ("is_open",)
    search_fields = ("label", "notes")
    ordering = ("date", "id")
    readonly_fields = ("created_at", "updated_at")


@admin.register(EsocRequest)
class EsocRequestAdmin(admin.ModelAdmin):
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


@admin.register(EsocClub)
class EsocClubAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "request", "position")
    search_fields = ("name",)
    raw_id_fields = ("request",)


@admin.register(EsocContact)
class EsocContactAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "role", "club", "position")
    search_fields = ("name", "email", "role")
    raw_id_fields = ("club",)
