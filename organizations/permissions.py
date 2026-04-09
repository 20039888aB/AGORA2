from rest_framework import permissions
from .models import Organization, Department, Team


class IsOrganizationMember(permissions.BasePermission):
    """
    Allows access only to organization members
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if isinstance(obj, Organization):
            return request.user.organization == obj
        
        # For department/team objects
        if hasattr(obj, 'organization'):
            return request.user.organization == obj.organization
        
        return False


class IsOrganizationAdmin(permissions.BasePermission):
    """
    Allows access only to organization admins
    """
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_admin_or_above()
        )
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if isinstance(obj, Organization):
            return request.user.can_manage_organization(obj)
        
        return False


class CanManageDepartment(permissions.BasePermission):
    """
    Allows access only to users who can manage the department
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if not isinstance(obj, Department):
            return False
        
        # Superadmin can manage all departments
        if request.user.is_superadmin():
            return True
        
        # Admin can manage departments in their organization
        if request.user.is_admin() and obj.organization == request.user.organization:
            return True
        
        # Department head can manage their own department
        if obj.head == request.user:
            return True
        
        return False


class CanManageTeam(permissions.BasePermission):
    """
    Allows access only to users who can manage the team
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if not isinstance(obj, Team):
            return False
        
        # Superadmin can manage all teams
        if request.user.is_superadmin():
            return True
        
        # Admin can manage teams in their organization
        if request.user.is_admin() and obj.organization == request.user.organization:
            return True
        
        # Team lead can manage their own team
        if obj.lead == request.user:
            return True
        
        # Manager can manage teams in their department
        if (request.user.is_manager() and 
            obj.department and 
            obj.department.organization == request.user.organization and
            request.user.profile.department == obj.department):
            return True
        
        return False


class IsDepartmentMember(permissions.BasePermission):
    """
    Allows access only to department members
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if not isinstance(obj, Department):
            return False
        
        # Check if user is member of the department
        from .models import DepartmentMembership
        return DepartmentMembership.objects.filter(
            user=request.user,
            department=obj
        ).exists()


class IsTeamMember(permissions.BasePermission):
    """
    Allows access only to team members
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if not isinstance(obj, Team):
            return False
        
        # Check if user is member of the team
        from .models import TeamMembership
        return TeamMembership.objects.filter(
            user=request.user,
            team=obj
        ).exists()


class OrganizationBasedPermission(permissions.BasePermission):
    """
    Dynamic permission based on organization membership
    """
    
    def __init__(self, allowed_roles=None):
        self.allowed_roles = allowed_roles or []
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.organization and
            (not self.allowed_roles or request.user.role in self.allowed_roles)
        )
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Check object has organization
        obj_org = None
        if hasattr(obj, 'organization'):
            obj_org = obj.organization
        elif hasattr(obj, 'department') and hasattr(obj.department, 'organization'):
            obj_org = obj.department.organization
        elif hasattr(obj, 'team') and hasattr(obj.team, 'organization'):
            obj_org = obj.team.organization
        
        return obj_org == request.user.organization
