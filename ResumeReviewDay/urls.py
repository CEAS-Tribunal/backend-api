from django.urls import path, include
from . import views

urlpatterns = [
    path('employer/', views.EmployerViewSet.as_view(), name='employers'),
    path('student/', views.StudentViewSet.as_view(), name='students'),
    path('timeslots/', views.TimeslotViewSet.as_view(), name='timeslots'),

]

