from django.urls import path
from . import enhanced_views

app_name = 'content'

urlpatterns = [
    # Enhanced Course Management
    path('courses/', enhanced_views.enhanced_courses_list_view, name='enhanced_courses_list'),
    path('courses/create/', enhanced_views.enhanced_course_create_view, name='enhanced_course_create'),
    path('course/<uuid:course_id>/', enhanced_views.enhanced_course_detail_view, name='enhanced_course_detail'),
    path('course/<uuid:course_id>/edit/', enhanced_views.enhanced_course_edit_view, name='enhanced_course_edit'),
    path('course/<uuid:course_id>/update/', enhanced_views.enhanced_course_update_view, name='enhanced_course_update'),
    path('course/<uuid:course_id>/delete/', enhanced_views.enhanced_course_delete_view, name='enhanced_course_delete'),
    
    # API Endpoints
    path('api/course/<uuid:course_id>/upload-file/', enhanced_views.api_upload_course_file, name='api_upload_course_file'),
]
