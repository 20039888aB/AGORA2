from django.contrib import admin
from .models import Category, Course, Module, Lesson, CourseDocument, DocumentProgress, CourseReview

# Enhanced Course Models Admin
from django.contrib import admin
from .enhanced_models import EnhancedCourse, CourseFile


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent', 'organization', 'is_active', 'created_at']
    list_filter = ['organization', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['organization', 'name']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'category', 'instructor', 'status', 'difficulty', 
        'duration_hours', 'price', 'max_students', 'total_enrollments', 'is_featured', 'created_at'
    ]
    list_filter = [
        'organization', 'category', 'instructor', 'status', 'difficulty',
        'is_featured', 'created_at'
    ]
    search_fields = ['title', 'description', 'short_description']
    ordering = ['organization', '-created_at']
    readonly_fields = ['created_at', 'updated_at', 'total_enrollments', 'is_featured']
    
    fieldsets = (
        (None, {
            'fields': (
                'title', 'slug', 'description', 'short_description'
            )
        }),
        ('Course Details', {
            'fields': (
                'category', 'instructor', 'difficulty', 'duration_hours',
                'price', 'prerequisites', 'objectives', 'outcomes'
            )
        }),
        ('Settings', {
            'fields': (
                'language', 'max_students', 'certificate_enabled', 'is_featured'
            )
        }),
        ('Status', {
            'fields': (
                'status',
            )
        }),
        ('Organization', {
            'fields': (
                'organization',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def total_enrollments(self, obj):
        return obj.total_enrollments


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order', 'is_published', 'created_at']
    list_filter = ['course', 'is_published', 'created_at']
    search_fields = ['title', 'description']
    ordering = ['course', 'order', 'created_at']


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'module', 'course', 'order', 'is_published', 'created_at']
    list_filter = ['course', 'is_published', 'created_at']
    search_fields = ['title', 'description']
    ordering = ['course', 'module', 'order', 'created_at']


@admin.register(CourseDocument)
class CourseDocumentAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'course', 'category', 'file_type', 'file_size_display',
        'is_required', 'is_downloadable', 'is_printable', 'is_public',
        'access_level', 'version', 'is_latest_version', 'published_at', 'created_at'
    ]
    list_filter = [
        'course', 'file_type', 'category', 'is_required', 'is_downloadable',
        'is_printable', 'is_public', 'access_level', 'is_latest_version',
        'created_at', 'published_at'
    ]
    search_fields = ['title', 'description', 'course__title']
    ordering = ['course', 'order', 'created_at']
    readonly_fields = [
        'created_at', 'updated_at', 'file_size_display', 'file_size',
        'file_hash', 'mime_type', 'file_extension', 'is_pdf'
    ]
    
    fieldsets = (
        (None, {
            'fields': ('course', 'title', 'description', 'file')
        }),
        ('Document Details', {
            'fields': (
                ('order', 'version', 'is_latest_version'),
                ('file_type', 'category'),
                ('file_size', 'file_hash')
            )
        }),
        ('Access Control', {
            'fields': (
                ('is_required', 'is_downloadable', 'is_printable'),
                ('is_public', 'access_level'),
                'published_at'
            )
        }),
        ('Version Control', {
            'fields': ('previous_version',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def file_size_display(self, obj):
        return obj.file_size_display
    file_size_display.short_description = 'File Size'
    
    def file_extension(self, obj):
        return obj.file_extension
    file_extension.short_description = 'Extension'
    
    def is_pdf(self, obj):
        return obj.is_pdf
    is_pdf.boolean = True
    is_pdf.short_description = 'Is PDF'
    
    def get_queryset(self, request):
        """Filter documents based on user permissions"""
        qs = super().get_queryset(request)
        
        if request.user.is_superadmin():
            return qs
        
        if request.user.is_admin_or_above():
            # Admin can see documents from their organization
            if request.user.organization:
                return qs.filter(course__organization=request.user.organization)
        
        if request.user.is_instructor():
            # Instructors can see documents from their courses
            return qs.filter(course__instructor=request.user)
        
        # Students can't see documents in admin
        return qs.none()
    
    def get_readonly_fields(self, request, obj=None):
        """Make some fields readonly based on user role"""
        readonly_fields = list(self.readonly_fields)
        
        if obj and not request.user.is_admin_or_above():
            # Non-admins can't modify certain fields
            readonly_fields.extend(['file_hash', 'mime_type'])
        
        return readonly_fields


@admin.register(DocumentProgress)
class DocumentProgressAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'course', 'document', 'is_completed', 'completed_at', 'created_at'
    ]
    list_filter = [
        'course', 'is_completed', 'created_at', 'completed_at'
    ]
    search_fields = ['user__email', 'document__title', 'course__title']
    ordering = ['user', 'course', 'document', 'created_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CourseReview)
class CourseReviewAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'course', 'rating', 'review', 'is_verified', 'created_at'
    ]
    list_filter = [
        'course', 'user', 'rating', 'is_verified', 'created_at'
    ]
    search_fields = ['review', 'user__email', 'course__title']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']


# Enhanced Course Models Admin
@admin.register(EnhancedCourse)
class EnhancedCourseAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'category', 'difficulty', 'duration_hours', 
        'max_students', 'status', 'is_featured', 'created_at'
    ]
    list_filter = [
        'status', 'category', 'difficulty', 'is_featured', 'created_at'
    ]
    search_fields = ['title', 'description', 'short_description']
    ordering = ['organization', '-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': (
                'title', 'slug', 'description', 'short_description'
            )
        }),
        ('Course Details', {
            'fields': (
                ('category', 'difficulty', 'duration_hours', 'max_students'),
                ('language', 'status')
            )
        }),
        ('Learning Content', {
            'fields': (
                'prerequisites', 'objectives', 'outcomes'
            )
        }),
        ('Settings', {
            'fields': (
                'certificate_enabled', 'is_featured', 'tags'
            )
        }),
        ('Organization', {
            'fields': (
                'organization', 'created_by'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superadmin():
            return qs
        return qs.filter(organization=request.user.organization)


@admin.register(CourseFile)
class CourseFileAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'course', 'file_type', 'file_size_display', 
        'uploaded_by', 'created_at'
    ]
    list_filter = [
        'course', 'file_type', 'is_required', 'is_downloadable', 'created_at'
    ]
    search_fields = ['title', 'description']
    ordering = ['course', 'order', 'created_at']
    readonly_fields = ['file_size', 'mime_type', 'created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': (
                'title', 'description', 'file'
            )
        }),
        ('File Details', {
            'fields': (
                'file_type', 'file_size', 'mime_type'
            )
        }),
        ('Organization', {
            'fields': (
                'course', 'uploaded_by', 'organization'
            )
        }),
        ('Settings', {
            'fields': (
                'order', 'is_required', 'is_downloadable', 'is_active'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def file_size_display(self, obj):
        if obj.file_size:
            for unit in ['B', 'KB', 'MB', 'GB']:
                if obj.file_size < 1024.0:
                    return f"{obj.file_size:.1f} {unit}"
                obj.file_size /= 1024.0
            return f"{obj.file_size:.1f} TB"
        return "0 B"
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superadmin():
            return qs
        return qs.filter(organization=request.user.organization)
