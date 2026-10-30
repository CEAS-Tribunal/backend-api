from rest_framework.routers import DefaultRouter

from .views import JudgeViewSet

router = DefaultRouter()
router.register(r"judges", JudgeViewSet, basename="expo-judges")

urlpatterns = router.urls
