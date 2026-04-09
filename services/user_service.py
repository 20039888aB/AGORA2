"""
User Service - Centralized User Business Logic

This service contains all user-related business logic that should be used
instead of putting logic directly in models or views.
"""

from django.db import models, transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db.models import Q
import uuid

User = get_user_model()


class UserService:
    """
    Service layer for User business logic
    """
    
    @staticmethod
    def create_user(data, created_by=None):
        """
        Create new user with validation and business logic
        """
        # Extract and validate required fields
        email = data.get('email')
        password = data.get('password')
        role = data.get('role')
        organization = data.get('organization')
        
        # Validate required fields
        if not email:
            raise ValidationError("Email is required")
        if not password:
            raise ValidationError("Password is required")
        if not role:
            raise ValidationError("Role is required")
        
        # Validate role
        valid_roles = [choice[0] for choice in User.ROLE_CHOICES]
        if role not in valid_roles:
            raise ValidationError(f"Role must be one of: {valid_roles}")
        
        # Validate organization for non-superadmin users
        if role != 'SUPERADMIN' and not organization:
            raise ValidationError("Organization is required for non-superadmin users")
        
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            raise ValidationError("User with this email already exists")
        
        # Validate managed_by relationship if provided
        managed_by = data.get('managed_by')
        if managed_by and managed_by.role not in ['MANAGER', 'ADMIN', 'SUPERADMIN']:
            raise ValidationError("Manager must have a managerial role")
        
        # Create user
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            role=role,
            organization=organization,
            managed_by=managed_by,
            phone=data.get('phone', ''),
            address=data.get('address', ''),
            bio=data.get('bio', ''),
            avatar=data.get('avatar', None),
            is_active=data.get('is_active', True)
        )
        
        # Create user profile
        from accounts.models import UserProfile
        UserProfile.objects.create(
            user=user,
            employee_id=data.get('employee_id', ''),
            department=data.get('department', ''),
            position=data.get('position', ''),
            hire_date=data.get('hire_date', None),
            salary=data.get('salary', 0),
            skills=data.get('skills', []),
            certifications=data.get('certifications', [])
        )
        
        # Log user creation
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=created_by,
            action='USER_CREATE',
            details={
                'user_id': str(user.id),
                'email': user.email,
                'role': user.role,
                'organization': str(organization.id) if organization else None
            },
            ip_address=created_by.last_login_ip if created_by else None
        )
        
        return user
    
    @staticmethod
    def update_user(user, data, updated_by=None):
        """
        Update user with validation and business logic
        """
        # Validate role change
        if 'role' in data and data['role'] != user.role:
            # Validate new role
            valid_roles = [choice[0] for choice in User.ROLE_CHOICES]
            if data['role'] not in valid_roles:
                raise ValidationError(f"Role must be one of: {valid_roles}")
            
            # Validate organization for non-superadmin users
            if data['role'] != 'SUPERADMIN' and not user.organization:
                raise ValidationError("Organization is required for non-superadmin users")
        
        # Validate managed_by relationship
        if 'managed_by' in data and data['managed_by']:
            if data['managed_by'].role not in ['MANAGER', 'ADMIN', 'SUPERADMIN']:
                raise ValidationError("Manager must have a managerial role")
        
        # Update user fields
        for field, value in data.items():
            if hasattr(user, field) and field not in ['id', 'password']:
                setattr(user, field, value)
        
        # Handle password change
        if 'password' in data and data['password']:
            user.password = make_password(data['password'])
        
        user.save()
        
        # Update user profile if provided
        profile_fields = ['employee_id', 'department', 'position', 'hire_date', 'salary', 'skills', 'certifications']
        profile_data = {k: v for k, v in data.items() if k in profile_fields}
        
        if profile_data:
            profile = user.profile
            for field, value in profile_data.items():
                setattr(profile, field, value)
            profile.save()
        
        # Log user update
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=updated_by,
            action='USER_UPDATE',
            details={
                'user_id': str(user.id),
                'email': user.email,
                'updated_fields': list(data.keys())
            },
            ip_address=updated_by.last_login_ip if updated_by else None
        )
        
        return user
    
    @staticmethod
    def soft_delete_user(user, deleted_by=None):
        """
        Soft delete user with business logic
        """
        if user.is_deleted:
            raise ValidationError("User is already deleted")
        
        # Store original email
        original_email = user.email
        
        # Soft delete
        user.is_deleted = True
        user.is_active = False
        user.email = f"deleted_{uuid.uuid4().hex[:8]}_{original_email}"
        user.deleted_at = timezone.now()
        user.save(update_fields=['is_deleted', 'is_active', 'email', 'deleted_at'])
        
        # Log user deletion
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=deleted_by,
            action='USER_DELETE',
            details={
                'user_id': str(user.id),
                'original_email': original_email
            },
            ip_address=deleted_by.last_login_ip if deleted_by else None
        )
        
        return user
    
    @staticmethod
    def restore_user(user, restored_by=None):
        """
        Restore soft deleted user
        """
        if not user.is_deleted:
            raise ValidationError("User is not deleted")
        
        # Restore email
        original_email = user.email
        if original_email.startswith('deleted_'):
            # Extract original email from deleted format
            parts = original_email.split('_', 2)
            if len(parts) >= 3:
                original_email = parts[2]
        
        # Restore user
        user.is_deleted = False
        user.is_active = True
        user.email = original_email
        user.deleted_at = None
        user.save(update_fields=['is_deleted', 'is_active', 'email', 'deleted_at'])
        
        # Log user restoration
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=restored_by,
            action='USER_RESTORE',
            details={
                'user_id': str(user.id),
                'email': user.email
            },
            ip_address=restored_by.last_login_ip if restored_by else None
        )
        
        return user
    
    @staticmethod
    def change_user_role(user, new_role, changed_by=None):
        """
        Change user role with validation and business logic
        """
        if new_role == user.role:
            raise ValidationError("User already has this role")
        
        # Validate new role
        valid_roles = [choice[0] for choice in User.ROLE_CHOICES]
        if new_role not in valid_roles:
            raise ValidationError(f"Role must be one of: {valid_roles}")
        
        # Store old role for logging
        old_role = user.role
        
        # Update role
        user.role = new_role
        user.role_update_count = (user.role_update_count or 0) + 1
        user.role_updated_at = timezone.now()
        user.save(update_fields=['role', 'role_update_count', 'role_updated_at'])
        
        # Log role change
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=changed_by,
            action='USER_ROLE_CHANGE',
            details={
                'user_id': str(user.id),
                'email': user.email,
                'old_role': old_role,
                'new_role': new_role,
                'update_count': user.role_update_count
            },
            ip_address=changed_by.last_login_ip if changed_by else None
        )
        
        # Send signal for role change
        from accounts.signals import post_role_change
        post_role_change.send(
            sender=User,
            user=user,
            old_role=old_role,
            new_role=new_role,
            changed_by=changed_by
        )
        
        return user
    
    @staticmethod
    def get_user_statistics(organization=None):
        """
        Get user statistics
        """
        users = User.objects.filter(is_deleted=False)
        
        if organization:
            users = users.filter(organization=organization)
        
        return {
            'total_users': users.count(),
            'active_users': users.filter(is_active=True).count(),
            'inactive_users': users.filter(is_active=False).count(),
            'superadmins': users.filter(role='SUPERADMIN').count(),
            'admins': users.filter(role='ADMIN').count(),
            'managers': users.filter(role='MANAGER').count(),
            'students': users.filter(role='STUDENT').count(),
            'users_created_this_month': users.filter(
                created_at__gte=timezone.now() - timezone.timedelta(days=30)
            ).count(),
            'users_created_this_year': users.filter(
                created_at__gte=timezone.now() - timezone.timedelta(days=365)
            ).count(),
        }
    
    @staticmethod
    def get_users_by_role(role, organization=None):
        """
        Get users by role
        """
        users = User.objects.filter(role=role, is_deleted=False, is_active=True)
        
        if organization:
            users = users.filter(organization=organization)
        
        return users
    
    @staticmethod
    def get_managed_users(manager, organization=None):
        """
        Get users managed by a manager
        """
        users = User.objects.filter(
            managed_by=manager,
            is_deleted=False,
            is_active=True
        )
        
        if organization:
            users = users.filter(organization=organization)
        
        return users
    
    @staticmethod
    def search_users(query, organization=None, role=None):
        """
        Search users by email, first name, or last name
        """
        users = User.objects.filter(is_deleted=False)
        
        if organization:
            users = users.filter(organization=organization)
        
        if role:
            users = users.filter(role=role)
        
        if query:
            users = users.filter(
                Q(email__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query)
            )
        
        return users.distinct()
    
    @staticmethod
    def validate_user_permissions(user, resource_type, action_type, scope_object=None):
        """
        Validate user permissions using the permissions system
        """
        return user.has_permission(resource_type, action_type, scope_object)
    
    @staticmethod
    def get_user_enrollments(user, status=None):
        """
        Get user enrollments
        """
        from enrollments.models import Enrollment
        enrollments = Enrollment.objects.filter(user=user, is_active=True)
        
        if status:
            enrollments = enrollments.filter(status=status)
        
        return enrollments
    
    @staticmethod
    def get_user_certificates(user, status=None):
        """
        Get user certificates
        """
        from certificates.models import Certificate
        certificates = Certificate.objects.filter(user=user)
        
        if status:
            certificates = certificates.filter(status=status)
        
        return certificates
    
    @staticmethod
    def get_user_assignments(user, status=None):
        """
        Get user assignments
        """
        from assignments.models import AssignmentSubmission
        submissions = AssignmentSubmission.objects.filter(student=user, is_active=True)
        
        if status:
            submissions = submissions.filter(status=status)
        
        return submissions
    
    @staticmethod
    def update_last_login(user, ip_address=None):
        """
        Update user last login information
        """
        user.last_login = timezone.now()
        user.last_login_ip = ip_address
        user.login_count = (user.login_count or 0) + 1
        user.save(update_fields=['last_login', 'last_login_ip', 'login_count'])
        
        # Log login
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=user,
            action='USER_LOGIN',
            details={
                'ip_address': ip_address,
                'login_count': user.login_count
            },
            ip_address=ip_address
        )
