from django.urls import path

from .views import (
    EsocDateAllListView,
    EsocDateDetailView,
    EsocDateListCreateView,
    EsocRequestCreateView,
    EsocRequestDetailView,
    EsocRequestListView,
)

urlpatterns = [
    path("", EsocRequestCreateView.as_view(), name="esoc-request-create"),
    path("requests/", EsocRequestListView.as_view(), name="esoc-request-list"),
    path(
        "requests/<int:pk>/",
        EsocRequestDetailView.as_view(),
        name="esoc-request-detail",
    ),
    path("dates/", EsocDateListCreateView.as_view(), name="esoc-date-list-create"),
    path("dates/all/", EsocDateAllListView.as_view(), name="esoc-date-all"),
    path("dates/<int:pk>/", EsocDateDetailView.as_view(), name="esoc-date-detail"),
]
