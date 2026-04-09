from django.db import models, transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Permission, RolePermission, UserPermission, PermissionTemplate


class PermissionService:
    """
    Service layer for permission management
    """
    
    @staticmethod
    def create_permission(data, creator=None):
        """Create new permission with validation"""
        # Validate permissions
        if creator and not creator.is_superadmin():
            raise ValidationError("Only superadmins can create permissions")
        
        # Validate permission combination
        permission = Permission.objects.create(**data)
        
        # Log permission creation
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=creator,
            action='PERMISSION_CREATE',
            details={
                'permission': str(permission.id),
                'resource_type': permission.resource_type,
                'action_type': permission.action_type,
            },
            ip_address=creator.last_login_ip
        )
        
        return permission
    
    @staticmethod
    def create_role_permission(data, creator=None):
        """Create role-based permission"""
        # Validate permissions
        if creator and not creator.is_superadmin():
            raise ValidationError("Only superadmins can create role permissions")
        
        role_permission = RolePermission.objects.create(**data)
        
        # Log role permission creation
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=creator,
            action='ROLE_PERMISSION_CREATE',
            details={
                'role': role_permission.role,
                'permissions': list(role_permission.permissions.values_list('code')),
            },
            ip_address=creator.last_login_ip
        )
        
        return role_permission
    
    @staticmethod
    def grant_user_permission(user, permission, scope_object_id=None, scope_object_type=None, granted_by=None):
        """Grant permission to user"""
        # Validate permission exists and is active
        if not permission.is_active:
            raise ValidationError("Permission is not active")
        
        # Check if user already has this permission
        existing_permission = UserPermission.objects.filter(
            user=user,
            permission=permission,
            is_active=True
        ).first()
        
        if existing_permission:
            # Update existing permission
            existing_permission.scope_object_id = scope_object_id
            existing_permission.scope_object_type = scope_object_type
            existing_permission.granted_by = granted_by
            existing_permission.expires_at = timezone.now() + timezone.timedelta(days=365)  # 1 year
            existing_permission.save()
        else:
            # Create new permission
            UserPermission.objects.create(
                user=user,
                permission=permission,
                scope_object_id=scope_object_id,
                scope_object_type=scope_object_type,
                granted_by=granted_by,
                expires_at=timezone.now() + timezone.timedelta(days=365)  # 1 year
            )
        
        # Log permission grant
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=granted_by or user,
            action='USER_PERMISSION_GRANT',
            details={
                'target_user': str(user.id),
                'permission': str(permission.id),
                'scope_object_id': scope_object_id,
                'scope_object_type': scope_object_type,
            },
            ip_address=(granted_by or user).last_login_ip
        )
    
    @staticmethod
    def revoke_user_permission(user_permission, revoked_by=None):
        """Revoke user permission"""
        user_permission.is_active = False
        user_permission.save()
        
        # Log permission revocation
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=revoked_by,
            action='USER_PERMISSION_REVOKE',
            details={
                'target_user': str(user_permission.user.id),
                'permission': str(user_permission.permission.id),
            },
            ip_address=revoked_by.last_login_ip
        )
    
    @staticmethod
    def check_user_permission(user, resource_type, action_type, scope_object_id=None, scope_object_type=None):
        """Check if user has specific permission"""
        # Check direct user permissions
        user_permissions = UserPermission.objects.filter(
            user=user,
            permission__resource_type=resource_type,
            permission__action_type=action_type,
            is_active=True
        )
        
        # Apply scope filtering
        if scope_object_id:
            user_permissions = user_permissions.filter(
                scope_object_id=scope_object_id,
                scope_object_type=scope_object_type
            )
        
        # Check role-based permissions
        user_role_permissions = RolePermission.objects.filter(
            role=user.role,
            permission__resource_type=resource_type,
            permission__action_type=action_type,
            is_active=True
        )
        
        # Convert to permission objects and check conditions
        for userPermission in user_permissions:
            permission = UserPermission.permission
            if permission.check_permission(user, resource_type, action_type):
                return True
        
        for role_permission in user_role_permissions:
            permission = role_permission.permission
            if permission.check_permission(user, resource_type, action_type):
                return True
        
        return False
    
    @staticmethod
    def get_user_permissions(user):
        """Get all active permissions for user"""
        user_permissions = UserPermission.objects.filter(
            user=user,
            is_active=True
        ).select_related('permission')
        
        permissions = []
        for userPermission in user_permissions:
            permission = UserPermission.permission
            permissions.append({
                'id': str(permission.id),
                'name': permission.name,
                'code': permission.code,
                'resource_type': permission.resource_type,
                'action_type': permission.action_type,
                'scope_object_id': UserPermission.scope_object_id,
                'scope_object_type': UserPermission.scope_object_type,
                'granted_at': UserPermission.granted_at,
                'expires_at': UserPermission.expires_at,
                'granted_by': UserPermission.granted_by.email if UserPermission.granted_by else None,
            })
        
        return permissions
    
    @staticmethod
    def create_permission_template(data, creator=None):
        """Create permission template"""
        # Validate permissions
        if creator and not creator.is_superadmin():
            raise ValidationError("Only superadmins can create permission templates")
        
        template = PermissionTemplate.objects.create(**data)
        
        # Log template creation
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=creator,
            action='PERMISSION_TEMPLATE_CREATE',
            details={
                'template': str(template.id),
                'name': template.name,
                'code': template.code,
            },
            ip_address=creator.last_login_ip
        )
        
        return template
    
    @staticmethod
    def apply_permission_template(template, users, granted_by=None):
        """Apply permission template to multiple users"""
        permissions_created = []
        
        with transaction.atomic():
            for userPermission in template.default_permissions.items():
                permission = Permission.objects.get(
                    resource_type=UserPermission['resource_type'],
                    action_type=UserPermission['action_type']
                )
                
                for user in users:
                    PermissionService.grant_user_permission(
                        user=user,
                        permission=permission,
                        granted_by=granted_by
                    )
                    permissions_created.append(str(permission.id))
        
        # Log bulk permission grant
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=granted_by,
            action='BULK_PERMISSION_GRANT',
            details={
                'template': str(template.id),
                'users': [str(user.id) for user in users],
                'permissions': permissions_created,
            },
            ip_address=granted_by.last_login_ip
        )
        
        return permissions_created
    
    @staticmethod
    def cleanup_expired_permissions():
        """Clean up expired permissions"""
        from django.utils import timezone
        expired_permissions = UserPermission.objects.filter(
            expires_at__lt=timezone.now(),
            is_active=True
        )
        
        count = expired_permissions.count()
        expired_permissions.update(is_active=False)
        
        # Log cleanup
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=None,  # System action
            action='PERMISSION_CLEANUP',
            details={
                'expired_permissions': count,
            },
        )
        
        return count
