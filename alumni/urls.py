from django.urls import path
from .views import AlumniProfileListView

urlpatterns = [
    path("", AlumniProfileListView.as_view(), name="alumni-list"),
]