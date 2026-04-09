from django.contrib import admin
from .models import CertificateTemplate, Certificate, CertificateVerification, CertificateBatch


@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'organization', 'layout', 'is_default', 'is_active', 'created_at'
    ]
    list_filter = [
        'organization', 'layout', 'is_default', 'is_active', 'created_at'
    ]
    search_fields = ['name', 'description']
    ordering = ['organization', 'name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'organization')
        }),
        ('Design', {
            'fields': ('background_color', 'text_color', 'accent_color', 'font_family', 'font_size', 'layout')
        }),
        ('Content', {
            'fields': ('header_text', 'subheader_text', 'recipient_text', 'course_text', 'completion_text', 'footer_text')
        }),
        ('Images', {
            'fields': ('logo', 'signature_1', 'signature_1_title', 'signature_2', 'signature_2_title')
        }),
        ('Dimensions', {
            'fields': ('width', 'height', 'margin_top', 'margin_bottom', 'margin_left', 'margin_right')
        }),
        ('Status', {
            'fields': ('is_default', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = [
        'certificate_number', 'recipient_name', 'course_name', 'user',
        'status', 'score', 'issued_date', 'expiry_date', 'is_valid', 'is_expired'
    ]
    list_filter = [
        'template', 'user', 'course', 'status', 'issued_date', 'expiry_date'
    ]
    search_fields = ['certificate_number', 'recipient_name', 'course_name', 'user__email']
    ordering = ['-issued_date']
    readonly_fields = [
        'created_at', 'updated_at', 'certificate_number', 'verification_code',
        'is_valid', 'is_expired', 'days_until_expiry'
    ]
    
    fieldsets = (
        (None, {
            'fields': ('template', 'user', 'course', 'enrollment')
        }),
        ('Certificate Details', {
            'fields': ('certificate_number', 'verification_code', 'score', 'grade')
        }),
        ('Dates', {
            'fields': ('completion_date', 'issued_date', 'expiry_date')
        }),
        ('Issuer', {
            'fields': ('issued_by', 'issuer_name', 'issuer_title')
        }),
        ('Content', {
            'fields': ('recipient_name', 'course_name', 'completion_text', 'additional_text')
        }),
        ('Status', {
            'fields': ('status', 'download_url', 'pdf_file')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CertificateVerification)
class CertificateVerificationAdmin(admin.ModelAdmin):
    list_display = [
        'verification_code', 'certificate', 'verified_by', 'is_valid',
        'verified_at', 'ip_address'
    ]
    list_filter = [
        'certificate', 'is_valid', 'verified_by', 'verified_at'
    ]
    search_fields = ['verification_code', 'certificate__certificate_number']
    ordering = ['-verified_at']
    readonly_fields = ['verified_at']


@admin.register(CertificateBatch)
class CertificateBatchAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'organization', 'template', 'course', 'status',
        'total_certificates', 'processed_certificates', 'failed_certificates',
        'progress_percentage', 'created_at'
    ]
    list_filter = [
        'organization', 'template', 'course', 'status', 'created_at'
    ]
    search_fields = ['name', 'description']
    ordering = ['-created_at']
    readonly_fields = [
        'created_at', 'updated_at', 'progress_percentage', 'is_completed', 'is_failed'
    ]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'organization')
        }),
        ('Batch Details', {
            'fields': ('template', 'course', 'total_certificates', 'processed_certificates', 'failed_certificates')
        }),
        ('Status', {
            'fields': ('status', 'error_message', 'processing_started_at', 'processing_completed_at')
        }),
        ('Created By', {
            'fields': ('created_by',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
