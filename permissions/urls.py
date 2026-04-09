from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PermissionViewSet, RolePermissionViewSet, UserPermissionViewSet,
    PermissionTemplateViewSet
)

router = DefaultRouter()
router.register(r'permissions', PermissionViewSet, basename='permission')
router.register(r'role-permissions', RolePermissionViewSet, basename='role-permission')
router.register(r'user-permissions', UserPermissionViewSet, basename='user-permission')
router.register(r'permission-templates', PermissionTemplateViewSet, basename='permission-template')

urlpatterns = [
    path('', include(router.urls)),
]
