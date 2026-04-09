from django.db import models
from django.contrib.auth import get_user_model
import uuid


User = get_user_model()


class Permission(models.Model):
    """
    Base permission model for granular access control
    """
    
    RESOURCE_TYPES = [
        ('ORGANIZATION', 'Organization'),
        ('DEPARTMENT', 'Department'),
        ('TEAM', 'Team'),
        ('COURSE', 'Course'),
        ('MODULE', 'Module'),
        ('LESSON', 'Lesson'),
        ('ASSIGNMENT', 'Assignment'),
        ('ENROLLMENT', 'Enrollment'),
        ('CERTIFICATE', 'Certificate'),
        ('QUIZ', 'Quiz'),
        ('REPORT', 'Report'),
        ('USER', 'User'),
        ('ROLE_REQUEST', 'Role Request'),
        ('NOTIFICATION', 'Notification'),
        ('AUDIT_LOG', 'Audit Log'),
    ]
    
    ACTION_TYPES = [
        ('CREATE', 'Create'),
        ('READ', 'Read'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LIST', 'List'),
        ('EXPORT', 'Export'),
        ('IMPORT', 'Import'),
        ('APPROVE', 'Approve'),
        ('REJECT', 'Reject'),
        ('ASSIGN', 'Assign'),
        ('UNASSIGN', 'Unassign'),
        ('ACTIVATE', 'Activate'),
        ('DEACTIVATE', 'Deactivate'),
        ('ARCHIVE', 'Archive'),
        ('RESTORE', 'Restore'),
        ('MANAGE', 'Manage'),
        ('VIEW', 'View'),
        ('EDIT', 'Edit'),
        ('SHARE', 'Share'),
        ('DOWNLOAD', 'Download'),
        ('UPLOAD', 'Upload'),
    ]
    
    SCOPE_TYPES = [
        ('GLOBAL', 'Global'),
        ('ORGANIZATION', 'Organization'),
        ('DEPARTMENT', 'Department'),
        ('TEAM', 'Team'),
        ('PERSONAL', 'Personal'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, db_index=True)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.TextField(blank=True)
    resource_type = models.CharField(
        max_length=50,
        choices=RESOURCE_TYPES,
        db_index=True
    )
    action_type = models.CharField(
        max_length=50,
        choices=ACTION_TYPES,
        db_index=True
    )
    scope_type = models.CharField(
        max_length=50,
        choices=SCOPE_TYPES,
        default='ORGANIZATION',
        db_index=True
    )
    
    # Permission flags
    can_create = models.BooleanField(default=False)
    can_read = models.BooleanField(default=False)
    can_update = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    can_list = models.BooleanField(default=False)
    can_export = models.BooleanField(default=False)
    can_import = models.BooleanField(default=False)
    can_approve = models.BooleanField(default=False)
    can_reject = models.BooleanField(default=False)
    can_assign = models.BooleanField(default=False)
    can_unassign = models.BooleanField(default=False)
    can_activate = models.BooleanField(default=False)
    can_deactivate = models.BooleanField(default=False)
    can_archive = models.BooleanField(default=False)
    can_restore = models.BooleanField(default=False)
    can_manage = models.BooleanField(default=False)
    can_view = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_share = models.BooleanField(default=False)
    can_download = models.BooleanField(default=False)
    can_upload = models.BooleanField(default=False)
    
    # Conditions
    conditions = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'permissions'
        verbose_name = 'Permission'
        verbose_name_plural = 'Permissions'
        constraints = [
            models.UniqueConstraint(
                fields=['code'],
                name='unique_permission_code'
            ),
        ]
        indexes = [
            models.Index(fields=['resource_type', 'action_type']),
            models.Index(fields=['scope_type', 'is_active']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['resource_type', 'action_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    @property
    def full_permission_code(self):
        """Get full permission code with resource and action"""
        return f"{self.resource_type}_{self.action_type}"
    
    def check_permission(self, user, resource_type=None, action_type=None, scope_object=None):
        """Check if user has specific permission"""
        if not self.is_active:
            return False
        
        # Check resource type
        if resource_type and self.resource_type != resource_type:
            return False
        
        # Check action type
        if action_type and self.action_type != action_type:
            return False
        
        # Check conditions
        if self.conditions:
            for condition in self.conditions:
                if not self._evaluate_condition(condition, user, scope_object):
                    return False
        
        # Check permission flags
        action_map = {
            'create': self.can_create,
            'read': self.can_read,
            'update': self.can_update,
            'delete': self.can_delete,
            'list': self.can_list,
            'export': self.can_export,
            'import': self.can_import,
            'approve': self.can_approve,
            'reject': self.can_reject,
            'assign': self.can_assign,
            'unassign': self.can_unassign,
            'activate': self.can_activate,
            'deactivate': self.can_deactivate,
            'archive': self.can_archive,
            'restore': self.can_restore,
            'manage': self.can_manage,
            'view': self.can_view,
            'edit': self.can_edit,
            'share': self.can_share,
            'download': self.can_download,
            'upload': self.can_upload,
        }
        
        required_permission = action_map.get(action_type, False)
        return required_permission
    
    def _evaluate_condition(self, condition, user, scope_object):
        """Evaluate permission condition"""
        condition_type = condition.get('type')
        condition_value = condition.get('value')
        
        if condition_type == 'role':
            return user.role == condition_value
        elif condition_type == 'is_active':
            return user.is_active == condition_value
        elif condition_type == 'organization_member':
            return user.organization and user.organization.id == condition_value
        elif condition_type == 'department_member':
            return user.profile.department and user.profile.department.id == condition_value
        elif condition_type == 'team_member':
            return user.profile.team and user.profile.team.id == condition_value
        elif condition_type == 'user_id':
            return str(user.id) == condition_value
        
        return False


class RolePermission(models.Model):
    """
    Role-based permissions with hierarchy
    """
    
    ROLE_CHOICES = [
        ('SUPERADMIN', 'Super Admin'),
        ('ADMIN', 'Admin'),
        ('MANAGER', 'Manager'),
        ('STUDENT', 'Student'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        unique=True,
        db_index=True
    )
    permissions = models.ManyToManyField(
        Permission,
        related_name='role_permissions',
        blank=True,
        db_index=True
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'role_permissions'
        verbose_name = 'Role Permission'
        verbose_name_plural = 'Role Permissions'
        constraints = [
            models.UniqueConstraint(
                fields=['role'],
                name='unique_role_permission'
            ),
        ]
        indexes = [
            models.Index(fields=['role', 'is_active']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['role']
    
    def __str__(self):
        return f"{self.role} Permissions"
    
    def has_permission(self, user, resource_type, action_type):
        """Check if role has specific permission"""
        if not self.is_active:
            return False
        
        return self.permissions.filter(
            resource_type=resource_type,
            action_type=action_type,
            is_active=True
        ).exists()


class UserPermission(models.Model):
    """
    User-specific permissions for granular access control
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='custom_permissions',
        db_index=True
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name='user_permission_grants',
        db_index=True
    )
    scope_object_id = models.CharField(max_length=100, blank=True, db_index=True)
    scope_object_type = models.CharField(max_length=50, blank=True, db_index=True)
    granted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_permissions',
        db_index=True
    )
    granted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_permissions'
        verbose_name = 'User Permission'
        verbose_name_plural = 'User Permissions'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'permission'],
                name='unique_user_permission'
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'permission']),
            models.Index(fields=['granted_by']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['is_active']),
            models.Index(fields=['granted_at']),
        ]
        ordering = ['-granted_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.permission.name}"
    
    @property
    def is_expired(self):
        """Check if permission is expired"""
        if not self.expires_at:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    def is_valid(self, user):
        """Check if permission is valid for user"""
        if not self.is_active or self.is_expired:
            return False
        return True


class PermissionTemplate(models.Model):
    """
    Reusable permission templates for quick setup
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, db_index=True)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.TextField(blank=True)
    resource_type = models.CharField(
        max_length=50,
        choices=Permission.RESOURCE_TYPES,
        db_index=True
    )
    action_type = models.CharField(
        max_length=50,
        choices=Permission.ACTION_TYPES,
        db_index=True
    )
    default_permissions = models.JSONField(default=dict, blank=True)
    conditions = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'permission_templates'
        verbose_name = 'Permission Template'
        verbose_name_plural = 'Permission Templates'
        constraints = [
            models.UniqueConstraint(
                fields=['code'],
                name='unique_permission_template_code'
            ),
        ]
        indexes = [
            models.Index(fields=['resource_type', 'action_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['resource_type', 'action_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"
