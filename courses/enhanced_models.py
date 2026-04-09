from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class EnhancedCourse(models.Model):
    """
    Enhanced Course model with integrated file upload and proper frontend integration
    """
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PUBLISHED', 'Published'),
        ('ARCHIVED', 'Archived'),
    ]
    
    DIFFICULTY_CHOICES = [
        ('BEGINNER', 'Beginner'),
        ('INTERMEDIATE', 'Intermediate'),
        ('ADVANCED', 'Advanced'),
        ('EXPERT', 'Expert'),
    ]
    
    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300, db_index=True)
    slug = models.SlugField(max_length=300, db_index=True)
    description = models.TextField()
    short_description = models.CharField(max_length=500, blank=True)
    
    # Course Details
    difficulty = models.CharField(
        max_length=20,
        choices=DIFFICULTY_CHOICES,
        default='BEGINNER',
        db_index=True
    )
    duration_hours = models.PositiveIntegerField(default=0)
    max_students = models.PositiveIntegerField(default=50)
    language = models.CharField(max_length=10, default='en')
    
    # Category (Frontend compatible)
    category = models.CharField(
        max_length=50,
        choices=[
            ('technical', 'Technical Skills'),
            ('sales', 'Sales & Marketing'),
            ('compliance', 'Compliance'),
            ('management', 'Management'),
        ],
        default='technical',
        db_index=True
    )
    
    # Learning Content
    prerequisites = models.TextField(blank=True)
    objectives = models.TextField(blank=True)
    outcomes = models.TextField(blank=True)
    
    # Settings
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        db_index=True
    )
    certificate_enabled = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    
    # File Upload Integration
    course_file = models.FileField(
        upload_to='course_files/',
        blank=True,
        null=True,
        help_text="Main course file (PDF, video, etc.)"
    )
    
    # Organization and Creator
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='enhanced_courses',
        db_index=True
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_courses',
        db_index=True
    )
    
    # Metadata
    tags = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'enhanced_courses'
        verbose_name = 'Enhanced Course'
        verbose_name_plural = 'Enhanced Courses'
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'slug'],
                name='unique_enhanced_org_course_slug'
            ),
        ]
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['created_by']),
            models.Index(fields=['category']),
            models.Index(fields=['difficulty']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['organization', '-created_at']
    
    def __str__(self):
        return f"{self.organization.name} - {self.title}"
    
    @property
    def is_published(self):
        """Check if course is published"""
        return self.status == 'PUBLISHED'
    
    @property
    def is_accessible(self):
        """Check if course is accessible to students"""
        return self.is_active and self.is_published
    
    @property
    def total_enrollments(self):
        """Get total enrollments in this course"""
        from enrollments.models import Enrollment
        return Enrollment.objects.filter(
            course=self,
            is_active=True
        ).count()
    
    def get_status_display(self):
        """Get human-readable status"""
        return dict(self.STATUS_CHOICES).get(self.status, self.status)
    
    def get_difficulty_display(self):
        """Get human-readable difficulty"""
        return dict(self.DIFFICULTY_CHOICES).get(self.difficulty, self.difficulty)
    
    def get_category_display(self):
        """Get human-readable category"""
        category_choices = dict(self._meta.get_field('category').choices)
        return category_choices.get(self.category, self.category)
    
    def clean(self):
        """Enhanced model validation"""
        errors = {}
        
        # Validate creator belongs to same organization
        if self.created_by and self.created_by.organization != self.organization:
            errors['created_by'] = "Creator must belong to same organization"
        
        # Validate duration
        if self.duration_hours <= 0:
            errors['duration_hours'] = "Duration must be greater than 0"
        
        # Validate max students
        if self.max_students <= 0:
            errors['max_students'] = "Max students must be greater than 0"
        
        if errors:
            raise ValidationError(errors)
    
    def can_be_edited_by(self, user):
        """Check if user can edit this course"""
        if user.is_superadmin():
            return True
        if user.is_admin_or_above() and user.organization == self.organization:
            return True
        if user == self.created_by:
            return True
        return False
    
    def can_be_deleted_by(self, user):
        """Check if user can delete this course"""
        if user.is_superadmin():
            return True
        if user.is_admin_or_above() and user.organization == self.organization:
            return True
        return False


class CourseFile(models.Model):
    """
    Individual course files with metadata and tracking
    """
    
    FILE_TYPES = [
        ('PDF', 'PDF Document'),
        ('VIDEO', 'Video File'),
        ('AUDIO', 'Audio File'),
        ('IMAGE', 'Image File'),
        ('DOCUMENT', 'Other Document'),
        ('ARCHIVE', 'Archive File'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(
        EnhancedCourse,
        on_delete=models.CASCADE,
        related_name='files',
        db_index=True
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # File Information
    file = models.FileField(upload_to='course_files/')
    file_type = models.CharField(
        max_length=20,
        choices=FILE_TYPES,
        default='PDF'
    )
    file_size = models.BigIntegerField(default=0)
    mime_type = models.CharField(max_length=100, blank=True)
    
    # Organization and Tracking
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_files'
    )
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='course_files',
        db_index=True
    )
    
    # Metadata
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=True)
    is_downloadable = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'course_files'
        verbose_name = 'Course File'
        verbose_name_plural = 'Course Files'
        constraints = [
            models.UniqueConstraint(
                fields=['course', 'title'],
                name='unique_course_file_title'
            ),
        ]
        indexes = [
            models.Index(fields=['course', 'order']),
            models.Index(fields=['course', 'file_type']),
            models.Index(fields=['organization']),
            models.Index(fields=['uploaded_by']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['course', 'order', 'created_at']
    
    def __str__(self):
        return f"{self.title} - {self.course.title}"
    
    @property
    def file_size_display(self):
        """Get human-readable file size"""
        if not self.file_size:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.file_size < 1024.0:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024.0
        return f"{self.file_size:.1f} TB"
    
    def get_file_type_display(self):
        """Get human-readable file type"""
        return dict(self.FILE_TYPES).get(self.file_type, self.file_type)
    
    def clean(self):
        """File validation"""
        errors = {}
        
        # Validate uploader belongs to same organization
        if self.uploaded_by and self.uploaded_by.organization != self.organization:
            errors['uploaded_by'] = "Uploader must belong to same organization"
        
        # Validate file size (max 50MB)
        if self.file and self.file.size > 50 * 1024 * 1024:
            errors['file'] = "File size cannot exceed 50MB"
        
        if errors:
            raise ValidationError(errors)
