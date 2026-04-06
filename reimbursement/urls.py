from django.urls import path

from .views import ReimbursementRequestCreateView

urlpatterns = [
    path("", ReimbursementRequestCreateView.as_view(), name="reimbursement-request-create"),
]
