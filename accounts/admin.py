from django.contrib import admin
from django.utils.html import format_html
from .models import User, UserProfile, RoleRequest


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = [
        'email', 'full_name', 'role', 'organization', 'is_active',
        'login_count', 'last_active_at', 'original_email', 'created_at'
    ]
    list_filter = [
        'role', 'is_active', 'is_deleted', 'organization',
        'created_at', 'last_active_at'
    ]
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-created_at']
    readonly_fields = [
        'id', 'login_count', 'last_active_at', 'role_update_count',
        'created_at', 'updated_at', 'deleted_at', 'original_email'
    ]
    
    fieldsets = (
        (None, {
            'fields': ('email', 'password', 'first_name', 'last_name')
        }),
        ('Role & Organization', {
            'fields': ('role', 'organization', 'managed_by')
        }),
        ('Profile', {
            'fields': ('phone', 'avatar', 'date_of_birth', 'bio', 'is_verified')
        }),
        ('Status', {
            'fields': ('is_active', 'is_deleted', 'deleted_at', 'original_email')
        }),
        ('Timestamps', {
            'fields': ('login_count', 'last_active_at', 'role_update_count',
                      'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return User.objects.filter(is_deleted=False)
    
    def full_name(self, obj):
        return obj.full_name if obj else '-'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'employee_id', 'department', 'team', 'job_title',
        'location', 'created_at'
    ]
    list_filter = [
        'department', 'team', 'created_at'
    ]
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name',
        'employee_id', 'job_title'
    ]
    readonly_fields = ['created_at', 'updated_at', 'last_login_ip']
    
    fieldsets = (
        (None, {
            'fields': ('user', 'employee_id')
        }),
        ('Organization', {
            'fields': ('department', 'team')
        }),
        ('Details', {
            'fields': ('job_title', 'location', 'timezone', 'language',
                      'notification_preferences')
        }),
        ('System', {
            'fields': ('last_login_ip', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(RoleRequest)
class RoleRequestAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'requested_role', 'status', 'reviewed_by',
        'created_at', 'reviewed_at'
    ]
    list_filter = [
        'status', 'requested_role', 'created_at', 'reviewed_at'
    ]
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name',
        'reason', 'review_comments'
    ]
    ordering = ['-created_at']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'reviewed_at'
    ]
    
    fieldsets = (
        (None, {
            'fields': ('user', 'requested_role', 'status')
        }),
        ('Request Details', {
            'fields': ('reason',)
        }),
        ('Review', {
            'fields': ('reviewed_by', 'reviewed_at', 'review_comments'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_requests', 'reject_requests']
    
    def approve_requests(self, request, queryset):
        count = 0
        for role_request in queryset.filter(status='PENDING'):
            role_request.approve(request.user, 'Bulk approved via admin')
            count += 1
        self.message_user(request, f'Approved {count} role requests.')
    approve_requests.short_description = 'Approve selected requests'
    
    def reject_requests(self, request, queryset):
        count = 0
        for role_request in queryset.filter(status='PENDING'):
            role_request.reject(request.user, 'Bulk rejected via admin')
            count += 1
        self.message_user(request, f'Rejected {count} role requests.')
    reject_requests.short_description = 'Reject selected requests'
