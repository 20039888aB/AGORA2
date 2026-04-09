"""
Organization Service - Centralized Organization Business Logic

This service contains all organization-related business logic that should be used
instead of putting logic directly in models or views.
"""

from django.db import models, transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db.models import Q
import uuid

User = get_user_model()


class OrganizationService:
    """
    Service layer for Organization business logic
    """
    
    @staticmethod
    def create_organization(data, created_by=None):
        """
        Create new organization with validation and business logic
        """
        # Extract and validate required fields
        name = data.get('name')
        description = data.get('description', '')
        domain = data.get('domain', '')
        
        if not name:
            raise ValidationError("Organization name is required")
        
        # Check if organization already exists
        from organizations.models import Organization
        if Organization.objects.filter(name=name).exists():
            raise ValidationError("Organization with this name already exists")
        
        if domain and Organization.objects.filter(domain=domain).exists():
            raise ValidationError("Organization with this domain already exists")
        
        # Create organization
        organization = Organization.objects.create(
            name=name,
            description=description,
            domain=domain,
            logo=data.get('logo', None),
            website=data.get('website', ''),
            phone=data.get('phone', ''),
            address=data.get('address', ''),
            city=data.get('city', ''),
            state=data.get('state', ''),
            country=data.get('country', ''),
            postal_code=data.get('postal_code', ''),
            is_active=data.get('is_active', True),
            settings=data.get('settings', {}),
            metadata=data.get('metadata', {})
        )
        
        # Log organization creation
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=created_by,
            action='ORGANIZATION_CREATE',
            details={
                'organization_id': str(organization.id),
                'name': organization.name,
                'domain': organization.domain
            },
            ip_address=created_by.last_login_ip if created_by else None
        )
        
        return organization
    
    @staticmethod
    def update_organization(organization, data, updated_by=None):
        """
        Update organization with validation and business logic
        """
        # Check if name is being changed and validate uniqueness
        if 'name' in data and data['name'] != organization.name:
            from organizations.models import Organization
            if Organization.objects.filter(name=data['name']).exclude(id=organization.id).exists():
                raise ValidationError("Organization with this name already exists")
        
        # Check if domain is being changed and validate uniqueness
        if 'domain' in data and data['domain'] != organization.domain:
            from organizations.models import Organization
            if data['domain'] and Organization.objects.filter(domain=data['domain']).exclude(id=organization.id).exists():
                raise ValidationError("Organization with this domain already exists")
        
        # Update organization fields
        for field, value in data.items():
            if hasattr(organization, field) and field not in ['id']:
                setattr(organization, field, value)
        
        organization.save()
        
        # Log organization update
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=updated_by,
            action='ORGANIZATION_UPDATE',
            details={
                'organization_id': str(organization.id),
                'name': organization.name,
                'updated_fields': list(data.keys())
            },
            ip_address=updated_by.last_login_ip if updated_by else None
        )
        
        return organization
    
    @staticmethod
    def deactivate_organization(organization, deactivated_by=None):
        """
        Deactivate organization
        """
        if not organization.is_active:
            raise ValidationError("Organization is already inactive")
        
        organization.is_active = False
        organization.save(update_fields=['is_active'])
        
        # Log organization deactivation
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=deactivated_by,
            action='ORGANIZATION_DEACTIVATE',
            details={
                'organization_id': str(organization.id),
                'name': organization.name
            },
            ip_address=deactivated_by.last_login_ip if deactivated_by else None
        )
        
        return organization
    
    @staticmethod
    def activate_organization(organization, activated_by=None):
        """
        Activate organization
        """
        if organization.is_active:
            raise ValidationError("Organization is already active")
        
        organization.is_active = True
        organization.save(update_fields=['is_active'])
        
        # Log organization activation
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=activated_by,
            action='ORGANIZATION_ACTIVATE',
            details={
                'organization_id': str(organization.id),
                'name': organization.name
            },
            ip_address=activated_by.last_login_ip if activated_by else None
        )
        
        return organization
    
    @staticmethod
    def create_department(organization, data, created_by=None):
        """
        Create new department
        """
        from organizations.models import Department
        
        # Validate required fields
        name = data.get('name')
        if not name:
            raise ValidationError("Department name is required")
        
        # Check if department already exists in organization
        if Department.objects.filter(organization=organization, name=name).exists():
            raise ValidationError("Department with this name already exists in this organization")
        
        # Create department
        department = Department.objects.create(
            organization=organization,
            name=name,
            description=data.get('description', ''),
            parent=data.get('parent', None),
            manager=data.get('manager', None),
            is_active=data.get('is_active', True)
        )
        
        # Log department creation
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=created_by,
            action='DEPARTMENT_CREATE',
            details={
                'department_id': str(department.id),
                'name': department.name,
                'organization_id': str(organization.id)
            },
            ip_address=created_by.last_login_ip if created_by else None
        )
        
        return department
    
    @staticmethod
    def create_team(organization, data, created_by=None):
        """
        Create new team
        """
        from organizations.models import Team
        
        # Validate required fields
        name = data.get('name')
        if not name:
            raise ValidationError("Team name is required")
        
        # Create team
        team = Team.objects.create(
            organization=organization,
            name=name,
            description=data.get('description', ''),
            leader=data.get('leader', None),
            department=data.get('department', None),
            is_active=data.get('is_active', True)
        )
        
        # Log team creation
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=created_by,
            action='TEAM_CREATE',
            details={
                'team_id': str(team.id),
                'name': team.name,
                'organization_id': str(organization.id)
            },
            ip_address=created_by.last_login_ip if created_by else None
        )
        
        return team
    
    @staticmethod
    def add_user_to_department(user, department, role='MEMBER', added_by=None):
        """
        Add user to department
        """
        from organizations.models import DepartmentMembership
        
        # Check if user is already in department
        if DepartmentMembership.objects.filter(user=user, department=department).exists():
            raise ValidationError("User is already a member of this department")
        
        # Validate user belongs to same organization
        if user.organization != department.organization:
            raise ValidationError("User must belong to same organization as department")
        
        # Create department membership
        membership = DepartmentMembership.objects.create(
            user=user,
            department=department,
            role=role,
            joined_at=timezone.now()
        )
        
        # Log department membership
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=added_by,
            action='DEPARTMENT_MEMBER_ADD',
            details={
                'user_id': str(user.id),
                'department_id': str(department.id),
                'role': role
            },
            ip_address=added_by.last_login_ip if added_by else None
        )
        
        return membership
    
    @staticmethod
    def add_user_to_team(user, team, role='MEMBER', added_by=None):
        """
        Add user to team
        """
        from organizations.models import TeamMembership
        
        # Check if user is already in team
        if TeamMembership.objects.filter(user=user, team=team).exists():
            raise ValidationError("User is already a member of this team")
        
        # Validate user belongs to same organization
        if user.organization != team.organization:
            raise ValidationError("User must belong to same organization as team")
        
        # Create team membership
        membership = TeamMembership.objects.create(
            user=user,
            team=team,
            role=role,
            joined_at=timezone.now()
        )
        
        # Log team membership
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=added_by,
            action='TEAM_MEMBER_ADD',
            details={
                'user_id': str(user.id),
                'team_id': str(team.id),
                'role': role
            },
            ip_address=added_by.last_login_ip if added_by else None
        )
        
        return membership
    
    @staticmethod
    def get_organization_statistics(organization):
        """
        Get organization statistics
        """
        users = User.objects.filter(organization=organization, is_deleted=False)
        
        from organizations.models import Department, Team
        departments = Department.objects.filter(organization=organization, is_active=True)
        teams = Team.objects.filter(organization=organization, is_active=True)
        
        from courses.models import Course
        courses = Course.objects.filter(organization=organization, is_active=True)
        
        from enrollments.models import Enrollment
        enrollments = Enrollment.objects.filter(course__organization=organization, is_active=True)
        
        return {
            'total_users': users.count(),
            'active_users': users.filter(is_active=True).count(),
            'total_departments': departments.count(),
            'active_departments': departments.filter(is_active=True).count(),
            'total_teams': teams.count(),
            'active_teams': teams.filter(is_active=True).count(),
            'total_courses': courses.count(),
            'published_courses': courses.filter(is_published=True).count(),
            'total_enrollments': enrollments.count(),
            'active_enrollments': enrollments.filter(status='ACTIVE').count(),
            'completed_enrollments': enrollments.filter(status='COMPLETED').count(),
        }
    
    @staticmethod
    def get_organization_users(organization, role=None, department=None, team=None):
        """
        Get organization users with optional filters
        """
        users = User.objects.filter(organization=organization, is_deleted=False)
        
        if role:
            users = users.filter(role=role)
        
        if department:
            from organizations.models import DepartmentMembership
            user_ids = DepartmentMembership.objects.filter(
                department=department
            ).values_list('user_id', flat=True)
            users = users.filter(id__in=user_ids)
        
        if team:
            from organizations.models import TeamMembership
            user_ids = TeamMembership.objects.filter(
                team=team
            ).values_list('user_id', flat=True)
            users = users.filter(id__in=user_ids)
        
        return users
    
    @staticmethod
    def get_department_hierarchy(organization):
        """
        Get department hierarchy for organization
        """
        from organizations.models import Department
        
        departments = Department.objects.filter(
            organization=organization,
            is_active=True
        ).order_by('name')
        
        # Build hierarchy
        hierarchy = {}
        root_departments = []
        
        for dept in departments:
            dept_data = {
                'id': str(dept.id),
                'name': dept.name,
                'description': dept.description,
                'parent_id': str(dept.parent.id) if dept.parent else None,
                'manager_id': str(dept.manager.id) if dept.manager else None,
                'total_members': dept.total_members,
                'children': []
            }
            
            if dept.parent:
                if str(dept.parent.id) not in hierarchy:
                    hierarchy[str(dept.parent.id)] = []
                hierarchy[str(dept.parent.id)].append(dept_data)
            else:
                root_departments.append(dept_data)
        
        # Build tree structure
        def build_tree(items):
            for item in items:
                item_id = item['id']
                if item_id in hierarchy:
                    item['children'] = build_tree(hierarchy[item_id])
            return items
        
        return build_tree(root_departments)
    
    @staticmethod
    def search_organizations(query):
        """
        Search organizations by name or domain
        """
        from organizations.models import Organization
        
        organizations = Organization.objects.filter(
            Q(name__icontains=query) |
            Q(domain__icontains=query)
        )
        
        return organizations
    
    @staticmethod
    def validate_organization_access(user, organization):
        """
        Validate if user has access to organization
        """
        if user.is_superadmin():
            return True
        
        return user.organization == organization
    
    @staticmethod
    def get_user_organizations(user):
        """
        Get organizations accessible to user
        """
        if user.is_superadmin():
            from organizations.models import Organization
            return Organization.objects.all()
        
        if user.organization:
            return [user.organization]
        
        return []
