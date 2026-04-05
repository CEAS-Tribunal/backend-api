from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from rest_framework_simplejwt.views import TokenVerifyView

from dashboard.api.Auth.jwt_views import (
    StaffOnlyTokenObtainPairView,
    StaffOnlyTokenRefreshView,
)
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    # API Schema
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    path('admin/', admin.site.urls),
    path('dashboard/', include('dashboard.urls'), name='dashboard'),
    path('api/resume-review-day/', include('ResumeReviewDay.urls'), name='resume-review-day'),
    path('api/career-fair/', include('career_fair.urls'), name='career-fair'),

    # JWT Authentication endpoints (staff-only issuance; see StaffOnlyTokenObtainPairSerializer)
    path('api/token/', StaffOnlyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', StaffOnlyTokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]
