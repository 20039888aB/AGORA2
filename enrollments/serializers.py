from rest_framework import serializers
from .models import Enrollment, LessonProgress, EnrollmentCertificate


class EnrollmentSerializer(serializers.ModelSerializer):
    """
    Serializer for Enrollment model
    """
    user_info = serializers.SerializerMethodField()
    course_info = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    days_since_enrollment = serializers.ReadOnlyField()
    is_completed = serializers.ReadOnlyField()
    is_active_enrollment = serializers.ReadOnlyField()
    completion_rate = serializers.ReadOnlyField()
    
    class Meta:
        model = Enrollment
        fields = [
            'id', 'user', 'user_info', 'course', 'course_info',
            'enrollment_date', 'start_date', 'end_date', 'completion_date',
            'progress_percentage', 'last_accessed_at', 'total_time_spent',
            'status', 'status_display', 'notes', 'certificate_issued',
            'certificate_url', 'payment_status', 'payment_status_display',
            'payment_amount', 'payment_date', 'is_active', 'created_at',
            'updated_at', 'days_since_enrollment', 'is_completed',
            'is_active_enrollment', 'completion_rate'
        ]
        read_only_fields = [
            'enrollment_date', 'created_at', 'updated_at',
            'days_since_enrollment', 'is_completed', 'is_active_enrollment',
            'completion_rate'
        ]
    
    def get_user_info(self, obj):
        """Get user information"""
        return {
            'id': str(obj.user.id),
            'email': obj.user.email,
            'full_name': obj.user.full_name,
            'role': obj.user.role,
        }
    
    def get_course_info(self, obj):
        """Get course information"""
        return {
            'id': str(obj.course.id),
            'title': obj.course.title,
            'slug': obj.course.slug,
            'difficulty': obj.course.difficulty,
            'duration_hours': obj.course.duration_hours,
            'price': obj.course.price,
        }
    
    def validate_progress_percentage(self, value):
        """Validate progress percentage"""
        if value < 0 or value > 100:
            raise serializers.ValidationError("Progress must be between 0 and 100")
        return value
    
    def validate_payment_amount(self, value):
        """Validate payment amount"""
        if value < 0:
            raise serializers.ValidationError("Payment amount cannot be negative")
        return value


class LessonProgressSerializer(serializers.ModelSerializer):
    """
    Serializer for LessonProgress model
    """
    user_info = serializers.SerializerMethodField()
    lesson_info = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_completed = serializers.ReadOnlyField()
    
    class Meta:
        model = LessonProgress
        fields = [
            'id', 'enrollment', 'user_info', 'lesson', 'lesson_info',
            'status', 'status_display', 'progress_percentage', 'time_spent',
            'last_accessed_at', 'completed_at', 'notes', 'quiz_score',
            'assignment_score', 'created_at', 'updated_at', 'is_completed'
        ]
        read_only_fields = ['created_at', 'updated_at', 'is_completed']
    
    def get_user_info(self, obj):
        """Get user information"""
        return {
            'id': str(obj.user.id),
            'email': obj.user.email,
            'full_name': obj.user.full_name,
        }
    
    def get_lesson_info(self, obj):
        """Get lesson information"""
        return {
            'id': str(obj.lesson.id),
            'title': obj.lesson.title,
            'slug': obj.lesson.slug,
            'lesson_type': obj.lesson.lesson_type,
            'duration_minutes': obj.lesson.duration_minutes,
        }
    
    def validate_progress_percentage(self, value):
        """Validate progress percentage"""
        if value < 0 or value > 100:
            raise serializers.ValidationError("Progress must be between 0 and 100")
        return value


class EnrollmentCertificateSerializer(serializers.ModelSerializer):
    """
    Serializer for EnrollmentCertificate model
    """
    user_info = serializers.SerializerMethodField()
    course_info = serializers.SerializerMethodField()
    certificate_info = serializers.SerializerMethodField()
    is_expired = serializers.ReadOnlyField()
    
    class Meta:
        model = EnrollmentCertificate
        fields = [
            'id', 'enrollment', 'user_info', 'course_info', 'certificate',
            'certificate_info', 'issued_date', 'expiry_date', 'verification_code',
            'download_url', 'is_revoked', 'metadata', 'created_at',
            'updated_at', 'is_expired'
        ]
        read_only_fields = [
            'issued_date', 'verification_code', 'created_at',
            'updated_at', 'is_expired'
        ]
    
    def get_user_info(self, obj):
        """Get user information"""
        return {
            'id': str(obj.enrollment.user.id),
            'email': obj.enrollment.user.email,
            'full_name': obj.enrollment.user.full_name,
        }
    
    def get_course_info(self, obj):
        """Get course information"""
        return {
            'id': str(obj.enrollment.course.id),
            'title': obj.enrollment.course.title,
            'slug': obj.enrollment.course.slug,
        }
    
    def get_certificate_info(self, obj):
        """Get certificate information"""
        return {
            'id': str(obj.certificate.id),
            'template_name': obj.certificate.template.name,
            'issued_by': obj.certificate.issued_by.email if obj.certificate.issued_by else None,
        }


class EnrollmentCreateSerializer(serializers.Serializer):
    """
    Serializer for creating enrollments
    """
    course_id = serializers.UUIDField(write_only=True)
    payment_status = serializers.ChoiceField(
        choices=Enrollment.STATUS_CHOICES,
        default='PENDING'
    )
    payment_amount = serializers.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    def validate_course_id(self, value):
        """Validate course exists and is accessible"""
        from courses.models import Course
        try:
            course = Course.objects.get(id=value)
            if not course.is_accessible:
                raise serializers.ValidationError("Course is not accessible for enrollment")
            return value
        except Course.DoesNotExist:
            raise serializers.ValidationError("Course not found")


class EnrollmentUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating enrollments
    """
    status = serializers.ChoiceField(
        choices=Enrollment.STATUS_CHOICES,
        required=False
    )
    progress_percentage = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False
    )
    notes = serializers.CharField(required=False, allow_blank=True)


class LessonProgressUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating lesson progress
    """
    progress_percentage = serializers.DecimalField(
        max_digits=5, decimal_places=2,
        min_value=0, max_value=100
    )
    time_spent = serializers.DurationField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    quiz_score = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False,
        min_value=0, max_value=100
    )
    assignment_score = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False,
        min_value=0, max_value=100
    )


class CertificateVerifySerializer(serializers.Serializer):
    """
    Serializer for certificate verification
    """
    verification_code = serializers.CharField(max_length=50)


class CertificateRevokeSerializer(serializers.Serializer):
    """
    Serializer for revoking certificates
    """
    reason = serializers.CharField(max_length=500, required=False)


class EnrollmentStatisticsSerializer(serializers.Serializer):
    """
    Serializer for enrollment statistics
    """
    total_enrollments = serializers.IntegerField(read_only=True)
    active_enrollments = serializers.IntegerField(read_only=True)
    completed_enrollments = serializers.IntegerField(read_only=True)
    suspended_enrollments = serializers.IntegerField(read_only=True)
    average_progress = serializers.FloatField(read_only=True)
    completion_rate = serializers.FloatField(read_only=True)
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)


class LessonProgressStatisticsSerializer(serializers.Serializer):
    """
    Serializer for lesson progress statistics
    """
    total_students = serializers.IntegerField(read_only=True)
    completed_students = serializers.IntegerField(read_only=True)
    in_progress_students = serializers.IntegerField(read_only=True)
    not_started_students = serializers.IntegerField(read_only=True)
    average_progress = serializers.FloatField(read_only=True)
    average_time_spent = serializers.DurationField(read_only=True)


class CertificateStatisticsSerializer(serializers.Serializer):
    """
    Serializer for certificate statistics
    """
    total_certificates = serializers.IntegerField(read_only=True)
    active_certificates = serializers.IntegerField(read_only=True)
    revoked_certificates = serializers.IntegerField(read_only=True)
    expired_certificates = serializers.IntegerField(read_only=True)
    certificates_this_month = serializers.IntegerField(read_only=True)
