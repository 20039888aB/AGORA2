from rest_framework import serializers
from .models import Permission, RolePermission, UserPermission, PermissionTemplate


class PermissionSerializer(serializers.ModelSerializer):
    """
    Serializer for Permission model
    """
    resource_type_display = serializers.CharField(source='get_resource_type_display', read_only=True)
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    scope_type_display = serializers.CharField(source='get_scope_type_display', read_only=True)
    
    class Meta:
        model = Permission
        fields = [
            'id', 'name', 'code', 'description', 'resource_type',
            'resource_type_display', 'action_type', 'action_type_display',
            'scope_type', 'scope_type_display', 'conditions',
            'can_create', 'can_read', 'can_update', 'can_delete',
            'can_list', 'can_export', 'can_import', 'can_approve',
            'can_reject', 'can_assign', 'can_unassign', 'can_activate',
            'can_deactivate', 'can_archive', 'can_restore', 'can_manage',
            'can_view', 'can_edit', 'can_share', 'can_download',
            'can_upload', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'full_permission_code']


class RolePermissionSerializer(serializers.ModelSerializer):
    """
    Serializer for RolePermission model
    """
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    permissions_display = serializers.SerializerMethodField()
    
    class Meta:
        model = RolePermission
        fields = [
            'id', 'role', 'role_display', 'description', 'permissions_display',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_permissions_display(self, obj):
        """Get permissions display"""
        permissions = obj.permissions.all()
        return [p.name for p in permissions]


class UserPermissionSerializer(serializers.ModelSerializer):
    """
    Serializer for UserPermission model
    """
    permission_info = serializers.SerializerMethodField()
    granted_by_info = serializers.SerializerMethodField()
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = UserPermission
        fields = [
            'id', 'user', 'permission', 'permission_info', 'scope_object_id',
            'scope_object_type', 'granted_by', 'granted_by_info',
            'granted_at', 'expires_at', 'is_expired', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['granted_at', 'created_at', 'updated_at', 'is_expired']
    
    def get_permission_info(self, obj):
        """Get permission information"""
        permission = obj.permission
        return {
            'id': str(permission.id),
            'name': permission.name,
            'code': permission.code,
            'resource_type': permission.resource_type,
            'action_type': permission.action_type,
        }
    
    def get_granted_by_info(self, obj):
        """Get granted by user information"""
        if obj.granted_by:
            return {
                'id': str(obj.granted_by.id),
                'email': obj.granted_by.email,
                'full_name': obj.granted_by.full_name,
            }
        return None


class PermissionTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for PermissionTemplate model
    """
    resource_type_display = serializers.CharField(source='get_resource_type_display', read_only=True)
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    
    class Meta:
        model = PermissionTemplate
        fields = [
            'id', 'name', 'code', 'description', 'resource_type',
            'resource_type_display', 'action_type', 'action_type_display',
            'default_permissions', 'conditions', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class PermissionGrantSerializer(serializers.Serializer):
    """
    Serializer for granting permissions to users
    """
    user_id = serializers.UUIDField(write_only=True)
    permission_id = serializers.UUIDField(write_only=True)
    scope_object_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    scope_object_type = serializers.CharField(max_length=50, required=False, allow_blank=True)
    expires_days = serializers.IntegerField(default=365, min_value=1, max_value=3650)


class PermissionRevokeSerializer(serializers.Serializer):
    """
    Serializer for revoking permissions from users
    """
    user_permission_id = serializers.UUIDField(write_only=True)


class PermissionTemplateApplySerializer(serializers.Serializer):
    """
    Serializer for applying permission templates to users
    """
    user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True
    )


class UserPermissionCheckSerializer(serializers.Serializer):
    """
    Serializer for checking user permissions
    """
    resource_type = serializers.CharField(max_length=50)
    action_type = serializers.CharField(max_length=50)
    scope_object_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    scope_object_type = serializers.CharField(max_length=50, required=False, allow_blank=True)
