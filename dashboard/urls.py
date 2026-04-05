from django.urls import path

from .api.Auth import views as auth
from .api.ExecMember import views as member
from .api.ExecRole import views as role

urlpatterns = [
    path("auth/me/", auth.AuthMeView.as_view(), name="dashboard-auth-me"),
    path(
        "auth/change-password/",
        auth.ChangePasswordView.as_view(),
        name="dashboard-auth-change-password",
    ),
    path('exec-member/', member.ExecMemberView.as_view(), name='exec-member'),
    path('exec-role/', role.ExecRoleView.as_view(), name='exec-role'),
]
