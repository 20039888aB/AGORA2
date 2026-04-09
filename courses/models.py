from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class Category(models.Model):
    """
    Course categories with hierarchical structure
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        db_index=True
    )
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='categories',
        db_index=True
    )
    
    # Status and timestamps
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'categories'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'slug'],
                name='unique_org_category_slug'
            ),
        ]
        indexes = [
            models.Index(fields=['organization', 'parent']),
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['organization', 'name']
    
    def __str__(self):
        return f"{self.organization.name} - {self.name}"
    
    @property
    def full_path(self):
        """Get full hierarchical path"""
        path = [self.name]
        current = self.parent
        while current:
            path.append(current.name)
            current = current.parent
        return " → ".join(reversed(path))
    
    @property
    def level(self):
        """Get category level in hierarchy"""
        level = 0
        current = self.parent
        while current:
            level += 1
            current = current.parent
        return level
    
    @property
    def total_courses(self):
        """Get total courses in this category"""
        return self.courses.filter(is_active=True).count()
    
    @property
    def total_subcategories(self):
        """Get total subcategories"""
        return self.children.filter(is_active=True).count()
    
    def clean(self):
        """Model validation"""
        errors = {}
        
        # Validate hierarchy - prevent cycles
        if self.parent and self.parent == self:
            errors['parent'] = "Category cannot be its own parent"
        
        # Validate parent belongs to same organization
        if self.parent and self.parent.organization != self.organization:
            errors['parent'] = "Parent category must belong to same organization"
        
        if errors:
            raise ValidationError(errors)


class Course(models.Model):
    """
    Main course model with comprehensive metadata and PDF document support
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
    
    VISIBILITY_CHOICES = [
        ('ORGANIZATION', 'Organization Wide'),
        ('MANAGERS', 'Managers Only'),
        ('SPECIFIC', 'Specific Groups'),
        ('PUBLIC', 'Public'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300, db_index=True)
    slug = models.SlugField(max_length=300, unique=True, db_index=True)
    description = models.TextField(blank=True)
    short_description = models.CharField(max_length=500, blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='courses',
        db_index=True
    )
    instructor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='instructed_courses',
        db_index=True
    )
    thumbnail = models.ImageField(upload_to='courses/thumbnails/', blank=True, null=True)
    
    # Course PDF document - main course material
    course_pdf = models.FileField(
        upload_to='courses/pdfs/',
        blank=True,
        null=True,
        help_text='Main course PDF document that will be visible to all students in the organization'
    )
    pdf_title = models.CharField(
        max_length=255,
        blank=True,
        help_text='Title for the PDF document'
    )
    pdf_description = models.TextField(
        blank=True,
        help_text='Description for the PDF document'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        db_index=True
    )
    difficulty = models.CharField(
        max_length=20,
        choices=DIFFICULTY_CHOICES,
        default='BEGINNER',
        db_index=True
    )
    duration_hours = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    prerequisites = models.TextField(blank=True)
    objectives = models.TextField(blank=True)
    outcomes = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    language = models.CharField(max_length=10, default='en')
    max_students = models.PositiveIntegerField(default=0)
    certificate_enabled = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    
    # Enhanced visibility settings
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default='ORGANIZATION',
        db_index=True,
        help_text='Who can see this course'
    )
    show_in_dashboard = models.BooleanField(
        default=True,
        db_index=True,
        help_text='Show this course in all dashboards'
    )
    allow_organization_access = models.BooleanField(
        default=True,
        db_index=True,
        help_text='Allow all organization members to access this course'
    )
    
    # Organization relationship
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='courses',
        db_index=True
    )
    
    # Status and timestamps
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'courses'
        verbose_name = 'Course'
        verbose_name_plural = 'Courses'
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'slug'],
                name='unique_org_course_slug'
            ),
        ]
        indexes = [
            models.Index(fields=['organization', 'category']),
            models.Index(fields=['status', 'is_active']),
            models.Index(fields=['instructor']),
            models.Index(fields=['difficulty']),
            models.Index(fields=['created_at']),
            models.Index(fields=['price']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['visibility']),
            models.Index(fields=['show_in_dashboard']),
            models.Index(fields=['allow_organization_access']),
        ]
        ordering = ['organization', '-created_at']
    
    def __str__(self):
        return f"{self.organization.name} - {self.title}"
    
    @property
    def total_modules(self):
        """Get total modules in this course"""
        return self.modules.filter(is_active=True).count()
    
    @property
    def total_lessons(self):
        """Get total lessons in this course"""
        return self.lessons.filter(is_active=True).count()
    
    @property
    def total_enrollments(self):
        """Get total enrollments in this course"""
        from enrollments.models import Enrollment
        return Enrollment.objects.filter(
            course=self,
            is_active=True
        ).count()
    
    @property
    def is_published(self):
        """Check if course is published"""
        return self.status == 'PUBLISHED'
    
    @property
    def is_accessible(self):
        """Check if course is accessible to students"""
        return self.is_active and self.is_published
    
    @property
    def has_pdf_document(self):
        """Check if course has a PDF document"""
        return self.course_pdf and bool(self.course_pdf.name)
    
    @property
    def pdf_filename(self):
        """Get PDF filename"""
        if self.course_pdf:
            return self.course_pdf.name.split('/')[-1]
        return None
    
    @property
    def pdf_size_display(self):
        """Get PDF file size in human readable format"""
        if self.course_pdf and hasattr(self.course_pdf, 'size'):
            size = self.course_pdf.size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024:
                    return f"{size} {unit}"
                size /= 1024
            return f"{size:.1f} GB"
        return "0 B"
    
    def is_visible_to_user(self, user):
        """Check if course is visible to a specific user"""
        if not user or not user.is_authenticated:
            return self.visibility == 'PUBLIC'
        
        # Superadmins can see all courses
        if user.is_superadmin():
            return True
        
        # Check organization access
        if user.organization != self.organization:
            return False
        
        # Check visibility settings
        if self.visibility == 'PUBLIC':
            return True
        elif self.visibility == 'ORGANIZATION':
            return self.allow_organization_access
        elif self.visibility == 'MANAGERS':
            return user.is_manager_or_above()
        elif self.visibility == 'SPECIFIC':
            # For now, allow organization access - can be extended later
            return self.allow_organization_access
        
        return False
    
    def can_user_access(self, user):
        """Check if user can access course content"""
        if not self.is_visible_to_user(user):
            return False
        
        # Published courses are accessible to organization members
        if self.is_published and self.allow_organization_access:
            return True
        
        # Managers and admins can access unpublished courses
        if user.is_manager_or_above():
            return True
        
        return False
    
    def get_organization_courses(self):
        """Get all courses visible to organization members"""
        return Course.objects.filter(
            organization=self.organization,
            is_active=True,
            show_in_dashboard=True,
            allow_organization_access=True
        )
    
    def clean(self):
        """Model validation"""
        errors = {}
        
        # Validate instructor belongs to same organization
        if self.instructor and self.instructor.organization != self.organization:
            errors['instructor'] = "Instructor must belong to same organization"
        
        # Validate category belongs to same organization
        if self.category and self.category.organization != self.organization:
            errors['category'] = "Category must belong to same organization"
        
        # Validate price
        if self.price < 0:
            errors['price'] = "Price cannot be negative"
        
        # Validate duration
        if self.duration_hours <= 0:
            errors['duration_hours'] = "Duration must be greater than 0"
        
        # Validate max students
        if self.max_students <= 0:
            errors['max_students'] = "Max students must be greater than 0"
        
        # Validate PDF file
        if self.course_pdf:
            # Check if file is PDF
            if not self.course_pdf.name.lower().endswith('.pdf'):
                errors['course_pdf'] = "Only PDF files are allowed for course documents"
        
        if errors:
            raise ValidationError(errors)


class Module(models.Model):
    """
    Course modules with ordering system
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='modules',
        db_index=True
    )
    title = models.CharField(max_length=300, db_index=True)
    slug = models.SlugField(max_length=300, db_index=True)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    
    # Status and timestamps
    is_active = models.BooleanField(default=True, db_index=True)
    is_published = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'modules'
        verbose_name = 'Module'
        verbose_name_plural = 'Modules'
        constraints = [
            models.UniqueConstraint(
                fields=['course', 'slug'],
                name='unique_course_module_slug'
            ),
        ]
        indexes = [
            models.Index(fields=['course', 'order']),
            models.Index(fields=['course', 'is_active']),
            models.Index(fields=['order']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['course', 'order']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"
    
    @property
    def total_lessons(self):
        """Get total lessons in this module"""
        return self.lessons.filter(is_active=True).count()
    
    @property
    def full_name(self):
        """Get full module name with course"""
        return f"{self.course.title} - {self.title}"


class Lesson(models.Model):
    """
    Individual lessons with multiple content types
    """
    
    LESSON_TYPES = [
        ('VIDEO', 'Video'),
        ('TEXT', 'Text'),
        ('QUIZ', 'Quiz'),
        ('ASSIGNMENT', 'Assignment'),
        ('DOCUMENT', 'Document'),
        ('INTERACTIVE', 'Interactive'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name='lessons',
        db_index=True
    )
    title = models.CharField(max_length=300, db_index=True)
    slug = models.SlugField(max_length=300, db_index=True)
    description = models.TextField(blank=True)
    lesson_type = models.CharField(
        max_length=20,
        choices=LESSON_TYPES,
        default='TEXT',
        db_index=True
    )
    content = models.TextField(blank=True)
    video_url = models.URLField(max_length=500, blank=True)
    pdf_file = models.FileField(upload_to='lessons/pdfs/', blank=True, null=True)
    external_url = models.URLField(max_length=500, blank=True)
    duration_minutes = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=0)
    
    # Access control
    is_published = models.BooleanField(default=False, db_index=True)
    is_free = models.BooleanField(default=False, db_index=True)
    is_locked = models.BooleanField(default=False, db_index=True)
    unlock_conditions = models.JSONField(default=dict, blank=True)
    
    # Status and timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'lessons'
        verbose_name = 'Lesson'
        verbose_name_plural = 'Lessons'
        constraints = [
            models.UniqueConstraint(
                fields=['module', 'slug'],
                name='unique_module_lesson_slug'
            ),
        ]
        indexes = [
            models.Index(fields=['module', 'order']),
            models.Index(fields=['lesson_type']),
            models.Index(fields=['is_published']),
            models.Index(fields=['is_free']),
            models.Index(fields=['is_locked']),
            models.Index(fields=['order']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['module', 'order']
    
    def __str__(self):
        return f"{self.module.title} - {self.title}"
    
    @property
    def full_name(self):
        """Get full lesson name with course and module"""
        return f"{self.module.course.title} - {self.module.title} - {self.title}"
    
    @property
    def is_accessible(self):
        """Check if lesson is accessible to students"""
        return (self.is_published and 
                not self.is_locked and 
                (self.is_free or self.module.course.is_published))


class Resource(models.Model):
    """
    Course resources and materials
    """
    
    RESOURCE_TYPES = [
        ('PDF', 'PDF Document'),
        ('VIDEO', 'Video'),
        ('AUDIO', 'Audio'),
        ('IMAGE', 'Image'),
        ('DOCUMENT', 'Document'),
        ('LINK', 'External Link'),
        ('ZIP', 'Archive'),
        ('PRESENTATION', 'Presentation'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='resources',
        db_index=True
    )
    title = models.CharField(max_length=300, db_index=True)
    description = models.TextField(blank=True)
    resource_type = models.CharField(
        max_length=20,
        choices=RESOURCE_TYPES,
        db_index=True
    )
    file = models.FileField(upload_to='resources/files/', blank=True, null=True)
    url = models.URLField(max_length=500, blank=True)
    download_url = models.URLField(max_length=500, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=False, db_index=True)
    
    # Status and timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'resources'
        verbose_name = 'Resource'
        verbose_name_plural = 'Resources'
        indexes = [
            models.Index(fields=['lesson', 'resource_type']),
            models.Index(fields=['lesson', 'order']),
            models.Index(fields=['is_required']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['lesson', 'order']
    
    def __str__(self):
        return f"{self.lesson.title} - {self.title}"
    
    @property
    def file_size(self):
        """Get file size in human readable format"""
        if self.file and hasattr(self.file, 'size'):
            size = self.file.size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024:
                    return f"{size} {unit}"
                size /= 1024
                if size < 1024:
                    return f"{size:.1f} {unit}"
                size /= 1024
                if size < 1024:
                    return f"{size:.1f} {unit}"
        return "0 B"


class CourseReview(models.Model):
    """
    Student course reviews and ratings
    """
    
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='reviews',
        db_index=True
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='course_reviews',
        db_index=True
    )
    rating = models.PositiveIntegerField(
        choices=RATING_CHOICES,
        db_index=True
    )
    review = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False, db_index=True)
    
    # Status and timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'course_reviews'
        verbose_name = 'Course Review'
        verbose_name_plural = 'Course Reviews'
        constraints = [
            models.UniqueConstraint(
                fields=['course', 'user'],
                name='unique_course_user_review'
            ),
        ]
        indexes = [
            models.Index(fields=['course', 'rating']),
            models.Index(fields=['course', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.course.title} ({self.rating}/5)"
    
    @property
    def rating_display(self):
        """Get rating display text"""
        return f"{self.rating}/5 Stars"


class CourseDocument(models.Model):
    """
    Enhanced course materials and documents with PDF support
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    # Enhanced file handling for PDFs
    file = models.FileField(
        upload_to='course_documents/'
    )
    
    # File metadata
    file_size = models.BigIntegerField(default=0)  # Size in bytes
    file_type = models.CharField(
        max_length=50, 
        choices=[
            ('PDF', 'PDF Document'),
            ('DOC', 'Word Document'),
            ('PPT', 'PowerPoint'),
            ('TXT', 'Text File'),
            ('VIDEO', 'Video File'),
            ('AUDIO', 'Audio File'),
            ('IMAGE', 'Image File'),
            ('OTHER', 'Other File')
        ],
        default='PDF'
    )
    mime_type = models.CharField(max_length=100, blank=True, null=True)  # Store MIME type
    file_hash = models.CharField(max_length=64, blank=True, null=True)  # SHA-256 hash for integrity
    
    # Document organization and requirements
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=True)
    is_downloadable = models.BooleanField(default=True)  # Allow/disable download
    is_printable = models.BooleanField(default=True)  # Allow/disable printing
    
    # Document categorization
    category = models.CharField(
        max_length=50,
        choices=[
            ('READING', 'Reading Material'),
            ('ASSIGNMENT', 'Assignment'),
            ('REFERENCE', 'Reference Material'),
            ('VIDEO', 'Video Content'),
            ('AUDIO', 'Audio Content'),
            ('TEMPLATE', 'Template/Form'),
            ('OTHER', 'Other Material')
        ],
        default='READING'
    )
    
    # Access control
    is_public = models.BooleanField(default=False)  # Public access without enrollment
    access_level = models.CharField(
        max_length=20,
        choices=[
            ('ALL', 'All Students'),
            ('ENROLLED', 'Enrolled Students Only'),
            ('COMPLETED', 'Completed Students Only'),
            ('CUSTOM', 'Custom Access')
        ],
        default='ENROLLED'
    )
    
    # Version control
    version = models.PositiveIntegerField(default=1)
    is_latest_version = models.BooleanField(default=True)
    previous_version = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)  # When document becomes available
    
    class Meta:
        db_table = 'course_documents'
        verbose_name = 'Course Document'
        verbose_name_plural = 'Course Documents'
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['course', 'order']),
            models.Index(fields=['course', 'file_type']),
            models.Index(fields=['course', 'category']),
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
            models.Index(fields=['published_at']),
            models.Index(fields=['file_hash']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['course', 'title', 'version'],
                name='unique_document_version'
            )
        ]
    
    def __str__(self):
        return f"{self.title} (v{self.version})"
    
    def save(self, *args, **kwargs):
        """Override save to handle file processing"""
        # Set file size if file is provided
        if self.file and hasattr(self.file, 'size'):
            self.file_size = self.file.size
        
        # Generate file hash for integrity
        if self.file and not self.file_hash:
            self.file_hash = self.generate_file_hash()
        
        # Set MIME type based on file
        if self.file and not self.mime_type:
            self.mime_type = self.get_mime_type()
        
        # Set default published_at if not set and document is being published
        if not self.published_at and self.is_latest_version:
            self.published_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def generate_file_hash(self):
        """Generate SHA-256 hash of the file"""
        if not self.file:
            return None
        
        import hashlib
        hash_sha256 = hashlib.sha256()
        
        # Read file in chunks to handle large files
        for chunk in self.file.chunks():
            hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()
    
    def get_mime_type(self):
        """Get MIME type based on file extension"""
        if not self.file:
            return None
        
        import mimetypes
        mime_type, _ = mimetypes.guess_type(self.file.name)
        return mime_type or 'application/octet-stream'
    
    @property
    def file_size_display(self):
        """Return human-readable file size"""
        if not self.file_size or self.file_size == 0:
            return '0 bytes'
        
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    @property
    def file_extension(self):
        """Get file extension"""
        if not self.file:
            return ''
        return self.file.name.split('.')[-1].lower() if '.' in self.file.name else ''
    
    @property
    def is_pdf(self):
        """Check if file is PDF"""
        return self.file_type == 'PDF' or self.file_extension == 'pdf'
    
    def is_accessible(self, user):
        """Check if user can access this document"""
        if not user or not user.is_authenticated:
            return self.is_public
        
        # Public documents are accessible to everyone
        if self.is_public:
            return True
        
        # ALL access level means everyone can access
        if self.access_level == 'ALL':
            return True
        
        # Check if user belongs to the same organization
        if user.organization and user.organization == self.course.organization:
            # Organization members can access if course allows organization access
            if self.course.allow_organization_access:
                return True
        
        # ENROLLED access level - check if user is enrolled
        if self.access_level == 'ENROLLED':
            from enrollments.models import Enrollment
            return Enrollment.objects.filter(
                user=user, 
                course=self.course, 
                status__in=['ACTIVE', 'COMPLETED']
            ).exists()
        
        # COMPLETED access level - check if user has completed the course
        if self.access_level == 'COMPLETED':
            from enrollments.models import Enrollment
            return Enrollment.objects.filter(
                user=user, 
                course=self.course, 
                status='COMPLETED'
            ).exists()
        
        # CUSTOM access level - for future implementation
        if self.access_level == 'CUSTOM':
            # For now, allow organization access
            if user.organization and user.organization == self.course.organization:
                return self.course.allow_organization_access
        
        return False
    
    def get_absolute_url(self):
        """Get absolute URL for the document"""
        from django.urls import reverse
        return reverse('document_view', kwargs={'document_id': self.id})
    
    def get_download_url(self):
        """Get download URL for the document"""
        from django.urls import reverse
        return reverse('document_download', kwargs={'document_id': self.id})
    
    def create_new_version(self, new_file=None, new_title=None):
        """Create a new version of this document"""
        # Mark current version as not latest
        self.is_latest_version = False
        self.save(update_fields=['is_latest_version'])
        
        # Create new version
        new_doc = CourseDocument.objects.create(
            course=self.course,
            title=new_title or self.title,
            description=self.description,
            file=new_file or self.file,
            file_type=self.file_type,
            order=self.order,
            is_required=self.is_required,
            is_downloadable=self.is_downloadable,
            is_printable=self.is_printable,
            category=self.category,
            is_public=self.is_public,
            access_level=self.access_level,
            version=self.version + 1,
            is_latest_version=True,
            previous_version=self
        )
        
        return new_doc
