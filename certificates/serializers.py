from rest_framework import serializers
from .models import CertificateTemplate, Certificate, CertificateVerification, CertificateBatch


class CertificateTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for CertificateTemplate model
    """
    organization_info = serializers.SerializerMethodField()
    layout_display = serializers.CharField(source='get_layout_display', read_only=True)
    
    class Meta:
        model = CertificateTemplate
        fields = [
            'id', 'name', 'description', 'organization', 'organization_info',
            'background_color', 'text_color', 'accent_color', 'font_family',
            'font_size', 'layout', 'layout_display', 'header_text',
            'subheader_text', 'recipient_text', 'course_text', 'completion_text',
            'footer_text', 'logo', 'signature_1', 'signature_1_title',
            'signature_2', 'signature_2_title', 'width', 'height',
            'margin_top', 'margin_bottom', 'margin_left', 'margin_right',
            'is_default', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_organization_info(self, obj):
        """Get organization information"""
        return {
            'id': str(obj.organization.id),
            'name': obj.organization.name,
        }
    
    def validate_background_color(self, value):
        """Validate background color"""
        if not value.startswith('#') or len(value) != 7:
            raise serializers.ValidationError("Color must be a valid hex color code (#RRGGBB)")
        return value
    
    def validate_text_color(self, value):
        """Validate text color"""
        if not value.startswith('#') or len(value) != 7:
            raise serializers.ValidationError("Color must be a valid hex color code (#RRGGBB)")
        return value
    
    def validate_accent_color(self, value):
        """Validate accent color"""
        if not value.startswith('#') or len(value) != 7:
            raise serializers.ValidationError("Color must be a valid hex color code (#RRGGBB)")
        return value


class CertificateSerializer(serializers.ModelSerializer):
    """
    Serializer for Certificate model
    """
    template_info = serializers.SerializerMethodField()
    user_info = serializers.SerializerMethodField()
    course_info = serializers.SerializerMethodField()
    enrollment_info = serializers.SerializerMethodField()
    issued_by_info = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_valid = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    days_until_expiry = serializers.ReadOnlyField()
    
    class Meta:
        model = Certificate
        fields = [
            'id', 'template', 'template_info', 'user', 'user_info', 'course',
            'course_info', 'enrollment', 'enrollment_info', 'certificate_number',
            'verification_code', 'score', 'grade', 'completion_date',
            'issued_date', 'expiry_date', 'issued_by', 'issued_by_info',
            'issuer_name', 'issuer_title', 'recipient_name', 'course_name',
            'completion_text', 'additional_text', 'status', 'status_display',
            'download_url', 'pdf_file', 'created_at', 'updated_at',
            'is_valid', 'is_expired', 'days_until_expiry'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'certificate_number', 'verification_code',
            'is_valid', 'is_expired', 'days_until_expiry'
        ]
    
    def get_template_info(self, obj):
        """Get template information"""
        return {
            'id': str(obj.template.id),
            'name': obj.template.name,
            'layout': obj.template.layout,
        }
    
    def get_user_info(self, obj):
        """Get user information"""
        return {
            'id': str(obj.user.id),
            'email': obj.user.email,
            'full_name': obj.user.full_name,
        }
    
    def get_course_info(self, obj):
        """Get course information"""
        return {
            'id': str(obj.course.id),
            'title': obj.course.title,
            'slug': obj.course.slug,
        }
    
    def get_enrollment_info(self, obj):
        """Get enrollment information"""
        return {
            'id': str(obj.enrollment.id),
            'enrollment_date': obj.enrollment.enrollment_date,
            'completion_date': obj.enrollment.completion_date,
            'progress_percentage': obj.enrollment.progress_percentage,
        }
    
    def get_issued_by_info(self, obj):
        """Get issued by information"""
        if obj.issued_by:
            return {
                'id': str(obj.issued_by.id),
                'email': obj.issued_by.email,
                'full_name': obj.issued_by.full_name,
            }
        return None
    
    def validate_score(self, value):
        """Validate score"""
        if value is not None and (value < 0 or value > 100):
            raise serializers.ValidationError("Score must be between 0 and 100")
        return value


class CertificateVerificationSerializer(serializers.ModelSerializer):
    """
    Serializer for CertificateVerification model
    """
    certificate_info = serializers.SerializerMethodField()
    verified_by_info = serializers.SerializerMethodField()
    verification_result = serializers.SerializerMethodField()
    
    class Meta:
        model = CertificateVerification
        fields = [
            'id', 'certificate', 'certificate_info', 'verification_code',
            'verified_at', 'verified_by', 'verified_by_info', 'ip_address',
            'user_agent', 'is_valid', 'verification_result'
        ]
        read_only_fields = ['verified_at', 'verification_result']
    
    def get_certificate_info(self, obj):
        """Get certificate information"""
        if obj.certificate:
            return {
                'id': str(obj.certificate.id),
                'certificate_number': obj.certificate.certificate_number,
                'recipient_name': obj.certificate.recipient_name,
                'course_name': obj.certificate.course_name,
                'issued_date': obj.certificate.issued_date,
                'is_expired': obj.certificate.is_expired,
            }
        return None
    
    def get_verified_by_info(self, obj):
        """Get verified by information"""
        if obj.verified_by:
            return {
                'id': str(obj.verified_by.id),
                'email': obj.verified_by.email,
                'full_name': obj.verified_by.full_name,
            }
        return None
    
    def get_verification_result(self, obj):
        """Get verification result"""
        return {
            'valid': obj.is_valid,
            'is_expired': obj.certificate.is_expired if obj.certificate else False,
        }


class CertificateBatchSerializer(serializers.ModelSerializer):
    """
    Serializer for CertificateBatch model
    """
    organization_info = serializers.SerializerMethodField()
    template_info = serializers.SerializerMethodField()
    course_info = serializers.SerializerMethodField()
    created_by_info = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    progress_percentage = serializers.ReadOnlyField()
    is_completed = serializers.ReadOnlyField()
    is_failed = serializers.ReadOnlyField()
    
    class Meta:
        model = CertificateBatch
        fields = [
            'id', 'name', 'description', 'organization', 'organization_info',
            'template', 'template_info', 'course', 'course_info',
            'total_certificates', 'processed_certificates', 'failed_certificates',
            'status', 'status_display', 'error_message', 'processing_started_at',
            'processing_completed_at', 'created_by', 'created_by_info',
            'created_at', 'updated_at', 'progress_percentage', 'is_completed',
            'is_failed'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'progress_percentage', 'is_completed',
            'is_failed'
        ]
    
    def get_organization_info(self, obj):
        """Get organization information"""
        return {
            'id': str(obj.organization.id),
            'name': obj.organization.name,
        }
    
    def get_template_info(self, obj):
        """Get template information"""
        return {
            'id': str(obj.template.id),
            'name': obj.template.name,
            'layout': obj.template.layout,
        }
    
    def get_course_info(self, obj):
        """Get course information"""
        return {
            'id': str(obj.course.id),
            'title': obj.course.title,
            'slug': obj.course.slug,
        }
    
    def get_created_by_info(self, obj):
        """Get created by information"""
        if obj.created_by:
            return {
                'id': str(obj.created_by.id),
                'email': obj.created_by.email,
                'full_name': obj.created_by.full_name,
            }
        return None


class CertificateCreateSerializer(serializers.Serializer):
    """
    Serializer for creating certificates
    """
    enrollment_id = serializers.UUIDField(write_only=True)
    template_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)


class CertificateIssueSerializer(serializers.Serializer):
    """
    Serializer for issuing certificates
    """
    pass


class CertificateRevokeSerializer(serializers.Serializer):
    """
    Serializer for revoking certificates
    """
    reason = serializers.CharField(max_length=500, required=False)


class CertificateVerifySerializer(serializers.Serializer):
    """
    Serializer for certificate verification
    """
    verification_code = serializers.CharField(max_length=50)


class CertificateTemplateCreateSerializer(serializers.Serializer):
    """
    Serializer for creating certificate templates
    """
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    organization_id = serializers.UUIDField(write_only=True)
    background_color = serializers.CharField(max_length=7, default='#ffffff')
    text_color = serializers.CharField(max_length=7, default='#333333')
    accent_color = serializers.CharField(max_length=7, default='#007bff')
    font_family = serializers.CharField(max_length=50, default='Arial')
    font_size = serializers.IntegerField(default=16)
    layout = serializers.ChoiceField(choices=[
        ('MODERN', 'Modern'),
        ('CLASSIC', 'Classic'),
        ('MINIMAL', 'Minimal'),
        ('ELEGANT', 'Elegant'),
        ('CORPORATE', 'Corporate'),
    ], default='MODERN')
    header_text = serializers.CharField(max_length=200, default='Certificate of Completion')
    subheader_text = serializers.CharField(max_length=200, default='This is to certify that')
    recipient_text = serializers.CharField(max_length=200, default='has successfully completed')
    course_text = serializers.CharField(max_length=200, default='the course')
    completion_text = serializers.CharField(max_length=200, default='with distinction')
    footer_text = serializers.CharField(max_length=200, default='Issued on')
    width = serializers.IntegerField(default=800)
    height = serializers.IntegerField(default=600)
    margin_top = serializers.IntegerField(default=50)
    margin_bottom = serializers.IntegerField(default=50)
    margin_left = serializers.IntegerField(default=50)
    margin_right = serializers.IntegerField(default=50)
    is_default = serializers.BooleanField(default=False)


class CertificateBatchCreateSerializer(serializers.Serializer):
    """
    Serializer for creating certificate batches
    """
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    organization_id = serializers.UUIDField(write_only=True)
    template_id = serializers.UUIDField(write_only=True)
    course_id = serializers.UUIDField(write_only=True)


class CertificateBatchProcessSerializer(serializers.Serializer):
    """
    Serializer for processing certificate batches
    """
    pass


class CertificateStatisticsSerializer(serializers.Serializer):
    """
    Serializer for certificate statistics
    """
    total_certificates = serializers.IntegerField(read_only=True)
    issued_certificates = serializers.IntegerField(read_only=True)
    revoked_certificates = serializers.IntegerField(read_only=True)
    expired_certificates = serializers.IntegerField(read_only=True)
    valid_certificates = serializers.IntegerField(read_only=True)
    certificates_this_month = serializers.IntegerField(read_only=True)
    certificates_this_year = serializers.IntegerField(read_only=True)


class CertificateTemplateStatisticsSerializer(serializers.Serializer):
    """
    Serializer for certificate template statistics
    """
    total_certificates = serializers.IntegerField(read_only=True)
    issued_certificates = serializers.IntegerField(read_only=True)
    revoked_certificates = serializers.IntegerField(read_only=True)
    expired_certificates = serializers.IntegerField(read_only=True)
    valid_certificates = serializers.IntegerField(read_only=True)


class CertificateBatchStatisticsSerializer(serializers.Serializer):
    """
    Serializer for certificate batch statistics
    """
    total_certificates = serializers.IntegerField(read_only=True)
    processed_certificates = serializers.IntegerField(read_only=True)
    failed_certificates = serializers.IntegerField(read_only=True)
    success_rate = serializers.FloatField(read_only=True)
    progress_percentage = serializers.FloatField(read_only=True)
    processing_duration = serializers.DurationField(read_only=True)
