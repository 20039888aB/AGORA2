from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class LearningPath(models.Model):
    """
    Learning paths for structured course progression
    """
    
    DIFFICULTY_LEVELS = [
        ('BEGINNER', 'Beginner'),
        ('INTERMEDIATE', 'Intermediate'),
        ('ADVANCED', 'Advanced'),
        ('MIXED', 'Mixed'),
    ]
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PUBLISHED', 'Published'),
        ('ARCHIVED', 'Archived'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300, db_index=True)
    description = models.TextField()
    short_description = models.CharField(max_length=500, blank=True)
    
    # Path settings
    difficulty_level = models.CharField(
        max_length=20,
        choices=DIFFICULTY_LEVELS,
        default='BEGINNER',
        db_index=True
    )
    estimated_hours = models.PositiveIntegerField(default=0, help_text="Estimated total hours to complete")
    prerequisites = models.TextField(blank=True, help_text="Prerequisites for this learning path")
    
    # Relationships
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='learning_paths',
        db_index=True
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_learning_paths',
        db_index=True
    )
    
    # Path structure
    is_sequential = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether courses must be taken in sequence"
    )
    allow_skipping = models.BooleanField(
        default=False,
        help_text="Allow learners to skip courses"
    )
    
    # Status and visibility
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        db_index=True
    )
    is_featured = models.BooleanField(default=False, db_index=True)
    
    # Enrollment settings
    max_enrollments = models.PositiveIntegerField(default=0, help_text="0 = unlimited")
    auto_enroll = models.BooleanField(default=False, help_text="Auto-enroll team members")
    certificate_enabled = models.BooleanField(default=True, help_text="Enable completion certificate")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    class Meta:
        db_table = 'learning_paths'
        verbose_name = 'Learning Path'
        verbose_name_plural = 'Learning Paths'
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['created_by', 'created_at']),
            models.Index(fields=['difficulty_level']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['is_sequential']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.organization.name}"
    
    @property
    def total_courses(self):
        """Get total number of courses in this path"""
        return self.path_courses.filter(is_active=True).count()
    
    @property
    def total_enrollments(self):
        """Get total number of enrollments"""
        return self.enrollments.filter(is_active=True).count()
    
    @property
    def is_published(self):
        """Check if learning path is published"""
        return self.status == 'PUBLISHED'
    
    @property
    def is_accessible(self):
        """Check if learning path is accessible to learners"""
        return self.is_active and self.is_published
    
    def can_user_enroll(self, user):
        """Check if user can enroll in this learning path"""
        if not user or not user.is_authenticated:
            return False
        
        # Check organization access
        if user.organization != self.organization:
            return False
        
        # Check if already enrolled
        if self.enrollments.filter(user=user, is_active=True).exists():
            return False
        
        # Check max enrollments
        if self.max_enrollments > 0:
            current_enrollments = self.enrollments.filter(is_active=True).count()
            if current_enrollments >= self.max_enrollments:
                return False
        
        return True
    
    def get_course_progression(self):
        """Get ordered list of courses in this path"""
        return self.path_courses.filter(is_active=True).order_by('order')
    
    def estimate_completion_time(self):
        """Calculate estimated completion time based on course durations"""
        total_hours = 0
        for path_course in self.get_course_progression():
            if path_course.course.duration_hours:
                total_hours += path_course.course.duration_hours
        return total_hours
    
    def clean(self):
        """Model validation"""
        errors = {}
        
        # Validate created_by belongs to same organization
        if self.created_by and self.created_by.organization != self.organization:
            errors['created_by'] = "Creator must belong to same organization"
        
        # Validate estimated hours
        if self.estimated_hours < 0:
            errors['estimated_hours'] = "Estimated hours cannot be negative"
        
        # Validate max enrollments
        if self.max_enrollments < 0:
            errors['max_enrollments'] = "Max enrollments cannot be negative"
        
        if errors:
            raise ValidationError(errors)


class PathCourse(models.Model):
    """
    Individual courses within a learning path
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    learning_path = models.ForeignKey(
        LearningPath,
        on_delete=models.CASCADE,
        related_name='path_courses',
        db_index=True
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='path_courses',
        db_index=True
    )
    
    # Course position and settings
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_required = models.BooleanField(default=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Prerequisites within the path
    prerequisites = models.ManyToManyField(
        'self',
        symmetrical=False,
        blank=True,
        related_name='dependent_courses',
        help_text="Courses that must be completed before this one"
    )
    
    # Time estimates
    estimated_hours_override = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Override course duration for this path"
    )
    
    # Additional settings
    custom_description = models.TextField(blank=True)
    learning_objectives = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'path_courses'
        verbose_name = 'Path Course'
        verbose_name_plural = 'Path Courses'
        constraints = [
            models.UniqueConstraint(
                fields=['learning_path', 'course'],
                name='unique_path_course'
            ),
        ]
        indexes = [
            models.Index(fields=['learning_path', 'order']),
            models.Index(fields=['course']),
            models.Index(fields=['is_required']),
            models.Index(fields=['is_active']),
        ]
        ordering = ['learning_path', 'order']
    
    def __str__(self):
        return f"{self.learning_path.title} - {self.course.title}"
    
    @property
    def effective_duration_hours(self):
        """Get effective duration (override or course duration)"""
        if self.estimated_hours_override:
            return self.estimated_hours_override
        return self.course.duration_hours or 0
    
    @property
    def has_prerequisites(self):
        """Check if this course has prerequisites within the path"""
        return self.prerequisites.exists()
    
    def get_prerequisites_list(self):
        """Get list of prerequisite courses"""
        return self.prerequisites.filter(is_active=True).order_by('order')
    
    def clean(self):
        """Model validation"""
        errors = {}
        
        # Validate course belongs to same organization as learning path
        if self.course.organization != self.learning_path.organization:
            errors['course'] = "Course must belong to same organization as learning path"
        
        # Validate estimated hours
        if self.estimated_hours_override is not None and self.estimated_hours_override < 0:
            errors['estimated_hours_override'] = "Estimated hours cannot be negative"
        
        if errors:
            raise ValidationError(errors)


class PathEnrollment(models.Model):
    """
    User enrollments in learning paths
    """
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('PAUSED', 'Paused'),
        ('DROPPED', 'Dropped'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    learning_path = models.ForeignKey(
        LearningPath,
        on_delete=models.CASCADE,
        related_name='enrollments',
        db_index=True
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='path_enrollments',
        db_index=True
    )
    
    # Enrollment settings
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE',
        db_index=True
    )
    progress_percentage = models.FloatField(default=0.0, db_index=True)
    
    # Timeline
    enrolled_at = models.DateTimeField(auto_now_add=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_activity_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Additional settings
    deadline = models.DateTimeField(null=True, blank=True, db_index=True)
    notes = models.TextField(blank=True)
    
    # Enrollment tracking
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_path_enrollments',
        db_index=True
    )
    
    class Meta:
        db_table = 'path_enrollments'
        verbose_name = 'Path Enrollment'
        verbose_name_plural = 'Path Enrollments'
        constraints = [
            models.UniqueConstraint(
                fields=['learning_path', 'user'],
                name='unique_path_user_enrollment'
            ),
        ]
        indexes = [
            models.Index(fields=['learning_path', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['enrolled_at']),
            models.Index(fields=['completed_at']),
            models.Index(fields=['progress_percentage']),
        ]
        ordering = ['-enrolled_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.learning_path.title} ({self.status})"
    
    @property
    def is_active(self):
        """Check if enrollment is active"""
        return self.status == 'ACTIVE'
    
    @property
    def is_completed(self):
        """Check if enrollment is completed"""
        return self.status == 'COMPLETED'
    
    @property
    def days_enrolled(self):
        """Calculate days since enrollment"""
        if self.enrolled_at:
            return (timezone.now() - self.enrolled_at).days
        return 0
    
    @property
    def completion_time_days(self):
        """Calculate days to completion"""
        if self.completed_at and self.enrolled_at:
            return (self.completed_at - self.enrolled_at).days
        return None
    
    def update_progress(self):
        """Update progress based on course completions"""
        from enrollments.models import Enrollment
        
        # Get all courses in the learning path
        path_courses = self.learning_path.get_course_progression()
        total_courses = path_courses.count()
        
        if total_courses == 0:
            self.progress_percentage = 0.0
            self.save(update_fields=['progress_percentage'])
            return
        
        # Count completed courses
        completed_courses = 0
        for path_course in path_courses:
            if Enrollment.objects.filter(
                user=self.user,
                course=path_course.course,
                status='COMPLETED'
            ).exists():
                completed_courses += 1
        
        # Calculate progress
        self.progress_percentage = (completed_courses / total_courses) * 100
        
        # Check if completed
        if completed_courses == total_courses and self.status == 'ACTIVE':
            self.status = 'COMPLETED'
            self.completed_at = timezone.now()
        
        # Update last activity
        self.last_activity_at = timezone.now()
        
        self.save(update_fields=['progress_percentage', 'status', 'completed_at', 'last_activity_at'])
    
    def start_enrollment(self):
        """Mark enrollment as started"""
        if not self.started_at:
            self.started_at = timezone.now()
            self.status = 'ACTIVE'
            self.save(update_fields=['started_at', 'status'])
    
    def complete_enrollment(self):
        """Mark enrollment as completed"""
        self.status = 'COMPLETED'
        self.completed_at = timezone.now()
        self.progress_percentage = 100.0
        self.save(update_fields=['status', 'completed_at', 'progress_percentage'])
    
    def pause_enrollment(self):
        """Pause enrollment"""
        self.status = 'PAUSED'
        self.save(update_fields=['status'])
    
    def resume_enrollment(self):
        """Resume paused enrollment"""
        self.status = 'ACTIVE'
        self.save(update_fields=['status'])


class PathProgress(models.Model):
    """
    Track progress for individual courses within a learning path
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    path_enrollment = models.ForeignKey(
        PathEnrollment,
        on_delete=models.CASCADE,
        related_name='course_progress',
        db_index=True
    )
    path_course = models.ForeignKey(
        PathCourse,
        on_delete=models.CASCADE,
        related_name='progress_records',
        db_index=True
    )
    
    # Progress tracking
    is_started = models.BooleanField(default=False, db_index=True)
    is_completed = models.BooleanField(default=False, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Additional data
    time_spent_hours = models.FloatField(default=0.0)
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'path_progress'
        verbose_name = 'Path Progress'
        verbose_name_plural = 'Path Progress'
        constraints = [
            models.UniqueConstraint(
                fields=['path_enrollment', 'path_course'],
                name='unique_enrollment_course_progress'
            ),
        ]
        indexes = [
            models.Index(fields=['path_enrollment', 'is_completed']),
            models.Index(fields=['path_course', 'is_completed']),
            models.Index(fields=['started_at']),
            models.Index(fields=['completed_at']),
        ]
        ordering = ['path_enrollment', 'path_course__order']
    
    def __str__(self):
        return f"{self.path_enrollment.user.email} - {self.path_course.course.title}"
    
    def start_course(self):
        """Mark course as started"""
        if not self.is_started:
            self.is_started = True
            self.started_at = timezone.now()
            self.save(update_fields=['is_started', 'started_at'])
    
    def complete_course(self):
        """Mark course as completed"""
        self.is_completed = True
        self.completed_at = timezone.now()
        self.save(update_fields=['is_completed', 'completed_at'])
        
        # Update overall enrollment progress
        self.path_enrollment.update_progress()
