from django.urls import path

from .views import RepresentativeListCreateView

urlpatterns = [
    path(
        "representatives/",
        RepresentativeListCreateView.as_view(),
        name="career-fair-representatives",
    ),
]
