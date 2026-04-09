from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AssignmentViewSet, AssignmentQuestionViewSet, AssignmentSubmissionViewSet, AssignmentFileViewSet
)

router = DefaultRouter()
router.register(r'assignments', AssignmentViewSet, basename='assignment')
router.register(r'assignment-questions', AssignmentQuestionViewSet, basename='assignment-question')
router.register(r'assignment-submissions', AssignmentSubmissionViewSet, basename='assignment-submission')
router.register(r'assignment-files', AssignmentFileViewSet, basename='assignment-file')

urlpatterns = [
    path('', include(router.urls)),
]
