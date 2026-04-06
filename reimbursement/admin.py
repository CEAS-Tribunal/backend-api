from django.contrib import admin

from .models import ReimbursementRequest, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "vendor_id")
    list_select_related = ("user",)
    search_fields = ("vendor_id", "user__username", "user__email")
    ordering = ("id",)
    raw_id_fields = ("user",)


@admin.register(ReimbursementRequest)
class ReimbursementRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "email",
        "vendor_id",
        "amount",
        "reimbursement_type",
        "created_at",
    )
    list_filter = ("reimbursement_type", "budgeted")
    search_fields = ("name", "email", "vendor_id", "m_number")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
