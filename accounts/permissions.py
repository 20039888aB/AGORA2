from rest_framework import permissions
from .models import User


class IsSuperAdmin(permissions.BasePermission):
    """
    Allows access only to superadmin users
    """
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_superadmin()
        )
    
    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsAdmin(permissions.BasePermission):
    """
    Allows access only to admin users (exact admin role, not including superadmins)
    """
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_admin()
        )
    
    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsAdminOrAbove(permissions.BasePermission):
    """
    Allows access only to admin users and above (including superadmins)
    """
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_admin_or_above()
        )
    
    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsManager(permissions.BasePermission):
    """
    Allows access only to manager users (exact manager role, not including admins)
    """
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_manager()
        )
    
    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsManagerOrAbove(permissions.BasePermission):
    """
    Allows access only to manager users and above (including admins and superadmins)
    """
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_manager_or_above()
        )
    
    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Allows access only to owners of the object or read-only access
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'id') and hasattr(request.user, 'id'):
            return obj.id == request.user.id
        
        return False


class CanManageUser(permissions.BasePermission):
    """
    Allows access only if user can manage the target user
    """
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated
        )
    
    def has_object_permission(self, request, view, obj):
        if not isinstance(obj, User):
            # Try to get user from object
            user = getattr(obj, 'user', None)
            if not user:
                return False
            obj = user
        
        return request.user.can_manage_user(obj)


class CanAccessUserData(permissions.BasePermission):
    """
    Allows access to user data based on role hierarchy
    """
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated
        )
    
    def has_object_permission(self, request, view, obj):
        if not isinstance(obj, User):
            # Try to get user from object
            user = getattr(obj, 'user', None)
            if not user:
                return False
            obj = user
        
        return request.user.can_access_user_data(obj)


class IsSameOrganization(permissions.BasePermission):
    """
    Allows access only to users from the same organization
    """
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.organization
        )
    
    def has_object_permission(self, request, view, obj):
        if not request.user.organization:
            return False
        
        # Get organization from object
        obj_org = getattr(obj, 'organization', None)
        if not obj_org:
            # Try to get user and then organization
            obj_user = getattr(obj, 'user', None)
            if obj_user:
                obj_org = getattr(obj_user, 'organization', None)
        
        return obj_org == request.user.organization


class IsSameDepartment(permissions.BasePermission):
    """
    Allows access only to users from the same department
    """
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.profile and
            request.user.profile.department
        )
    
    def has_object_permission(self, request, view, obj):
        if not request.user.profile or not request.user.profile.department:
            return False
        
        # Get department from object
        obj_dept = getattr(obj, 'department', None)
        if not obj_dept:
            # Try to get user and then department
            obj_user = getattr(obj, 'user', None)
            if obj_user and hasattr(obj_user, 'profile'):
                obj_dept = getattr(obj_user.profile, 'department', None)
        
        return obj_dept == request.user.profile.department


class IsSameTeam(permissions.BasePermission):
    """
    Allows access only to users from the same team
    """
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.profile and
            request.user.profile.team
        )
    
    def has_object_permission(self, request, view, obj):
        if not request.user.profile or not request.user.profile.team:
            return False
        
        # Get team from object
        obj_team = getattr(obj, 'team', None)
        if not obj_team:
            # Try to get user and then team
            obj_user = getattr(obj, 'user', None)
            if obj_user and hasattr(obj_user, 'profile'):
                obj_team = getattr(obj_user.profile, 'team', None)
        
        return obj_team == request.user.profile.team


class RoleBasedPermission(permissions.BasePermission):
    """
    Dynamic permission based on user role and object relationship
    """
    
    def __init__(self, allowed_roles=None, object_field=None):
        self.allowed_roles = allowed_roles or []
        self.object_field = object_field
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in self.allowed_roles
        )
    
    def has_object_permission(self, request, view, obj):
        if not self.has_permission(request, view):
            return False
        
        # If no object field specified, allow based on role
        if not self.object_field:
            return True
        
        # Check object field access
        obj_value = getattr(obj, self.object_field, None)
        user_value = getattr(request.user, self.object_field, None)
        
        return obj_value == user_value
