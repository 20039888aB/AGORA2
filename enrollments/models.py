from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class Enrollment(models.Model):
    """
    Course enrollment with progress tracking
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACTIVE', 'Active'),
        ('SUSPENDED', 'Suspended'),
        ('COMPLETED', 'Completed'),
        ('DROPPED', 'Dropped'),
        ('EXPIRED', 'Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='enrollments',
        db_index=True
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='enrollments',
        db_index=True
    )
    
    # Enrollment details
    enrollment_date = models.DateTimeField(auto_now_add=True, db_index=True)
    start_date = models.DateTimeField(null=True, blank=True, db_index=True)
    end_date = models.DateTimeField(null=True, blank=True, db_index=True)
    completion_date = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Progress tracking
    progress_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.00,
        db_index=True
    )
    last_accessed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    total_time_spent = models.DurationField(default=timezone.timedelta(0))
    
    # Status and metadata
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        db_index=True
    )
    notes = models.TextField(blank=True)
    certificate_issued = models.BooleanField(default=False, db_index=True)
    certificate_url = models.URLField(max_length=500, blank=True)
    
    # Payment information
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('COMPLETED', 'Completed'),
            ('FAILED', 'Failed'),
            ('REFUNDED', 'Refunded'),
        ],
        default='PENDING',
        db_index=True
    )
    payment_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00
    )
    payment_date = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Access control
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'enrollments'
        verbose_name = 'Enrollment'
        verbose_name_plural = 'Enrollments'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'course'],
                name='unique_user_course_enrollment'
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['course', 'status']),
            models.Index(fields=['status', 'enrollment_date']),
            models.Index(fields=['progress_percentage']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-enrollment_date']
    
    def __str__(self):
        return f"{self.user.email} - {self.course.title} ({self.status})"
    
    @property
    def is_completed(self):
        """Check if enrollment is completed"""
        return self.status == 'COMPLETED'
    
    @property
    def is_active_enrollment(self):
        """Check if enrollment is active"""
        return self.status == 'ACTIVE'
    
    @property
    def days_since_enrollment(self):
        """Get days since enrollment"""
        if self.enrollment_date:
            return (timezone.now() - self.enrollment_date).days
        return 0
    
    @property
    def completion_rate(self):
        """Get completion rate as percentage"""
        return float(self.progress_percentage)
    
    def mark_completed(self, completed_by=None):
        """Mark enrollment as completed"""
        self.status = 'COMPLETED'
        self.completion_date = timezone.now()
        self.progress_percentage = 100.00
        self.save(update_fields=['status', 'completion_date', 'progress_percentage'])
        
        # Log completion
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=completed_by or self.user,
            action='ENROLLMENT_COMPLETE',
            details=f'Enrollment completed for course: {self.course.title}'
        )
    
    def suspend(self, suspended_by=None, reason=''):
        """Suspend enrollment"""
        self.status = 'SUSPENDED'
        self.notes = f"Suspended: {reason}"
        self.save(update_fields=['status', 'notes'])
        
        # Log suspension
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=suspended_by,
            action='ENROLLMENT_SUSPEND',
            details={
                'enrollment': str(self.id),
                'course': str(self.course.id),
                'reason': reason,
            },
            ip_address=suspended_by.last_login_ip
        )
    
    def activate(self, activated_by=None):
        """Activate enrollment"""
        self.status = 'ACTIVE'
        self.start_date = timezone.now()
        self.save(update_fields=['status', 'start_date'])
        
        # Log activation
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=activated_by,
            action='ENROLLMENT_ACTIVATE',
            details={
                'enrollment': str(self.id),
                'course': str(self.course.id),
            },
            ip_address=activated_by.last_login_ip
        )
    
    def clean(self):
        """Model validation"""
        errors = {}
        
        # Validate course belongs to same organization as user
        if self.course and self.user and self.course.organization != self.user.organization:
            errors['course'] = "Course must belong to same organization as user"
        
        # Validate dates
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            errors['start_date'] = "Start date must be before end date"
        
        # Validate progress
        if self.progress_percentage < 0 or self.progress_percentage > 100:
            errors['progress_percentage'] = "Progress must be between 0 and 100"
        
        # Validate payment amount
        if self.payment_amount < 0:
            errors['payment_amount'] = "Payment amount cannot be negative"
        
        if errors:
            raise ValidationError(errors)


class LessonProgress(models.Model):
    """
    Individual lesson progress tracking
    """
    
    STATUS_CHOICES = [
        ('NOT_STARTED', 'Not Started'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('SKIPPED', 'Skipped'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name='lesson_progress',
        db_index=True
    )
    lesson = models.ForeignKey(
        'courses.Lesson',
        on_delete=models.CASCADE,
        related_name='progress_records',
        db_index=True
    )
    
    # Progress tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='NOT_STARTED',
        db_index=True
    )
    progress_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        db_index=True
    )
    time_spent = models.DurationField(default=timezone.timedelta(0))
    last_accessed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Additional data
    notes = models.TextField(blank=True)
    quiz_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    assignment_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'lesson_progress'
        verbose_name = 'Lesson Progress'
        verbose_name_plural = 'Lesson Progress'
        constraints = [
            models.UniqueConstraint(
                fields=['enrollment', 'lesson'],
                name='unique_enrollment_lesson_progress'
            ),
        ]
        indexes = [
            models.Index(fields=['enrollment', 'status']),
            models.Index(fields=['lesson', 'status']),
            models.Index(fields=['progress_percentage']),
            models.Index(fields=['completed_at']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['enrollment', 'lesson']
    
    def __str__(self):
        return f"{self.user.email} - {self.lesson.title} ({self.progress_percentage}%)"
    
    @property
    def user(self):
        """Get user from enrollment"""
        return self.enrollment.user
    
    @property
    def is_completed(self):
        """Check if lesson is completed"""
        return self.status == 'COMPLETED'
    
    def mark_completed(self, completed_by=None):
        """Mark lesson as completed"""
        self.status = 'COMPLETED'
        self.progress_percentage = 100.00
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'progress_percentage', 'completed_at'])
        
        # Log lesson completion
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=completed_by or self.user,
            action='LESSON_COMPLETE',
            details={
                'enrollment': str(self.enrollment.id),
                'lesson': str(self.lesson.id),
                'progress': float(self.progress_percentage),
            },
            ip_address=(completed_by or self.user).last_login_ip
        )
    
    def update_progress(self, progress_percentage, updated_by=None):
        """Update lesson progress"""
        if progress_percentage < 0:
            progress_percentage = 0
        elif progress_percentage > 100:
            progress_percentage = 100
        
        self.progress_percentage = progress_percentage
        self.last_accessed_at = timezone.now()
        
        if progress_percentage >= 100:
            self.status = 'COMPLETED'
            self.completed_at = timezone.now()
        elif self.status == 'NOT_STARTED':
            self.status = 'IN_PROGRESS'
        
        self.save(update_fields=['progress_percentage', 'last_accessed_at', 'status', 'completed_at'])
        
        # Log progress update
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=updated_by or self.user,
            action='LESSON_PROGRESS_UPDATE',
            details={
                'enrollment': str(self.enrollment.id),
                'lesson': str(self.lesson.id),
                'progress': float(progress_percentage),
            },
            ip_address=(updated_by or self.user).last_login_ip
        )


class EnrollmentCertificate(models.Model):
    """
    Certificate tracking for completed enrollments
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.OneToOneField(
        Enrollment,
        on_delete=models.CASCADE,
        related_name='certificate',
        db_index=True
    )
    certificate = models.ForeignKey(
        'certificates.Certificate',
        on_delete=models.CASCADE,
        related_name='enrollment_certificates',
        db_index=True
    )
    
    # Certificate details
    issued_date = models.DateTimeField(auto_now_add=True, db_index=True)
    expiry_date = models.DateTimeField(null=True, blank=True, db_index=True)
    verification_code = models.CharField(max_length=50, unique=True, db_index=True)
    download_url = models.URLField(max_length=500, blank=True)
    is_revoked = models.BooleanField(default=False, db_index=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'enrollment_certificates'
        verbose_name = 'Enrollment Certificate'
        verbose_name_plural = 'Enrollment Certificates'
        constraints = [
            models.UniqueConstraint(
                fields=['verification_code'],
                name='unique_certificate_verification_code'
            ),
        ]
        indexes = [
            models.Index(fields=['enrollment']),
            models.Index(fields=['certificate']),
            models.Index(fields=['issued_date']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['is_revoked']),
        ]
        ordering = ['-issued_date']
    
    def __str__(self):
        return f"{self.enrollment.user.email} - {self.enrollment.course.title} Certificate"
    
    @property
    def is_expired(self):
        """Check if certificate is expired"""
        if not self.expiry_date:
            return False
        return timezone.now() > self.expiry_date
    
    def revoke(self, revoked_by=None, reason=''):
        """Revoke certificate"""
        self.is_revoked = True
        self.metadata = {
            'revoked_at': timezone.now().isoformat(),
            'revoked_by': str(revoked_by.id) if revoked_by else None,
            'revocation_reason': reason,
        }
        self.save(update_fields=['is_revoked', 'metadata'])
        
        # Log certificate revocation
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=revoked_by,
            action='CERTIFICATE_REVOKE',
            details={
                'certificate': str(self.id),
                'enrollment': str(self.enrollment.id),
                'reason': reason,
            },
            ip_address=revoked_by.last_login_ip
        )


class DocumentProgress(models.Model):
    """
    Track student progress on course documents
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE)
    document = models.ForeignKey('courses.CourseDocument', on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'document_progress'
        verbose_name = 'Document Progress'
        verbose_name_plural = 'Document Progress'
        unique_together = ['user', 'course', 'document']
        indexes = [
            models.Index(fields=['user', 'course']),
            models.Index(fields=['user', 'course', 'is_completed']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.document.title}"
