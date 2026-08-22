from django.urls import path

from .views import (
    OrgFundingDateAllListView,
    OrgFundingDateDetailView,
    OrgFundingDateListCreateView,
    OrgFundingRequestCreateView,
    OrgFundingRequestDetailView,
    OrgFundingRequestListView,
)

urlpatterns = [
    path("", OrgFundingRequestCreateView.as_view(), name="org-funding-request-create"),
    path("requests/", OrgFundingRequestListView.as_view(), name="org-funding-request-list"),
    path(
        "requests/<int:pk>/",
        OrgFundingRequestDetailView.as_view(),
        name="org-funding-request-detail",
    ),
    path("dates/", OrgFundingDateListCreateView.as_view(), name="org-funding-date-list-create"),
    path("dates/all/", OrgFundingDateAllListView.as_view(), name="org-funding-date-all"),
    path("dates/<int:pk>/", OrgFundingDateDetailView.as_view(), name="org-funding-date-detail"),
]
