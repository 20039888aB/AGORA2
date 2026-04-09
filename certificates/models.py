from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class CertificateTemplate(models.Model):
    """
    Certificate template with customizable design
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, db_index=True)
    description = models.TextField(blank=True)
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='certificate_templates',
        db_index=True
    )
    
    # Template design
    background_color = models.CharField(max_length=7, default='#ffffff')
    text_color = models.CharField(max_length=7, default='#333333')
    accent_color = models.CharField(max_length=7, default='#007bff')
    font_family = models.CharField(max_length=50, default='Arial')
    font_size = models.PositiveIntegerField(default=16)
    layout = models.CharField(
        max_length=20,
        choices=[
            ('MODERN', 'Modern'),
            ('CLASSIC', 'Classic'),
            ('MINIMAL', 'Minimal'),
            ('ELEGANT', 'Elegant'),
            ('CORPORATE', 'Corporate'),
        ],
        default='MODERN'
    )
    
    # Template content
    header_text = models.CharField(max_length=200, default='Certificate of Completion')
    subheader_text = models.CharField(max_length=200, default='This is to certify that')
    recipient_text = models.CharField(max_length=200, default='has successfully completed')
    course_text = models.CharField(max_length=200, default='the course')
    completion_text = models.CharField(max_length=200, default='with distinction')
    footer_text = models.CharField(max_length=200, default='Issued on')
    
    # Logo and signature
    logo = models.ImageField(upload_to='certificates/logos/', blank=True, null=True)
    signature_1 = models.ImageField(upload_to='certificates/signatures/', blank=True, null=True)
    signature_1_title = models.CharField(max_length=100, blank=True)
    signature_2 = models.ImageField(upload_to='certificates/signatures/', blank=True, null=True)
    signature_2_title = models.CharField(max_length=100, blank=True)
    
    # Dimensions and settings
    width = models.PositiveIntegerField(default=800)  # pixels
    height = models.PositiveIntegerField(default=600)  # pixels
    margin_top = models.PositiveIntegerField(default=50)
    margin_bottom = models.PositiveIntegerField(default=50)
    margin_left = models.PositiveIntegerField(default=50)
    margin_right = models.PositiveIntegerField(default=50)
    
    # Status and metadata
    is_default = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'certificate_templates'
        verbose_name = 'Certificate Template'
        verbose_name_plural = 'Certificate Templates'
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'name'],
                name='unique_org_template_name'
            ),
        ]
        indexes = [
            models.Index(fields=['organization', 'is_default']),
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['layout']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['organization', 'name']
    
    def __str__(self):
        return f"{self.organization.name} - {self.name}"
    
    def clean(self):
        """Model validation"""
        errors = {}
        
        # Ensure only one default template per organization
        if self.is_default:
            existing_default = CertificateTemplate.objects.filter(
                organization=self.organization,
                is_default=True
            ).exclude(id=self.id)
            
            if existing_default.exists():
                errors['is_default'] = "Only one default template is allowed per organization"
        
        # Validate color codes
        color_fields = ['background_color', 'text_color', 'accent_color']
        for field in color_fields:
            color = getattr(self, field)
            if not color.startswith('#') or len(color) != 7:
                errors[field] = "Color must be a valid hex color code (#RRGGBB)"
        
        # Validate dimensions
        if self.width <= 0 or self.height <= 0:
            errors['width'] = "Width and height must be positive"
        
        if errors:
            raise ValidationError(errors)


class Certificate(models.Model):
    """
    Individual certificate issued to users
    """
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('ISSUED', 'Issued'),
        ('REVOKED', 'Revoked'),
        ('EXPIRED', 'Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        CertificateTemplate,
        on_delete=models.CASCADE,
        related_name='certificates',
        db_index=True
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='certificates',
        db_index=True
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='certificates',
        db_index=True
    )
    enrollment = models.ForeignKey(
        'enrollments.Enrollment',
        on_delete=models.CASCADE,
        related_name='certificates',
        db_index=True
    )
    
    # Certificate details
    certificate_number = models.CharField(max_length=50, unique=True, db_index=True)
    verification_code = models.CharField(max_length=50, unique=True, db_index=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    grade = models.CharField(max_length=10, blank=True)
    completion_date = models.DateTimeField(db_index=True)
    issued_date = models.DateTimeField(db_index=True)
    expiry_date = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Issuer information
    issued_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='issued_certificates',
        db_index=True
    )
    issuer_name = models.CharField(max_length=200, blank=True)
    issuer_title = models.CharField(max_length=100, blank=True)
    
    # Certificate content
    recipient_name = models.CharField(max_length=200)
    course_name = models.CharField(max_length=300)
    completion_text = models.CharField(max_length=500, blank=True)
    additional_text = models.TextField(blank=True)
    
    # Status and metadata
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        db_index=True
    )
    download_url = models.URLField(max_length=500, blank=True)
    pdf_file = models.FileField(upload_to='certificates/pdfs/', blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'certificates'
        verbose_name = 'Certificate'
        verbose_name_plural = 'Certificates'
        constraints = [
            models.UniqueConstraint(
                fields=['certificate_number'],
                name='unique_certificate_number'
            ),
            models.UniqueConstraint(
                fields=['verification_code'],
                name='unique_verification_code'
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['course', 'status']),
            models.Index(fields=['template']),
            models.Index(fields=['issued_date']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-issued_date']
    
    def __str__(self):
        return f"{self.recipient_name} - {self.course_name}"
    
    @property
    def is_valid(self):
        """Check if certificate is valid"""
        if self.status != 'ISSUED':
            return False
        
        if self.expiry_date and timezone.now() > self.expiry_date:
            return False
        
        return True
    
    @property
    def is_expired(self):
        """Check if certificate is expired"""
        if not self.expiry_date:
            return False
        return timezone.now() > self.expiry_date
    
    @property
    def days_until_expiry(self):
        """Get days until expiry"""
        if not self.expiry_date:
            return None
        delta = self.expiry_date - timezone.now()
        return delta.days if delta.days > 0 else 0
    
    def issue(self, issued_by=None):
        """Issue certificate"""
        if self.status != 'DRAFT':
            raise ValidationError("Only draft certificates can be issued")
        
        self.status = 'ISSUED'
        self.issued_date = timezone.now()
        self.issued_by = issued_by
        self.save(update_fields=['status', 'issued_date', 'issued_by'])
        
        # Generate PDF
        self.generate_pdf()
        
        # Log certificate issuance
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=issued_by,
            action='CERTIFICATE_ISSUE',
            details={
                'certificate': str(self.id),
                'user': str(self.user.id),
                'course': str(self.course.id),
                'certificate_number': self.certificate_number,
            },
            ip_address=issued_by.last_login_ip
        )
    
    def revoke(self, revoked_by=None, reason=''):
        """Revoke certificate"""
        if self.status != 'ISSUED':
            raise ValidationError("Only issued certificates can be revoked")
        
        self.status = 'REVOKED'
        self.save(update_fields=['status'])
        
        # Log certificate revocation
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=revoked_by,
            action='CERTIFICATE_REVOKE',
            details={
                'certificate': str(self.id),
                'user': str(self.user.id),
                'course': str(self.course.id),
                'reason': reason,
            },
            ip_address=revoked_by.last_login_ip
        )
    
    def generate_pdf(self):
        """Generate PDF certificate"""
        # This would integrate with a PDF generation library
        # For now, we'll just set a placeholder URL
        self.download_url = f"/api/certificates/{self.id}/download/"
        self.save(update_fields=['download_url'])
    
    def clean(self):
        """Model validation"""
        errors = {}
        
        # Validate user and course belong to same organization
        if self.user.organization != self.course.organization:
            errors['user'] = "User and course must belong to same organization"
        
        # Validate template belongs to same organization
        if self.template.organization != self.course.organization:
            errors['template'] = "Template must belong to same organization as course"
        
        # Validate enrollment belongs to user and course
        if (self.enrollment.user != self.user or 
            self.enrollment.course != self.course):
            errors['enrollment'] = "Enrollment must belong to user and course"
        
        # Validate dates
        if self.completion_date > self.issued_date:
            errors['completion_date'] = "Completion date must be before issued date"
        
        if self.expiry_date and self.expiry_date <= self.issued_date:
            errors['expiry_date'] = "Expiry date must be after issued date"
        
        # Validate score
        if self.score is not None and (self.score < 0 or self.score > 100):
            errors['score'] = "Score must be between 0 and 100"
        
        if errors:
            raise ValidationError(errors)


class CertificateVerification(models.Model):
    """
    Certificate verification records
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    certificate = models.ForeignKey(
        Certificate,
        on_delete=models.CASCADE,
        related_name='verifications',
        db_index=True
    )
    verification_code = models.CharField(max_length=50, db_index=True)
    verified_at = models.DateTimeField(auto_now_add=True, db_index=True)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='certificate_verifications',
        db_index=True
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    is_valid = models.BooleanField(default=True, db_index=True)
    
    class Meta:
        db_table = 'certificate_verifications'
        verbose_name = 'Certificate Verification'
        verbose_name_plural = 'Certificate Verifications'
        indexes = [
            models.Index(fields=['certificate', 'verified_at']),
            models.Index(fields=['verification_code']),
            models.Index(fields=['verified_by']),
            models.Index(fields=['is_valid']),
            models.Index(fields=['verified_at']),
        ]
        ordering = ['-verified_at']
    
    def __str__(self):
        return f"{self.certificate.certificate_number} - {self.verified_at}"
    
    @property
    def verification_result(self):
        """Get verification result"""
        return {
            'valid': self.is_valid,
            'certificate': self.certificate,
            'verified_at': self.verified_at,
            'is_expired': self.certificate.is_expired,
        }


class CertificateBatch(models.Model):
    """
    Batch certificate generation
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, db_index=True)
    description = models.TextField(blank=True)
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='certificate_batches',
        db_index=True
    )
    template = models.ForeignKey(
        CertificateTemplate,
        on_delete=models.CASCADE,
        related_name='certificate_batches',
        db_index=True
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='certificate_batches',
        db_index=True
    )
    
    # Batch details
    total_certificates = models.PositiveIntegerField(default=0)
    processed_certificates = models.PositiveIntegerField(default=0)
    failed_certificates = models.PositiveIntegerField(default=0)
    
    # Status and metadata
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        db_index=True
    )
    error_message = models.TextField(blank=True)
    processing_started_at = models.DateTimeField(null=True, blank=True, db_index=True)
    processing_completed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Created by
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_certificate_batches',
        db_index=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'certificate_batches'
        verbose_name = 'Certificate Batch'
        verbose_name_plural = 'Certificate Batches'
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'name'],
                name='unique_org_batch_name'
            ),
        ]
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['course']),
            models.Index(fields=['template']),
            models.Index(fields=['created_by']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.organization.name} - {self.name}"
    
    @property
    def progress_percentage(self):
        """Get progress percentage"""
        if self.total_certificates == 0:
            return 0
        return (self.processed_certificates / self.total_certificates) * 100
    
    @property
    def is_completed(self):
        """Check if batch is completed"""
        return self.status == 'COMPLETED'
    
    @property
    def is_failed(self):
        """Check if batch failed"""
        return self.status == 'FAILED'
    
    def start_processing(self, started_by=None):
        """Start batch processing"""
        if self.status != 'PENDING':
            raise ValidationError("Only pending batches can be started")
        
        self.status = 'PROCESSING'
        self.processing_started_at = timezone.now()
        self.save(update_fields=['status', 'processing_started_at'])
        
        # Log batch start
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=started_by,
            action='CERTIFICATE_BATCH_START',
            details={
                'batch': str(self.id),
                'name': self.name,
                'total_certificates': self.total_certificates,
            },
            ip_address=started_by.last_login_ip
        )
    
    def complete_processing(self, completed_by=None):
        """Complete batch processing"""
        if self.status != 'PROCESSING':
            raise ValidationError("Only processing batches can be completed")
        
        self.status = 'COMPLETED'
        self.processing_completed_at = timezone.now()
        self.save(update_fields=['status', 'processing_completed_at'])
        
        # Log batch completion
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=completed_by,
            action='CERTIFICATE_BATCH_COMPLETE',
            details={
                'batch': str(self.id),
                'name': self.name,
                'processed_certificates': self.processed_certificates,
                'failed_certificates': self.failed_certificates,
            },
            ip_address=completed_by.last_login_ip
        )
    
    def fail_processing(self, error_message, failed_by=None):
        """Fail batch processing"""
        if self.status != 'PROCESSING':
            raise ValidationError("Only processing batches can be failed")
        
        self.status = 'FAILED'
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message'])
        
        # Log batch failure
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=failed_by,
            action='CERTIFICATE_BATCH_FAIL',
            details={
                'batch': str(self.id),
                'name': self.name,
                'error_message': error_message,
            },
            ip_address=failed_by.last_login_ip
        )
    
    def clean(self):
        """Model validation"""
        errors = {}
        
        # Validate template belongs to same organization
        if self.template.organization != self.organization:
            errors['template'] = "Template must belong to same organization"
        
        # Validate course belongs to same organization
        if self.course.organization != self.organization:
            errors['course'] = "Course must belong to same organization"
        
        # Validate created_by belongs to same organization
        if self.created_by and self.created_by.organization != self.organization:
            errors['created_by'] = "Created by must belong to same organization"
        
        if errors:
            raise ValidationError(errors)
