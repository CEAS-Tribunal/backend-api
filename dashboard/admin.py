from django.contrib import admin

from . import models


@admin.register(models.ExecMember)
class ExecMemberAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "must_change_password", "imgURL")
    list_filter = ("must_change_password",)
    search_fields = ("user__username", "user__email", "id")


admin.site.register(models.ExecRole)