from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, RoleRequestViewSet, signup_view, dashboard_view, logout_view, dashboard_stats,
    superadmin_dashboard, admin_dashboard, manager_dashboard, student_dashboard,
    profile_view, upload_avatar, remove_avatar, change_password
)
from . import api_views_extended

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'role-requests', RoleRequestViewSet, basename='role-request')

urlpatterns = [
    path('', include(router.urls)),
    # API endpoints
    path('dashboard/stats/', dashboard_stats, name='dashboard_stats'),
    path('analytics/platform/', api_views_extended.platform_analytics, name='platform_analytics'),
    path('analytics/organization/', api_views_extended.organization_analytics, name='organization_analytics'),
    path('analytics/team/', api_views_extended.team_analytics, name='team_analytics'),
    path('analytics/student/', api_views_extended.student_analytics, name='student_analytics'),
    path('users/organization/', api_views_extended.organization_users, name='organization_users'),
    path('users/team/', api_views_extended.team_members, name='team_members'),
    path('training/assign/', api_views_extended.assign_training, name='assign_training'),
    path('permissions/', api_views_extended.user_permissions, name='user_permissions'),
    path('system/health/', api_views_extended.system_health, name='system_health'),
    # Web views
    path('signup/', signup_view, name='web_signup'),
    path('profile/', profile_view, name='profile'),
    path('upload-avatar/', upload_avatar, name='upload_avatar'),
    path('remove-avatar/', remove_avatar, name='remove_avatar'),
    path('change-password/', change_password, name='change_password'),
    path('dashboard/', dashboard_view, name='web_dashboard'),
    path('dashboard/superadmin/', superadmin_dashboard, name='superadmin_dashboard'),
    path('dashboard/admin/', admin_dashboard, name='admin_dashboard'),
    path('dashboard/manager/', manager_dashboard, name='manager_dashboard'),
    path('dashboard/student/', student_dashboard, name='student_dashboard'),
    path('logout/', logout_view, name='web_logout'),
]
