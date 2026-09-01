from django.urls import path, include
from . import views

urlpatterns = [
    path('employer/', views.EmployerViewSet.as_view(), name='employers'),
    path('student/', views.StudentViewSet.as_view(), name='students'),
    path('timeslots/', views.TimeslotViewSet.as_view(), name='timeslots'),
    path('roster/', views.AdminResumeRosterView.as_view(), name='admin-resume-roster'),
    path('resumes/download/', views.AdminResumeDownloadView.as_view(), name='admin-resume-download'),
    path('settings/', views.ResumeReviewSettingsView.as_view(), name='resume-review-settings'),
]

