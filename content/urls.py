from django.urls import path
from . import views

app_name = 'content'

urlpatterns = [
    # Content management
    path('upload/', views.content_upload, name='content_upload'),
    path('manager-library/', views.manager_uploaded_content, name='manager_uploaded_content'),
    path('organize/', views.content_organize, name='content_organize'),
    path('approve/', views.content_approve, name='content_approve'),
    path('browse/', views.courses_browse, name='courses_browse'),
    path('catalog/', views.ContentBrowseView.as_view(), name='content_browse'),
    
    # Learning
    path('continue/', views.learning_continue, name='learning_continue'),
    path('paths/', views.learning_paths_view, name='learning_paths'),
    
    # Dashboard
    path('profile/', views.profile_view, name='profile_detail'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('settings/', views.settings_view, name='user_settings'),
    path('admin/', views.admin_dashboard_view, name='admin_dashboard'),
    
    # Courses
    path('', views.courses_list_view, name='courses_list'),
    path('list/', views.courses_manage_view, name='courses_list_alt'),  # Alternative for /courses/list/
    path('manage/', views.courses_manage_view, name='courses_manage'),
    path('create/', views.course_create_view, name='course_create'),
    path('course/<uuid:course_id>/edit/', views.course_edit_view, name='course_edit'),
    path('course/<uuid:course_id>/update/', views.course_update_view, name='course_update'),
    path('course/<uuid:course_id>/delete/', views.course_delete_view, name='course_delete'),
    path('student-courses/', views.student_course_browse, name='student_course_browse'),
    path('course/<uuid:course_id>/', views.course_detail_view, name='course_detail'),
    path('course/<uuid:course_id>/finish/', views.finish_course, name='finish_course'),
    path('enroll/<uuid:course_id>/', views.enroll_student, name='enroll_student'),
    path('progress/<uuid:course_id>/', views.update_progress, name='update_progress'),
    
    # API endpoints
    path('api/documents/<str:document_id>/view/', views.view_document, name='view_document'),
    path('api/documents/<str:document_id>/complete/', views.mark_document_complete, name='mark_document_complete'),
    path('api/courses/<uuid:course_id>/enroll/', views.enroll_in_course, name='enroll_in_course'),
    
    # Organizations
    path('organizations/manage/', views.organizations_manage, name='organizations_manage'),
    path('organizations/create/', views.organizations_create, name='organizations_create'),
    
    # Users
    path('users/manage/', views.users_manage, name='users_manage'),
    path('users/invite/', views.users_invite, name='users_invite'),
    
    # Departments
    path('departments/manage/', views.departments_manage, name='departments_manage'),
    path('departments/create/', views.departments_create, name='departments_create'),
    
    # Enrollments
    path('enrollments/manage/', views.enrollments_manage_view, name='enrollments_manage'),
    
    # Assignments
    path('assignments/manage/', views.assignments_manage_view, name='assignments_manage'),
    path('assignments/my/', views.student_assignments_view, name='student_assignments'),
    
    # Certificates
    path('certificates/manage/', views.certificates_manage_view, name='certificates_manage'),
    path('certificates/my/', views.student_certificates_view, name='student_certificates'),
    path('course/<uuid:course_id>/certificate/', views.download_certificate, name='download_certificate'),
    
    # Team management
    path('team/add/', views.team_add, name='team_add'),
    path('team/assign/', views.team_assign, name='team_assign'),
    path('team/performance/', views.team_performance, name='team_performance'),
    path('team/schedule/', views.team_schedule, name='team_schedule'),
    path('team/communication/', views.team_communication, name='team_communication'),
    
    # Analytics
    path('analytics/platform/', views.analytics_platform, name='analytics_platform'),
    path('analytics/organization/', views.analytics_organization, name='analytics_organization'),
    path('analytics/team/', views.analytics_team, name='analytics_team'),
    path('analytics/reports/', views.analytics_reports, name='analytics_reports'),
    
    # Achievements
    path('achievements/', views.achievements_view, name='achievements'),
]
