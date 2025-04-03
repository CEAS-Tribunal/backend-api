from django.urls import path
from .api.ExecMember import views as member
from .api.ExecRole import views as role

urlpatterns = [
    path('exec-member/', member.ExecMemberView.as_view(), name='exec-member'),
    path('exec-role/', role.ExecRoleView.as_view(), name='exec-role'),
]
