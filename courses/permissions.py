from rest_framework import permissions
from .models import Course, Module, Lesson, Resource


class IsCourseInstructor(permissions.BasePermission):
    """
    Allows access only to course instructors
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if isinstance(obj, Course):
            return obj.instructor == request.user
        
        return False


class CanManageCourse(permissions.BasePermission):
    """
    Allows access only to users who can manage the course
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if not isinstance(obj, Course):
            return False
        
        # Superadmin can manage all courses
        if request.user.is_superadmin():
            return True
        
        # Admin can manage courses in their organization
        if request.user.is_admin() and obj.organization == request.user.organization:
            return True
        
        # Course instructor can manage their own course
        if obj.instructor == request.user:
            return True
        
        return False


class IsCourseMember(permissions.BasePermission):
    """
    Allows access only to enrolled course members
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if not isinstance(obj, Course):
            return False
        
        # Check if user is enrolled in the course
        from enrollments.models import Enrollment
        return Enrollment.objects.filter(
            user=request.user,
            course=obj,
            is_active=True
        ).exists()


class CanAccessCourseContent(permissions.BasePermission):
    """
    Allows access only to course content (modules, lessons, resources)
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if not isinstance(obj, Course):
            return False
        
        # Superadmin can access all course content
        if request.user.is_superadmin():
            return True
        
        # Admin can access content in their organization
        if request.user.is_admin() and obj.organization == request.user.organization:
            return True
        
        # Course instructor can access their own course content
        if obj.instructor == request.user:
            return True
        
        # Enrolled students can access published course content
        if obj.is_accessible and request.user.has_permission(
            'COURSE', 'READ', str(obj.id)
        ):
            return True
        
        return False


class CanManageModule(permissions.BasePermission):
    """
    Allows access only to users who can manage modules
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if not isinstance(obj, Module):
            return False
        
        # Superadmin can manage all modules
        if request.user.is_superadmin():
            return True
        
        # Admin can manage modules in their organization
        if request.user.is_admin() and obj.course.organization == request.user.organization:
            return True
        
        # Course instructor can manage modules in their course
        if obj.course.instructor == request.user:
            return True
        
        return False


class CanManageLesson(permissions.BasePermission):
    """
    Allows access only to users who can manage lessons
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if not isinstance(obj, Lesson):
            return False
        
        # Superadmin can manage all lessons
        if request.user.is_superadmin():
            return True
        
        # Admin can manage lessons in their organization
        if request.user.is_admin() and obj.module.course.organization == request.user.organization:
            return True
        
        # Course instructor can manage lessons in their course
        if obj.module.course.instructor == request.user:
            return True
        
        return False


class CanManageResource(permissions.BasePermission):
    """
    Allows access only to users who can manage resources
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if not isinstance(obj, Resource):
            return False
        
        # Superadmin can manage all resources
        if request.user.is_superadmin():
            return True
        
        # Admin can manage resources in their organization
        if request.user.is_admin() and obj.lesson.module.course.organization == request.user.organization:
            return True
        
        # Course instructor can manage resources in their course
        if obj.lesson.module.course.instructor == request.user:
            return True
        
        return False
