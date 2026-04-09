from django.contrib import admin
from .models import Enrollment, LessonProgress, EnrollmentCertificate


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'course', 'status', 'progress_percentage',
        'enrollment_date', 'payment_status', 'payment_amount',
        'certificate_issued', 'is_active'
    ]
    list_filter = [
        'status', 'payment_status', 'certificate_issued',
        'is_active', 'enrollment_date', 'created_at'
    ]
    search_fields = ['user__email', 'course__title']
    ordering = ['-enrollment_date']
    readonly_fields = ['enrollment_date', 'created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('user', 'course', 'status')
        }),
        ('Dates', {
            'fields': ('enrollment_date', 'start_date', 'end_date', 'completion_date')
        }),
        ('Progress', {
            'fields': ('progress_percentage', 'last_accessed_at', 'total_time_spent')
        }),
        ('Payment', {
            'fields': ('payment_status', 'payment_amount', 'payment_date')
        }),
        ('Certificate', {
            'fields': ('certificate_issued', 'certificate_url')
        }),
        ('Status', {
            'fields': ('is_active', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'lesson', 'status', 'progress_percentage',
        'time_spent', 'last_accessed_at', 'completed_at'
    ]
    list_filter = [
        'status', 'last_accessed_at', 'completed_at', 'created_at'
    ]
    search_fields = ['user__email', 'lesson__title']
    ordering = ['enrollment', 'lesson']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('enrollment', 'lesson', 'status')
        }),
        ('Progress', {
            'fields': ('progress_percentage', 'time_spent', 'last_accessed_at', 'completed_at')
        }),
        ('Scores', {
            'fields': ('quiz_score', 'assignment_score')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(EnrollmentCertificate)
class EnrollmentCertificateAdmin(admin.ModelAdmin):
    list_display = [
        'get_user', 'get_course', 'certificate', 'issued_date',
        'verification_code', 'is_revoked', 'is_expired'
    ]
    list_filter = [
        'is_revoked', 'issued_date', 'expiry_date', 'created_at'
    ]
    search_fields = [
        'enrollment__user__email', 'enrollment__course__title', 'verification_code'
    ]
    ordering = ['-issued_date']
    readonly_fields = ['issued_date', 'verification_code', 'created_at', 'updated_at']
    
    def get_user(self, obj):
        return obj.enrollment.user
    get_user.short_description = 'User'
    
    def get_course(self, obj):
        return obj.enrollment.course
    get_course.short_description = 'Course'
    
    fieldsets = (
        (None, {
            'fields': ('enrollment', 'certificate')
        }),
        ('Certificate Details', {
            'fields': ('issued_date', 'expiry_date', 'verification_code', 'download_url')
        }),
        ('Status', {
            'fields': ('is_revoked', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
