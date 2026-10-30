from django.contrib import admin
from .models import JudgeModel, StudentModel, SubmissionModel


@admin.register(JudgeModel)
class JudgeModelAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "email", "judge_pin")
    readonly_fields = ("judge_pin",)


admin.site.register(StudentModel)
admin.site.register(SubmissionModel)
