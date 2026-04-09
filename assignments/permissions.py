from rest_framework import permissions
from .models import Assignment, AssignmentSubmission, AssignmentQuestion


class IsAssignmentOwner(permissions.BasePermission):
    """
    Allows access only to assignment owner (creator)
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if isinstance(obj, Assignment):
            return obj.created_by == request.user
        
        return False


class CanManageAssignment(permissions.BasePermission):
    """
    Allows access only to users who can manage assignments
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if not isinstance(obj, Assignment):
            return False
        
        # Superadmin can manage all assignments
        if request.user.is_superadmin():
            return True
        
        # Admin can manage assignments in their organization
        if request.user.is_admin() and obj.course.organization == request.user.organization:
            return True
        
        # Course instructor can manage assignments in their course
        if obj.course.instructor == request.user:
            return True
        
        return False


class CanViewAssignment(permissions.BasePermission):
    """
    Allows access to view assignment details
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if not isinstance(obj, Assignment):
            return False
        
        # Superadmin can view all assignments
        if request.user.is_superadmin():
            return True
        
        # Admin can view assignments in their organization
        if request.user.is_admin() and obj.course.organization == request.user.organization:
            return True
        
        # Course instructor can view assignments in their course
        if obj.course.instructor == request.user:
            return True
        
        # Students can view assignments they're enrolled in
        if request.user.is_student():
            from enrollments.models import Enrollment
            return Enrollment.objects.filter(
                user=request.user,
                course=obj.course,
                status='ACTIVE'
            ).exists()
        
        return False


class IsSubmissionOwner(permissions.BasePermission):
    """
    Allows access only to submission owner
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if isinstance(obj, AssignmentSubmission):
            return obj.student == request.user
        
        return False


class CanManageSubmission(permissions.BasePermission):
    """
    Allows access only to users who can manage submissions
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if not isinstance(obj, AssignmentSubmission):
            return False
        
        # Superadmin can manage all submissions
        if request.user.is_superadmin():
            return True
        
        # Admin can manage submissions in their organization
        if request.user.is_admin() and obj.assignment.course.organization == request.user.organization:
            return True
        
        # Course instructor can manage submissions in their course
        if obj.assignment.course.instructor == request.user:
            return True
        
        # Submission owner can manage their own submission
        if obj.student == request.user:
            return True
        
        return False


class CanGradeSubmission(permissions.BasePermission):
    """
    Allows access only to users who can grade submissions
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if not isinstance(obj, AssignmentSubmission):
            return False
        
        # Superadmin can grade all submissions
        if request.user.is_superadmin():
            return True
        
        # Admin can grade submissions in their organization
        if request.user.is_admin() and obj.assignment.course.organization == request.user.organization:
            return True
        
        # Course instructor can grade submissions in their course
        if obj.assignment.course.instructor == request.user:
            return True
        
        return False


class CanManageQuestion(permissions.BasePermission):
    """
    Allows access only to users who can manage questions
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if not isinstance(obj, AssignmentQuestion):
            return False
        
        # Superadmin can manage all questions
        if request.user.is_superadmin():
            return True
        
        # Admin can manage questions in their organization
        if request.user.is_admin() and obj.assignment.course.organization == request.user.organization:
            return True
        
        # Course instructor can manage questions in their course
        if obj.assignment.course.instructor == request.user:
            return True
        
        return False


class CanSubmitAssignment(permissions.BasePermission):
    """
    Allows access only to users who can submit assignments
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Students can submit assignments
        if request.user.is_student():
            return True
        
        return False


class CanViewAssignmentStatistics(permissions.BasePermission):
    """
    Allows access only to users who can view assignment statistics
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
        
        # Course instructor can view their course statistics
        if request.user.is_manager():
            return True
        
        return False


class IsFileOwner(permissions.BasePermission):
    """
    Allows access only to file owner
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if isinstance(obj, AssignmentFile):
            return obj.uploaded_by == request.user
        
        return False


class CanManageFile(permissions.BasePermission):
    """
    Allows access only to users who can manage files
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if not isinstance(obj, AssignmentFile):
            return False
        
        # Superadmin can manage all files
        if request.user.is_superadmin():
            return True
        
        # Admin can manage files in their organization
        if request.user.is_admin():
            if obj.assignment:
                return obj.assignment.course.organization == request.user.organization
            elif obj.submission:
                return obj.submission.assignment.course.organization == request.user.organization
        
        # Course instructor can manage files in their course
        if request.user.is_manager():
            if obj.assignment:
                return obj.assignment.course.instructor == request.user
            elif obj.submission:
                return obj.submission.assignment.course.instructor == request.user
        
        # File owner can manage their own files
        if obj.uploaded_by == request.user:
            return True
        
        return False
