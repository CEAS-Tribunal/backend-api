from rest_framework.routers import DefaultRouter

from .views import JudgeAssignmentViewSet, JudgeViewSet, StudentViewSet

router = DefaultRouter()
router.register(r"judges", JudgeViewSet, basename="expo-judges")
router.register(r"students", StudentViewSet, basename="expo-students")
router.register(r"assignments", JudgeAssignmentViewSet, basename="expo-assignments")

urlpatterns = router.urls
