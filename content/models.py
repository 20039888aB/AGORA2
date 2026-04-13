from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
import uuid
import os
import hashlib

User = get_user_model()


class ContentFile(models.Model):
    """
    Content files uploaded by managers and admins
    """
    
    FILE_TYPES = [
        ('PDF', 'PDF Document'),
        ('DOC', 'Word Document'),
        ('PPT', 'PowerPoint'),
        ('TXT', 'Text File'),
        ('VIDEO', 'Video File'),
        ('AUDIO', 'Audio File'),
        ('IMAGE', 'Image File'),
        ('ARCHIVE', 'Archive File'),
        ('OTHER', 'Other File'),
    ]
    
    STATUS_CHOICES = [
        ('UPLOADING', 'Uploading'),
        ('UPLOADED', 'Uploaded'),
        ('PROCESSING', 'Processing'),
        ('READY', 'Ready'),
        ('FAILED', 'Failed'),
        ('DELETED', 'Deleted'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300, db_index=True)
    description = models.TextField(blank=True)
    
    # File information
    file = models.FileField(upload_to='content/files/')
    original_filename = models.CharField(max_length=500, db_index=True)
    file_type = models.CharField(
        max_length=20,
        choices=FILE_TYPES,
        db_index=True
    )
    mime_type = models.CharField(max_length=100, blank=True)
    file_size = models.BigIntegerField(default=0, db_index=True)
    file_hash = models.CharField(max_length=64, unique=True, db_index=True)
    
    # Relationships
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='content_uploaded_files',
        db_index=True
    )
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='content_files',
        db_index=True
    )
    
    # File categorization
    category = models.CharField(
        max_length=50,
        choices=[
            ('TRAINING', 'Training Material'),
            ('DOCUMENT', 'Document'),
            ('MEDIA', 'Media File'),
            ('TEMPLATE', 'Template'),
            ('REFERENCE', 'Reference Material'),
            ('OTHER', 'Other'),
        ],
        default='TRAINING',
        db_index=True
    )
    
    # Access control
    is_public = models.BooleanField(default=False, db_index=True)
    allow_download = models.BooleanField(default=True, db_index=True)
    access_level = models.CharField(
        max_length=20,
        choices=[
            ('ALL', 'All Organization Members'),
            ('MANAGERS', 'Managers Only'),
            ('ADMINS', 'Admins Only'),
            ('SPECIFIC', 'Specific Users'),
        ],
        default='ALL',
        db_index=True
    )
    
    # Processing and status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='UPLOADING',
        db_index=True
    )
    upload_progress = models.PositiveIntegerField(default=0, db_index=True)
    processing_error = models.TextField(blank=True)
    
    # Version control
    version = models.PositiveIntegerField(default=1)
    parent_file = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='versions',
        db_index=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    uploaded_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    class Meta:
        db_table = 'content_files'
        verbose_name = 'Content File'
        verbose_name_plural = 'Content Files'
        indexes = [
            models.Index(fields=['organization', 'created_at']),
            models.Index(fields=['uploaded_by', 'created_at']),
            models.Index(fields=['file_type']),
            models.Index(fields=['category']),
            models.Index(fields=['status']),
            models.Index(fields=['is_public']),
            models.Index(fields=['access_level']),
            models.Index(fields=['file_hash']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.original_filename})"
    
    @property
    def file_extension(self):
        """Get file extension"""
        if self.original_filename:
            return self.original_filename.split('.')[-1].lower()
        return ''
    
    @property
    def file_size_display(self):
        """Get human-readable file size"""
        if not self.file_size or self.file_size == 0:
            return '0 bytes'
        
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    @property
    def is_ready(self):
        """Check if file is ready for use"""
        return self.status == 'READY'
    
    @property
    def upload_complete(self):
        """Check if upload is complete"""
        return self.status in ['UPLOADED', 'PROCESSING', 'READY']
    
    def can_user_access(self, user):
        """Check if user can access this file"""
        if not user or not user.is_authenticated:
            return self.is_public
        
        # Superadmins can access all files
        if user.is_superadmin():
            return True
        
        # Check organization access
        if user.organization != self.organization:
            return False
        
        # Check access level
        if self.access_level == 'ALL':
            return True
        elif self.access_level == 'MANAGERS':
            return user.is_manager_or_above()
        elif self.access_level == 'ADMINS':
            return user.is_admin_or_above()
        elif self.access_level == 'SPECIFIC':
            # For now, return False - can be extended with specific user permissions
            return False
        
        return False
    
    def can_user_download(self, user):
        """Check if user can download this file"""
        return self.can_user_access(user) and self.allow_download and self.is_ready
    
    def generate_file_hash(self):
        """Generate SHA-256 hash of the file"""
        if not self.file:
            return None
        
        hash_sha256 = hashlib.sha256()
        
        # Reset file pointer
        self.file.seek(0)
        
        # Read file in chunks to handle large files
        for chunk in self.file.chunks():
            hash_sha256.update(chunk)
        
        # Reset file pointer again
        self.file.seek(0)
        
        return hash_sha256.hexdigest()
    
    def determine_file_type(self):
        """Determine file type based on extension"""
        if not self.original_filename:
            return 'OTHER'
        
        extension = self.file_extension.lower()
        
        if extension == 'pdf':
            return 'PDF'
        elif extension in ['doc', 'docx']:
            return 'DOC'
        elif extension in ['ppt', 'pptx']:
            return 'PPT'
        elif extension in ['txt', 'md']:
            return 'TXT'
        elif extension in ['mp4', 'avi', 'mov', 'wmv', 'flv']:
            return 'VIDEO'
        elif extension in ['mp3', 'wav', 'flac', 'aac']:
            return 'AUDIO'
        elif extension in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg']:
            return 'IMAGE'
        elif extension in ['zip', 'rar', '7z', 'tar', 'gz']:
            return 'ARCHIVE'
        else:
            return 'OTHER'
    
    def update_upload_progress(self, progress):
        """Update upload progress"""
        if 0 <= progress <= 100:
            self.upload_progress = progress
            if progress == 100:
                self.status = 'UPLOADED'
                self.uploaded_at = timezone.now()
            self.save(update_fields=['upload_progress', 'status', 'uploaded_at'])
    
    def mark_as_ready(self):
        """Mark file as ready for use"""
        self.status = 'READY'
        self.upload_progress = 100
        self.save(update_fields=['status', 'upload_progress'])
    
    def mark_as_failed(self, error_message):
        """Mark file upload as failed"""
        self.status = 'FAILED'
        self.processing_error = error_message
        self.save(update_fields=['status', 'processing_error'])
    
    def create_new_version(self, new_file, new_title=None):
        """Create a new version of this file"""
        # Mark current version as not the latest
        self.is_latest_version = False
        self.save(update_fields=['is_latest_version'])
        
        # Create new version
        new_file_obj = ContentFile.objects.create(
            title=new_title or self.title,
            description=self.description,
            file=new_file,
            original_filename=new_file.name,
            file_type=self.determine_file_type(),
            uploaded_by=self.uploaded_by,
            organization=self.organization,
            category=self.category,
            is_public=self.is_public,
            allow_download=self.allow_download,
            access_level=self.access_level,
            version=self.version + 1,
            parent_file=self
        )
        
        return new_file_obj
    
    def save(self, *args, **kwargs):
        """Override save to handle file processing"""
        is_new = self.pk is None
        
        # Set file metadata if file is provided
        if self.file and hasattr(self.file, 'size'):
            self.file_size = self.file.size
            
            # Generate file hash if not set
            if not self.file_hash:
                self.file_hash = self.generate_file_hash()
            
            # Determine file type if not set
            if not self.file_type:
                self.file_type = self.determine_file_type()
        
        # Set uploaded_at if this is a new file and status is UPLOADED
        if is_new and self.status == 'UPLOADED' and not self.uploaded_at:
            self.uploaded_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Model validation"""
        errors = {}
        
        # Validate uploaded_by belongs to same organization
        if self.uploaded_by and self.uploaded_by.organization != self.organization:
            errors['uploaded_by'] = "File uploader must belong to same organization"
        
        # Validate parent file belongs to same organization
        if self.parent_file and self.parent_file.organization != self.organization:
            errors['parent_file'] = "Parent file must belong to same organization"
        
        # Validate file size
        if self.file_size < 0:
            errors['file_size'] = "File size cannot be negative"
        
        # Validate version
        if self.version <= 0:
            errors['version'] = "Version must be greater than 0"
        
        if errors:
            raise ValidationError(errors)


class FileDownloadLog(models.Model):
    """
    Track file downloads
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(
        ContentFile,
        on_delete=models.CASCADE,
        related_name='download_logs',
        db_index=True
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='file_downloads',
        db_index=True
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Timestamps
    downloaded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'file_download_logs'
        verbose_name = 'File Download Log'
        verbose_name_plural = 'File Download Logs'
        indexes = [
            models.Index(fields=['file', 'downloaded_at']),
            models.Index(fields=['user', 'downloaded_at']),
            models.Index(fields=['downloaded_at']),
        ]
        ordering = ['-downloaded_at']
    
    def __str__(self):
        user_info = f"by {self.user.email}" if self.user else "by anonymous"
        return f"{self.file.title} downloaded {user_info}"


class FileShare(models.Model):
    """
    File sharing links
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(
        ContentFile,
        on_delete=models.CASCADE,
        related_name='shares',
        db_index=True
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_shares',
        db_index=True
    )
    
    # Share settings
    share_token = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    max_downloads = models.PositiveIntegerField(default=0, blank=True)  # 0 = unlimited
    password = models.CharField(max_length=255, blank=True)
    allow_download = models.BooleanField(default=True)
    
    # Status
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    last_accessed = models.DateTimeField(null=True, blank=True, db_index=True)
    
    class Meta:
        db_table = 'file_shares'
        verbose_name = 'File Share'
        verbose_name_plural = 'File Shares'
        indexes = [
            models.Index(fields=['file', 'created_at']),
            models.Index(fields=['created_by', 'created_at']),
            models.Index(fields=['share_token']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['is_active']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Share for {self.file.title}"
    
    @property
    def is_expired(self):
        """Check if share has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    @property
    def download_count(self):
        """Get number of downloads"""
        return self.download_logs.count()
    
    @property
    def can_download(self):
        """Check if file can be downloaded through this share"""
        return (self.is_active and 
                not self.is_expired and 
                self.allow_download and
                (self.max_downloads == 0 or self.download_count < self.max_downloads))
    
    def generate_share_token(self):
        """Generate unique share token"""
        import secrets
        return secrets.token_urlsafe(48)
    
    def log_download(self, user=None, ip_address=None, user_agent=None):
        """Log a download through this share"""
        FileDownloadLog.objects.create(
            file=self.file,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent
        )
        self.last_accessed = timezone.now()
        self.save(update_fields=['last_accessed'])
    
    def save(self, *args, **kwargs):
        """Override save to generate share token"""
        if not self.share_token:
            self.share_token = self.generate_share_token()
        super().save(*args, **kwargs)


class ContentLink(models.Model):
    """External links shared by managers/admins with their organization."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300, db_index=True)
    description = models.TextField(blank=True)
    url = models.URLField(max_length=1000)
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='content_links',
        db_index=True
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='content_links_uploaded',
        db_index=True
    )
    category = models.CharField(
        max_length=20,
        choices=[
            ('VIDEO', 'Video Link'),
            ('AUDIO', 'Audio Link'),
            ('ARTICLE', 'Article Link'),
            ('REFERENCE', 'Reference Link'),
            ('OTHER', 'Other Link'),
        ],
        default='REFERENCE',
        db_index=True
    )
    access_level = models.CharField(
        max_length=20,
        choices=[
            ('ALL', 'All Organization Members'),
            ('MANAGERS', 'Managers Only'),
            ('ADMINS', 'Admins Only'),
        ],
        default='ALL',
        db_index=True
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'content_links'
        verbose_name = 'Content Link'
        verbose_name_plural = 'Content Links'
        indexes = [
            models.Index(fields=['organization', 'created_at']),
            models.Index(fields=['uploaded_by', 'created_at']),
            models.Index(fields=['category']),
            models.Index(fields=['access_level']),
            models.Index(fields=['is_active']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class CourseApproval(models.Model):
    """
    Course approval workflow for manager-created courses
    """
    
    APPROVAL_STATUS = [
        ('PENDING', 'Pending Review'),
        ('UNDER_REVIEW', 'Under Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('RETURNED', 'Returned for Changes'),
        ('EXPIRED', 'Expired'),
    ]
    
    PRIORITY_LEVELS = [
        ('LOW', 'Low'),
        ('NORMAL', 'Normal'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.OneToOneField(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='approval_request',
        db_index=True
    )
    
    # Approval workflow
    status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS,
        default='PENDING',
        db_index=True
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_LEVELS,
        default='NORMAL',
        db_index=True
    )
    
    # People involved
    submitted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submitted_approvals',
        db_index=True
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_approvals',
        db_index=True
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_approvals',
        db_index=True
    )
    
    # Review details
    review_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    required_changes = models.JSONField(default=list, blank=True)
    
    # Timeline
    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    reviewed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    approved_at = models.DateTimeField(null=True, blank=True, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Review criteria
    content_quality_score = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="1-10 scale for content quality"
    )
    technical_quality_score = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="1-10 scale for technical quality"
    )
    educational_value_score = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="1-10 scale for educational value"
    )
    
    # Automated checks
    plagiarism_check_passed = models.BooleanField(default=False)
    accessibility_check_passed = models.BooleanField(default=False)
    technical_check_passed = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'course_approvals'
        verbose_name = 'Course Approval'
        verbose_name_plural = 'Course Approvals'
        indexes = [
            models.Index(fields=['course', 'status']),
            models.Index(fields=['submitted_by', 'submitted_at']),
            models.Index(fields=['reviewed_by', 'reviewed_at']),
            models.Index(fields=['approved_by', 'approved_at']),
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['submitted_at']),
            models.Index(fields=['expires_at']),
        ]
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"Approval for {self.course.title} ({self.status})"
    
    @property
    def is_pending(self):
        """Check if approval is pending"""
        return self.status in ['PENDING', 'UNDER_REVIEW']
    
    @property
    def is_approved(self):
        """Check if course is approved"""
        return self.status == 'APPROVED'
    
    @property
    def is_rejected(self):
        """Check if course is rejected"""
        return self.status == 'REJECTED'
    
    @property
    def is_expired(self):
        """Check if approval request has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    @property
    def days_pending(self):
        """Calculate days since submission"""
        if self.submitted_at:
            return (timezone.now() - self.submitted_at).days
        return 0
    
    @property
    def review_duration_days(self):
        """Calculate review duration in days"""
        if self.reviewed_at and self.submitted_at:
            return (self.reviewed_at - self.submitted_at).days
        return None
    
    @property
    def average_score(self):
        """Calculate average quality score"""
        scores = [
            self.content_quality_score,
            self.technical_quality_score,
            self.educational_value_score
        ]
        valid_scores = [s for s in scores if s is not None]
        if valid_scores:
            return sum(valid_scores) / len(valid_scores)
        return None
    
    def can_user_review(self, user):
        """Check if user can review this approval"""
        if not user or not user.is_authenticated:
            return False
        
        # Must be admin or superadmin
        if not user.is_admin_or_above():
            return False
        
        # Must belong to same organization (unless superadmin)
        if not user.is_superadmin() and user.organization != self.course.organization:
            return False
        
        # Cannot review own submission
        if self.submitted_by == user:
            return False
        
        # Can only review pending approvals
        if not self.is_pending:
            return False
        
        return True
    
    def submit_for_approval(self, submitted_by, priority='NORMAL', expires_days=None):
        """Submit course for approval"""
        self.status = 'PENDING'
        self.submitted_by = submitted_by
        self.priority = priority
        self.submitted_at = timezone.now()
        
        if expires_days:
            self.expires_at = timezone.now() + timedelta(days=expires_days)
        
        self.save(update_fields=['status', 'submitted_by', 'priority', 'submitted_at', 'expires_at'])
    
    def start_review(self, reviewed_by):
        """Start the review process"""
        if self.can_user_review(reviewed_by):
            self.status = 'UNDER_REVIEW'
            self.reviewed_by = reviewed_by
            self.reviewed_at = timezone.now()
            self.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
            return True
        return False
    
    def approve(self, approved_by, notes=None, content_score=None, technical_score=None, educational_score=None):
        """Approve the course"""
        if self.can_user_review(approved_by):
            self.status = 'APPROVED'
            self.approved_by = approved_by
            self.approved_at = timezone.now()
            
            if notes:
                self.review_notes = notes
            
            if content_score:
                self.content_quality_score = content_score
            if technical_score:
                self.technical_quality_score = technical_score
            if educational_score:
                self.educational_value_score = educational_score
            
            # Update course status
            self.course.status = 'PUBLISHED'
            self.course.save(update_fields=['status'])
            
            self.save(update_fields=[
                'status', 'approved_by', 'approved_at', 'review_notes',
                'content_quality_score', 'technical_quality_score', 'educational_value_score'
            ])
            return True
        return False
    
    def reject(self, reviewed_by, reason=None, required_changes=None):
        """Reject the course"""
        if self.can_user_review(reviewed_by):
            self.status = 'REJECTED'
            self.reviewed_by = reviewed_by
            self.reviewed_at = timezone.now()
            
            if reason:
                self.rejection_reason = reason
            if required_changes:
                self.required_changes = required_changes
            
            # Update course status
            self.course.status = 'ARCHIVED'
            self.course.save(update_fields=['status'])
            
            self.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'rejection_reason', 'required_changes'])
            return True
        return False
    
    def return_for_changes(self, reviewed_by, notes=None, required_changes=None):
        """Return course for changes"""
        if self.can_user_review(reviewed_by):
            self.status = 'RETURNED'
            self.reviewed_by = reviewed_by
            self.reviewed_at = timezone.now()
            
            if notes:
                self.review_notes = notes
            if required_changes:
                self.required_changes = required_changes
            
            self.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'review_notes', 'required_changes'])
            return True
        return False
    
    def resubmit(self):
        """Resubmit returned course for approval"""
        if self.status == 'RETURNED':
            self.status = 'PENDING'
            self.reviewed_by = None
            self.reviewed_at = None
            self.review_notes = ''
            self.rejection_reason = ''
            self.required_changes = []
            self.submitted_at = timezone.now()
            
            self.save(update_fields=[
                'status', 'reviewed_by', 'reviewed_at', 'review_notes',
                'rejection_reason', 'required_changes', 'submitted_at'
            ])
            return True
        return False
    
    def run_automated_checks(self):
        """Run automated quality checks"""
        # Placeholder for automated checks
        # In a real implementation, this would check:
        # - Plagiarism detection
        # - Accessibility compliance
        # - Technical quality (broken links, media files, etc.)
        
        self.plagiarism_check_passed = True
        self.accessibility_check_passed = True
        self.technical_check_passed = True
        
        self.save(update_fields=[
            'plagiarism_check_passed',
            'accessibility_check_passed',
            'technical_check_passed'
        ])
    
    def clean(self):
        """Model validation"""
        errors = {}
        
        # Validate reviewers belong to same organization
        if self.reviewed_by and not self.reviewed_by.is_superadmin():
            if self.reviewed_by.organization != self.course.organization:
                errors['reviewed_by'] = "Reviewer must belong to same organization"
        
        if self.approved_by and not self.approved_by.is_superadmin():
            if self.approved_by.organization != self.course.organization:
                errors['approved_by'] = "Approver must belong to same organization"
        
        # Validate score ranges
        for score_field in ['content_quality_score', 'technical_quality_score', 'educational_value_score']:
            score = getattr(self, score_field)
            if score is not None and (score < 1 or score > 10):
                errors[score_field] = "Score must be between 1 and 10"
        
        if errors:
            raise ValidationError(errors)
