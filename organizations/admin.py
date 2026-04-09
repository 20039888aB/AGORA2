from django.contrib import admin
from django.utils.html import format_html
from .models import Organization, Department, Team, DepartmentMembership, TeamMembership


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'subscription_tier', 'user_limit', 'total_users',
        'is_active', 'created_at'
    ]
    list_filter = [
        'subscription_tier', 'is_active', 'created_at'
    ]
    search_fields = ['name', 'description', 'email']
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'logo')
        }),
        ('Contact', {
            'fields': ('website', 'email', 'phone', 'address')
        }),
        ('Subscription', {
            'fields': ('subscription_tier', 'user_limit', 'approval_workflow')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def total_users(self, obj):
        return obj.total_users
    
    def total_departments(self, obj):
        return obj.total_departments


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'organization', 'parent', 'head', 'total_users',
        'total_subdepartments', 'is_active', 'created_at'
    ]
    list_filter = [
        'organization', 'is_active', 'created_at'
    ]
    search_fields = ['name', 'description']
    ordering = ['organization', 'name']
    readonly_fields = ['created_at', 'updated_at', 'total_users', 'total_subdepartments']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description')
        }),
        ('Organization', {
            'fields': ('organization',)
        }),
        ('Hierarchy', {
            'fields': ('parent', 'head')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def total_users(self, obj):
        return obj.total_users
    
    def total_subdepartments(self, obj):
        return obj.total_subdepartments


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'organization', 'department', 'lead', 'total_members',
        'is_active', 'created_at'
    ]
    list_filter = [
        'organization', 'department', 'is_active', 'created_at'
    ]
    search_fields = ['name', 'description']
    ordering = ['organization', 'department', 'name']
    readonly_fields = ['created_at', 'updated_at', 'total_members']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description')
        }),
        ('Organization', {
            'fields': ('organization', 'department')
        }),
        ('Leadership', {
            'fields': ('lead',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def total_members(self, obj):
        return obj.total_members


@admin.register(DepartmentMembership)
class DepartmentMembershipAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'department', 'role', 'joined_at'
    ]
    list_filter = [
        'department', 'role', 'joined_at'
    ]
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    ordering = ['-joined_at']
    readonly_fields = ['joined_at', 'updated_at']


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'team', 'role', 'joined_at'
    ]
    list_filter = [
        'team', 'role', 'joined_at'
    ]
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    ordering = ['-joined_at']
    readonly_fields = ['joined_at', 'updated_at']
