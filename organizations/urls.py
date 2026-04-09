from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    OrganizationViewSet, DepartmentViewSet, TeamViewSet,
    DepartmentMembershipViewSet, TeamMembershipViewSet
)

router = DefaultRouter()
router.register(r'organizations', OrganizationViewSet, basename='organization')
router.register(r'departments', DepartmentViewSet, basename='department')
router.register(r'teams', TeamViewSet, basename='team')
router.register(r'department-memberships', DepartmentMembershipViewSet, basename='department-membership')
router.register(r'team-memberships', TeamMembershipViewSet, basename='team-membership')

urlpatterns = [
    path('', include(router.urls)),
]
