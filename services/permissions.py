"""
REAL Permission System - Centralized Permission Logic

This module contains the actual permission classes that should be used
instead of putting logic directly in individual app permissions.
"""

from rest_framework import permissions
from django.contrib.auth import get_user_model

User = get_user_model()


class IsSuperAdmin(permissions.BasePermission):
    """
    Allows access only to superadmins
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_superadmin()


class IsAdmin(permissions.BasePermission):
    """
    Allows access only to admins
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin()


class IsManager(permissions.BasePermission):
    """
    Allows access only to managers
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_manager()


class IsStudent(permissions.BasePermission):
    """
    Allows access only to students
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_student()


class IsAdminOrAbove(permissions.BasePermission):
    """
    Allows access to admins and superadmins
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin_or_above()


class IsManagerOrAbove(permissions.BasePermission):
    """
    Allows access to managers, admins, and superadmins
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_manager_or_above()


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Allows access to resource owner or admin
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Superadmin can access everything
        if request.user.is_superadmin():
            return True
        
        # Admin can access everything in their organization
        if request.user.is_admin():
            return self._check_organization_match(obj, request.user.organization)
        
        # Owner can access their own resources
        return self._check_ownership(obj, request.user)
    
    def _check_organization_match(self, obj, user_organization):
        """Check if object belongs to user's organization"""
        if hasattr(obj, 'organization'):
            return obj.organization == user_organization
        elif hasattr(obj, 'course') and hasattr(obj.course, 'organization'):
            return obj.course.organization == user_organization
        elif hasattr(obj, 'user') and hasattr(obj.user, 'organization'):
            return obj.user.organization == user_organization
        return False
    
    def _check_ownership(self, obj, user):
        """Check if user owns the object"""
        if hasattr(obj, 'user'):
            return obj.user == user
        elif hasattr(obj, 'student'):
            return obj.student == user
        elif hasattr(obj, 'instructor'):
            return obj.instructor == user
        return False


class IsCourseInstructor(permissions.BasePermission):
    """
    Allows access only to course instructor
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Superadmin can access everything
        if request.user.is_superadmin():
            return True
        
        # Check if user is the course instructor
        if hasattr(obj, 'course') and hasattr(obj.course, 'instructor'):
            return obj.course.instructor == request.user
        
        # Check if user is the instructor
        if hasattr(obj, 'instructor'):
            return obj.instructor == request.user
        
        return False


class IsOrganizationMember(permissions.BasePermission):
    """
    Allows access only to organization members
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Superadmin can access everything
        if request.user.is_superadmin():
            return True
        
        # Check organization membership
        if hasattr(obj, 'organization'):
            return obj.organization == request.user.organization
        elif hasattr(obj, 'course') and hasattr(obj.course, 'organization'):
            return obj.course.organization == request.user.organization
        elif hasattr(obj, 'user') and hasattr(obj.user, 'organization'):
            return obj.user.organization == request.user.organization
        
        return False


class CanManageOrganization(permissions.BasePermission):
    """
    Allows access only to users who can manage organization
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin_or_above()


class CanManageCourse(permissions.BasePermission):
    """
    Allows access only to users who can manage courses
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin_or_above()
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Superadmin can manage all courses
        if request.user.is_superadmin():
            return True
        
        # Admin can manage courses in their organization
        if request.user.is_admin():
            return self._check_organization_match(obj, request.user.organization)
        
        # Manager can manage their own courses
        if request.user.is_manager():
            return self._check_course_instructor(obj, request.user)
        
        return False
    
    def _check_course_instructor(self, obj, user):
        """Check if user is the course instructor"""
        if hasattr(obj, 'course') and hasattr(obj.course, 'instructor'):
            return obj.course.instructor == user
        elif hasattr(obj, 'instructor'):
            return obj.instructor == user
        return False


class CanManageEnrollment(permissions.BasePermission):
    """
    Allows access only to users who can manage enrollments
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin_or_above()
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Superadmin can manage all enrollments
        if request.user.is_superadmin():
            return True
        
        # Admin can manage enrollments in their organization
        if request.user.is_admin():
            return self._check_organization_match(obj, request.user.organization)
        
        # Manager can manage enrollments in their courses
        if request.user.is_manager():
            return self._check_course_instructor(obj, request.user)
        
        # Student can manage their own enrollments
        if request.user.is_student():
            return self._check_ownership(obj, request.user)
        
        return False


class CanManageAssignment(permissions.BasePermission):
    """
    Allows access only to users who can manage assignments
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin_or_above()
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Superadmin can manage all assignments
        if request.user.is_superadmin():
            return True
        
        # Admin can manage assignments in their organization
        if request.user.is_admin():
            return self._check_organization_match(obj, request.user.organization)
        
        # Manager can manage assignments in their courses
        if request.user.is_manager():
            return self._check_course_instructor(obj, request.user)
        
        return False


class CanManageCertificate(permissions.BasePermission):
    """
    Allows access only to users who can manage certificates
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin_or_above()
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Superadmin can manage all certificates
        if request.user.is_superadmin():
            return True
        
        # Admin can manage certificates in their organization
        if request.user.is_admin():
            return self._check_organization_match(obj, request.user.organization)
        
        # Certificate owner can manage their own certificates
        if request.user.is_student():
            return self._check_ownership(obj, request.user)
        
        return False


class MultiTenantQuerysetMixin:
    """
    Mixin to enforce multi-tenancy in ViewSets
    """
    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        
        if not user.is_authenticated:
            return queryset.none()
        
        if user.is_superadmin():
            return queryset
        
        # Filter by user's organization
        if hasattr(queryset.model, 'organization'):
            return queryset.filter(organization=user.organization)
        elif hasattr(queryset.model, 'course'):
            return queryset.filter(course__organization=user.organization)
        elif hasattr(queryset.model, 'user'):
            return queryset.filter(user__organization=user.organization)
        elif hasattr(queryset.model, 'student'):
            return queryset.filter(student__organization=user.organization)
        
        return queryset


class IsEnrolledStudent(permissions.BasePermission):
    """
    Allows access only to enrolled students
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_student()
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Check if user is enrolled in the course
        if hasattr(obj, 'course'):
            from enrollments.models import Enrollment
            return Enrollment.objects.filter(
                user=request.user,
                course=obj.course,
                status='ACTIVE',
                is_active=True
            ).exists()
        
        return False


class CanSubmitAssignment(permissions.BasePermission):
    """
    Allows access only to users who can submit assignments
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_student()
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Check if user is enrolled in the course and assignment is available
        if hasattr(obj, 'assignment'):
            from enrollments.models import Enrollment
            enrollment = Enrollment.objects.filter(
                user=request.user,
                course=obj.assignment.course,
                status='ACTIVE',
                is_active=True
            ).first()
            
            return enrollment and obj.assignment.is_available
        
        return False
