import re

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path, re_path
from django.views.static import serve
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
    
    path('django-admin/', admin.site.urls),
    path('dashboard/', include('dashboard.urls'), name='dashboard'),
    path('api/resume-review-day/', include('ResumeReviewDay.urls'), name='resume-review-day'),
    path('api/career-fair/', include('career_fair.urls'), name='career-fair'),
    path('api/reimbursement/', include('reimbursement.urls'), name='reimbursement'),

    # JWT Authentication endpoints (staff-only issuance; see StaffOnlyTokenObtainPairSerializer)
    path('api/token/', StaffOnlyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', StaffOnlyTokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]

# User-uploaded media (e.g. FileField in admin).
# DEBUG: django.contrib.staticfiles helper.
# Production without S3: serve from disk (e.g. Render). Set AWS_STORAGE_BUCKET_NAME for durable object storage.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif not getattr(settings, "USE_S3_MEDIA", False):
    _media_prefix = (settings.MEDIA_URL or "").lstrip("/")
    if _media_prefix and not _media_prefix.endswith("/"):
        _media_prefix = f"{_media_prefix}/"
    urlpatterns += [
        re_path(
            rf"^{re.escape(_media_prefix)}(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]
