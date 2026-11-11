from django.urls import path

from .views import (
    JudgeDetailView,
    JudgeListCreateView,
    ResultsListView,
    RoomListView,
    SubmissionDetailView,
    SubmissionListCreateView,
    TeamDetailView,
    TeamListCreateView,
)

urlpatterns = [
    path("rooms/", RoomListView.as_view(), name="innovation-rooms"),
    path("judges/", JudgeListCreateView.as_view(), name="innovation-judges"),
    path("judges/<int:pk>/", JudgeDetailView.as_view(), name="innovation-judge-detail"),
    path("teams/", TeamListCreateView.as_view(), name="innovation-teams"),
    path("teams/<int:pk>/", TeamDetailView.as_view(), name="innovation-team-detail"),
    path(
        "submissions/",
        SubmissionListCreateView.as_view(),
        name="innovation-submissions",
    ),
    path(
        "submissions/<int:pk>/",
        SubmissionDetailView.as_view(),
        name="innovation-submission-detail",
    ),
    path("results/", ResultsListView.as_view(), name="innovation-results"),
]
