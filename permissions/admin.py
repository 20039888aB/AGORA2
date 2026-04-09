from django.contrib import admin
from .models import Permission, RolePermission, UserPermission, PermissionTemplate


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'code', 'resource_type', 'action_type', 'scope_type',
        'is_active', 'created_at'
    ]
    list_filter = [
        'resource_type', 'action_type', 'scope_type', 'is_active', 'created_at'
    ]
    search_fields = ['name', 'description', 'code']
    ordering = ['resource_type', 'action_type', 'name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = [
        'role', 'permissions_display', 'is_active', 'created_at'
    ]
    list_filter = [
        'role', 'is_active', 'created_at'
    ]
    search_fields = ['role', 'description']
    ordering = ['role', 'created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    def permissions_display(self, obj):
        return ", ".join([p.name for p in obj.permissions.all()])
    permissions_display.short_description = 'Permissions'


@admin.register(UserPermission)
class UserPermissionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'permission', 'scope_object_id', 'scope_object_type',
        'granted_by', 'granted_at', 'expires_at', 'is_active'
    ]
    list_filter = [
        'permission', 'user', 'is_active', 'granted_at', 'expires_at'
    ]
    search_fields = ['user__email', 'permission__name', 'scope_object_id']
    ordering = ['-granted_at']
    readonly_fields = ['granted_at', 'created_at', 'updated_at']


@admin.register(PermissionTemplate)
class PermissionTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'code', 'resource_type', 'action_type', 'is_active', 'created_at'
    ]
    list_filter = [
        'resource_type', 'action_type', 'is_active', 'created_at'
    ]
    search_fields = ['name', 'description', 'code']
    ordering = ['resource_type', 'action_type', 'name']
    readonly_fields = ['created_at', 'updated_at']
