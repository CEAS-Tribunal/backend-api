from django.urls import path

from .views import RepresentativeListCreateView, RepresentativePrintedUpdateView

urlpatterns = [
    path(
        "representatives/",
        RepresentativeListCreateView.as_view(),
        name="career-fair-representatives",
    ),
    path(
        "representatives/<str:pk>/printed/",
        RepresentativePrintedUpdateView.as_view(),
        name="career-fair-representative-printed",
    ),
]