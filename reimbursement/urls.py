from django.urls import path

from .views import (
    ReimbursementRequestCreateView,
    ReimbursementRequestFiledUpdateView,
    ReimbursementRequestListView,
)

urlpatterns = [
    path("", ReimbursementRequestCreateView.as_view(), name="reimbursement-request-create"),
    path("requests/", ReimbursementRequestListView.as_view(), name="reimbursement-request-list"),
    path(
        "requests/<int:pk>/filed/",
        ReimbursementRequestFiledUpdateView.as_view(),
        name="reimbursement-request-filed",
    ),
]
