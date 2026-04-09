from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet, CourseViewSet, ModuleViewSet, LessonViewSet,
    ResourceViewSet, CourseReviewViewSet
)
from . import django_views

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'modules', ModuleViewSet, basename='module')
router.register(r'lessons', LessonViewSet, basename='lesson')
router.register(r'resources', ResourceViewSet, basename='resource')
router.register(r'course-reviews', CourseReviewViewSet, basename='course-review')

urlpatterns = [
    # API URLs
    path('', include(router.urls)),
    
    # Django Views for Document Management
    path('course/<uuid:course_id>/documents/', django_views.course_documents, name='course_documents'),
    path('course/<uuid:course_id>/documents/student/', django_views.student_course_documents, name='student_course_documents'),
    path('course/<uuid:course_id>/documents/add/', django_views.add_course_document, name='add_course_document'),
    path('course/<uuid:course_id>/documents/<uuid:document_id>/edit/', django_views.edit_course_document, name='edit_course_document'),
    path('course/<uuid:course_id>/documents/<uuid:document_id>/delete/', django_views.delete_course_document, name='delete_course_document'),
    path('course/<uuid:course_id>/documents/bulk-upload/', django_views.bulk_upload_documents, name='bulk_upload_documents'),
    path('course/<uuid:course_id>/documents/reorder/', django_views.reorder_documents, name='reorder_documents'),
]
