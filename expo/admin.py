from django.contrib import admin
from .models import JudgeAssignmentModel, JudgeModel, StudentModel, SubmissionModel


@admin.register(JudgeModel)
class JudgeModelAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "email", "judge_pin")
    readonly_fields = ("judge_pin",)


@admin.register(JudgeAssignmentModel)
class JudgeAssignmentModelAdmin(admin.ModelAdmin):
    list_display = ("judge", "student", "timeslot")
    list_filter = ("timeslot",)


admin.site.register(StudentModel)
admin.site.register(SubmissionModel)
