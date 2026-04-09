from rest_framework import permissions
from .models import Enrollment, LessonProgress


class IsEnrollmentOwner(permissions.BasePermission):
    """
    Allows access only to enrollment owner
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if isinstance(obj, Enrollment):
            return obj.user == request.user
        
        return False


class CanManageEnrollment(permissions.BasePermission):
    """
    Allows access only to users who can manage enrollments
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if not isinstance(obj, Enrollment):
            return False
        
        # Superadmin can manage all enrollments
        if request.user.is_superadmin():
            return True
        
        # Admin can manage enrollments in their organization
        if request.user.is_admin() and obj.course.organization == request.user.organization:
            return True
        
        # Course instructor can manage enrollments in their course
        if obj.course.instructor == request.user:
            return True
        
        return False


class CanViewEnrollment(permissions.BasePermission):
    """
    Allows access to view enrollment details
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if not isinstance(obj, Enrollment):
            return False
        
        # Superadmin can view all enrollments
        if request.user.is_superadmin():
            return True
        
        # Admin can view enrollments in their organization
        if request.user.is_admin() and obj.course.organization == request.user.organization:
            return True
        
        # Course instructor can view enrollments in their course
        if obj.course.instructor == request.user:
            return True
        
        # Enrollment owner can view their own enrollment
        if obj.user == request.user:
            return True
        
        return False


class IsLessonProgressOwner(permissions.BasePermission):
    """
    Allows access only to lesson progress owner
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if isinstance(obj, LessonProgress):
            return obj.enrollment.user == request.user
        
        return False


class CanManageLessonProgress(permissions.BasePermission):
    """
    Allows access only to users who can manage lesson progress
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if not isinstance(obj, LessonProgress):
            return False
        
        # Superadmin can manage all lesson progress
        if request.user.is_superadmin():
            return True
        
        # Admin can manage lesson progress in their organization
        if request.user.is_admin() and obj.lesson.module.course.organization == request.user.organization:
            return True
        
        # Course instructor can manage lesson progress in their course
        if obj.lesson.module.course.instructor == request.user:
            return True
        
        # Lesson progress owner can manage their own progress
        if obj.enrollment.user == request.user:
            return True
        
        return False


class CanEnrollInCourse(permissions.BasePermission):
    """
    Allows access only to users who can enroll in course
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Superadmin can enroll in any course
        if request.user.is_superadmin():
            return True
        
        # Admin can enroll in courses in their organization
        if request.user.is_admin():
            return True
        
        # Manager can enroll in courses in their organization
        if request.user.is_manager():
            return True
        
        # Students can enroll in accessible courses
        if request.user.is_student():
            return True
        
        return False


class CanViewEnrollmentStatistics(permissions.BasePermission):
    """
    Allows access only to users who can view enrollment statistics
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Superadmin can view all statistics
        if request.user.is_superadmin():
            return True
        
        # Admin can view organization statistics
        if request.user.is_admin():
            return True
        
        # Manager can view team statistics
        if request.user.is_manager():
            return True
        
        return False


class CanManageCertificates(permissions.BasePermission):
    """
    Allows access only to users who can manage certificates
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Superadmin can manage all certificates
        if request.user.is_superadmin():
            return True
        
        # Admin can manage certificates in their organization
        if request.user.is_admin():
            return True
        
        return False


class IsCertificateOwner(permissions.BasePermission):
    """
    Allows access only to certificate owner
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if hasattr(obj, 'enrollment'):
            return obj.enrollment.user == request.user
        
        return False
