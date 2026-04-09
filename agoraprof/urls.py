from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from content.views import (
    enrollments_list,
    settings_view,
    achievements_view,
    users_manage,
    users_invite,
    organizations_manage,
    organizations_create,
    departments_manage,
    departments_create,
    analytics_platform,
    analytics_organization,
    analytics_team,
    analytics_reports,
    team_add,
    team_assign,
    team_performance,
    team_schedule,
    team_communication,
    courses_browse,
    courses_manage_view,
    course_create_view,
    enrollments_manage_view,
    certificates_manage_view,
    student_certificates_view,
    assignments_manage_view,
    student_assignments_view,
)
from accounts.views import (
    dashboard_view,
    login_view,
    signup_view,
    logout_view,
    student_dashboard,
    manager_dashboard,
    admin_dashboard,
    superadmin_dashboard,
    profile_view,
    profile_edit_view,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Web pages
    path('', TemplateView.as_view(template_name='pages/landing.html'), name='landing'),
    path('login/', login_view, name='login'),
    path('signup/', signup_view, name='signup'),
    path('logout/', logout_view, name='logout'),
    
    # Account web views (specific paths)
    path('dashboard/student/', student_dashboard, name='student_dashboard'),
    path('dashboard/manager/', manager_dashboard, name='manager_dashboard'),
    path('dashboard/admin/', admin_dashboard, name='admin_dashboard'),
    path('dashboard/superadmin/', superadmin_dashboard, name='superadmin_dashboard'),
    
    # General dashboard (fallback)
    path('dashboard/', dashboard_view, name='dashboard'),

    # User account pages
    path('profile/', profile_view, name='profile'),
    path('profile/edit/', profile_edit_view, name='profile_edit'),
    path('settings/', settings_view, name='settings'),
    path('achievements/', achievements_view, name='achievements'),

    # Common management shortcuts
    path('users/manage/', users_manage, name='users_manage'),
    path('users/invite/', users_invite, name='users_invite'),
    path('organizations/manage/', organizations_manage, name='organizations_manage'),
    path('organizations/create/', organizations_create, name='organizations_create'),
    path('departments/manage/', departments_manage, name='departments_manage'),
    path('departments/create/', departments_create, name='departments_create'),
    path('analytics/platform/', analytics_platform, name='analytics_platform'),
    path('analytics/organization/', analytics_organization, name='analytics_organization'),
    path('analytics/team/', analytics_team, name='analytics_team'),
    path('analytics/reports/', analytics_reports, name='analytics_reports'),
    path('team/add/', team_add, name='team_add'),
    path('team/assign/', team_assign, name='team_assign'),
    path('team/performance/', team_performance, name='team_performance'),
    path('team/schedule/', team_schedule, name='team_schedule'),
    path('team/communication/', team_communication, name='team_communication'),
    path('courses/browse/', courses_browse, name='courses_browse_root'),
    path('courses/manage/', courses_manage_view, name='courses_manage_root'),
    path('courses/create/', course_create_view, name='course_create_root'),
    path('enrollments/manage/', enrollments_manage_view, name='enrollments_manage_root'),
    path('certificates/manage/', certificates_manage_view, name='certificates_manage_root'),
    path('certificates/my/', student_certificates_view, name='student_certificates_root'),
    path('assignments/manage/', assignments_manage_view, name='assignments_manage_root'),
    path('assignments/my/', student_assignments_view, name='student_assignments_root'),
    path('reports/', analytics_reports, name='reports_root'),
    
    # Content and learning
    path('content/', include(('content.urls', 'content'), namespace='content')),
    path('enhanced/', include(('content.enhanced_urls', 'content'), namespace='enhanced_content')),
    path('learning/', include(('content.urls', 'content'), namespace='learning_content')),
    path('courses/', include(('content.urls', 'content'), namespace='courses_content')),
    path('courses/', include('courses.urls')),  # Add courses app URLs
    
    # User management
    path('users/', include(('content.urls', 'content'), namespace='users_content')),
    
    # Organization management
    path('certificates/', include(('certificates.urls', 'certificates'), namespace='certificates')),
    
    # Team management (using content views)
    
    # Analytics
    
    # Static pages
    path('enrollments/', enrollments_list, name='enrollments'),
    path('assignments/', student_assignments_view, name='assignments'),
    path('about/', TemplateView.as_view(template_name='pages/about.html'), name='about'),
    path('features/', TemplateView.as_view(template_name='pages/features.html'), name='features'),
    path('pricing/', TemplateView.as_view(template_name='pages/pricing.html'), name='pricing'),
    path('faq/', TemplateView.as_view(template_name='pages/faq.html'), name='faq'),
    
    # API URLs
    path('api/accounts/', include(('accounts.urls', 'accounts'), namespace='accounts_api')),
    path('api/organizations/', include('organizations.urls')),
    path('api/permissions/', include('permissions.urls')),
    path('api/courses/', include('courses.urls')),
    path('api/enrollments/', include('enrollments.urls')),
    path('api/assignments/', include('assignments.urls')),
    path('api/certificates/', include(('certificates.urls', 'certificates'), namespace='certificates_api')),
    path('api/notifications/', include('notifications.urls')),
    path('api/reports/', include('reports.urls')),
    path('api/audit-logs/', include('audit_logs.urls')),
    path('api/analytics/', include('analytics.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += staticfiles_urlpatterns()
