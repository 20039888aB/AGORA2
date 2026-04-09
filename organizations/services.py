from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Organization, Department, Team, DepartmentMembership, TeamMembership


class OrganizationService:
    """
    Service layer for Organization business logic
    """
    
    @staticmethod
    def create_organization(data, creator=None):
        """Create new organization with validation"""
        # Validate user permissions
        if creator and not creator.is_admin_or_above():
            raise ValidationError("Only admins can create organizations")
        
        # Validate subscription tier limits
        subscription_tier = data.get('subscription_tier', 'FREE')
        user_limit = data.get('user_limit', 10)
        
        if subscription_tier == 'FREE' and user_limit > 10:
            raise ValidationError("Free tier cannot have more than 10 users")
        
        organization = Organization.objects.create(**data)
        
        # Auto-assign creator as admin if not superadmin
        if creator and not creator.is_superadmin():
            creator.organization = organization
            creator.role = 'ADMIN'
            creator.save(update_fields=['organization', 'role'])
        
        return organization
    
    @staticmethod
    def can_user_join_organization(user, organization):
        """Check if user can join organization"""
        if not organization.is_active:
            return False, "Organization is not active"
        
        if organization.is_at_user_limit:
            return False, "Organization has reached user limit"
        
        if organization.approval_workflow == 'REQUIRES_APPROVAL':
            return False, "Organization requires approval"
        
        return True, "Can join"
    
    @staticmethod
    def get_organization_statistics(organization):
        """Get comprehensive organization statistics"""
        from accounts.models import User
        
        return {
            'total_users': organization.total_users,
            'user_limit': organization.user_limit,
            'users_remaining': max(0, organization.user_limit - organization.total_users),
            'total_departments': organization.total_departments,
            'total_teams': organization.teams.filter(is_active=True).count(),
            'subscription_tier': organization.get_subscription_tier_display(),
            'is_at_limit': organization.is_at_user_limit,
        }
    
    @staticmethod
    def upgrade_subscription(organization, new_tier, upgraded_by):
        """Upgrade organization subscription tier"""
        old_tier = organization.subscription_tier
        organization.subscription_tier = new_tier
        organization.save(update_fields=['subscription_tier'])
        
        # Log subscription change
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=upgraded_by,
            action='SUBSCRIPTION_CHANGE',
            details={
                'organization': str(organization.id),
                'old_tier': old_tier,
                'new_tier': new_tier,
            },
            ip_address=upgraded_by.last_login_ip
        )


class DepartmentService:
    """
    Service layer for Department business logic
    """
    
    @staticmethod
    def create_department(data, creator=None):
        """Create new department with validation"""
        # Validate permissions
        if creator and not creator.is_admin_or_above():
            raise ValidationError("Only admins can create departments")
        
        # Validate hierarchy
        parent = data.get('parent')
        if parent:
            parent_dept = Department.objects.get(id=parent)
            if parent_dept.organization != data.get('organization'):
                raise ValidationError("Parent department must be in same organization")
        
        department = Department.objects.create(**data)
        return department
    
    @staticmethod
    def move_department(department, new_parent, moved_by):
        """Move department to new parent"""
        # Validate no cycles
        current = new_parent
        max_depth = 10  # Prevent infinite loops
        
        for _ in range(max_depth):
            if not current:
                break
            if current.id == department.id:
                raise ValidationError("Cannot create circular hierarchy")
            current = current.parent
        
        department.parent = new_parent
        department.save(update_fields=['parent'])
        
        # Log department move
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=moved_by,
            action='DEPARTMENT_MOVE',
            details={
                'department': str(department.id),
                'old_parent': str(department.parent_id) if department.parent_id else None,
                'new_parent': str(new_parent.id) if new_parent else None,
            },
            ip_address=moved_by.last_login_ip
        )
    
    @staticmethod
    def assign_head(department, new_head, assigned_by):
        """Assign new head to department"""
        # Validate permissions
        if assigned_by and not assigned_by.is_admin_or_above():
            raise ValidationError("Only admins can assign department heads")
        
        # Validate head belongs to organization
        if new_head.organization != department.organization:
            raise ValidationError("Department head must belong to same organization")
        
        old_head = department.head
        department.head = new_head
        department.save(update_fields=['head'])
        
        # Log head assignment
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=assigned_by,
            action='DEPARTMENT_HEAD_CHANGE',
            details={
                'department': str(department.id),
                'old_head': str(old_head.id) if old_head else None,
                'new_head': str(new_head.id),
            },
            ip_address=assigned_by.last_login_ip
        )
    
    @staticmethod
    def get_department_hierarchy(department):
        """Get full department hierarchy"""
        hierarchy = []
        
        def collect_children(dept, level=0):
            hierarchy.append({
                'id': str(dept.id),
                'name': dept.name,
                'level': level,
                'parent_id': str(dept.parent_id) if dept.parent_id else None,
                'total_users': dept.total_users,
                'total_subdepartments': dept.total_subdepartments,
            })
            
            for child in dept.children.filter(is_active=True):
                collect_children(child, level + 1)
        
        collect_children(department)
        return hierarchy


class TeamService:
    """
    Service layer for Team business logic
    """
    
    @staticmethod
    def create_team(data, creator=None):
        """Create new team with validation"""
        # Validate permissions
        if creator and not creator.is_manager_or_above():
            raise ValidationError("Only managers can create teams")
        
        # Validate department belongs to same organization
        department = data.get('department')
        if department:
            dept = Department.objects.get(id=department)
            if dept.organization != data.get('organization'):
                raise ValidationError("Team department must belong to same organization")
        
        team = Team.objects.create(**data)
        return team
    
    @staticmethod
    def assign_lead(team, new_lead, assigned_by):
        """Assign new lead to team"""
        # Validate permissions
        if assigned_by and not assigned_by.is_manager_or_above():
            raise ValidationError("Only managers can assign team leads")
        
        # Validate lead belongs to organization
        if new_lead.organization != team.organization:
            raise ValidationError("Team lead must belong to same organization")
        
        old_lead = team.lead
        team.lead = new_lead
        team.save(update_fields=['lead'])
        
        # Log lead assignment
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=assigned_by,
            action='TEAM_LEAD_CHANGE',
            details={
                'team': str(team.id),
                'old_lead': str(old_lead.id) if old_lead else None,
                'new_lead': str(new_lead.id),
            },
            ip_address=assigned_by.last_login_ip
        )
    
    @staticmethod
    def add_team_member(team, user, role='MEMBER', added_by=None):
        """Add user to team"""
        # Validate permissions
        if added_by and not added_by.is_manager_or_above():
            raise ValidationError("Only managers can add team members")
        
        # Validate user belongs to organization
        if user.organization != team.organization:
            raise ValidationError("User must belong to same organization")
        
        # Create team membership
        membership = TeamMembership.objects.create(
            team=team,
            user=user,
            role=role
        )
        
        # Log member addition
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=added_by,
            action='TEAM_MEMBER_ADD',
            details={
                'team': str(team.id),
                'user': str(user.id),
                'role': role,
            },
            ip_address=added_by.last_login_ip
        )
        
        return membership
    
    @staticmethod
    def remove_team_member(team, user, removed_by=None):
        """Remove user from team"""
        # Validate permissions
        if removed_by and not removed_by.is_manager_or_above():
            raise ValidationError("Only managers can remove team members")
        
        # Delete team membership
        membership = TeamMembership.objects.filter(team=team, user=user).first()
        if membership:
            membership.delete()
            
            # Log member removal
            from audit_logs.models import AuditLog
            AuditLog.objects.create(
                user=removed_by,
                action='TEAM_MEMBER_REMOVE',
                details={
                    'team': str(team.id),
                    'user': str(user.id),
                },
                ip_address=removed_by.last_login_ip
            )
