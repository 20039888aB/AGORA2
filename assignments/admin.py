from django.contrib import admin
from .models import Assignment, AssignmentQuestion, AssignmentSubmission, AssignmentFile


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'course', 'assignment_type', 'status', 'max_score',
        'passing_score', 'due_date', 'total_submissions', 'graded_submissions',
        'average_score', 'is_published', 'created_at'
    ]
    list_filter = [
        'assignment_type', 'status', 'is_published', 'created_at', 'due_date'
    ]
    search_fields = ['title', 'description', 'instructions']
    ordering = ['course', '-created_at']
    readonly_fields = ['created_at', 'updated_at', 'total_submissions', 'graded_submissions', 'average_score']
    
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'instructions', 'assignment_type')
        }),
        ('Course & Lesson', {
            'fields': ('course', 'lesson')
        }),
        ('Scoring', {
            'fields': ('max_score', 'passing_score', 'duration_minutes', 'attempts_allowed')
        }),
        ('Settings', {
            'fields': ('randomize_questions', 'allow_late_submission')
        }),
        ('Dates', {
            'fields': ('available_from', 'available_until', 'due_date', 'grace_period')
        }),
        ('Status', {
            'fields': ('status', 'is_published', 'is_active')
        }),
        ('Created By', {
            'fields': ('created_by',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AssignmentQuestion)
class AssignmentQuestionAdmin(admin.ModelAdmin):
    list_display = [
        'assignment', 'question_text', 'question_type', 'points',
        'order', 'is_required', 'created_at'
    ]
    list_filter = [
        'question_type', 'is_required', 'created_at'
    ]
    search_fields = ['question_text']
    ordering = ['assignment', 'order']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'assignment', 'status', 'score', 'max_possible_score',
        'percentage_score', 'is_passed', 'is_late', 'attempt_number',
        'submitted_at', 'graded_at'
    ]
    list_filter = [
        'status', 'submitted_at', 'graded_at'
    ]
    search_fields = ['student__email', 'assignment__title']
    ordering = ['assignment', 'student', '-attempt_number']
    readonly_fields = ['created_at', 'updated_at', 'last_saved_at', 'percentage_score', 'is_passed', 'is_late']
    
    fieldsets = (
        (None, {
            'fields': ('assignment', 'student', 'status')
        }),
        ('Content', {
            'fields': ('answers', 'text_content', 'attached_files')
        }),
        ('Grading', {
            'fields': ('score', 'max_possible_score', 'feedback', 'graded_by', 'graded_at')
        }),
        ('Timing', {
            'fields': ('submitted_at', 'last_saved_at', 'time_spent', 'attempt_number')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AssignmentFile)
class AssignmentFileAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'assignment', 'submission', 'file_type',
        'file_size_display', 'uploaded_by', 'uploaded_at', 'is_active'
    ]
    list_filter = [
        'file_type', 'uploaded_at', 'is_active'
    ]
    search_fields = ['title', 'uploaded_by__email']
    ordering = ['-uploaded_at']
    readonly_fields = ['uploaded_at', 'file_size', 'file_size_display']
    
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'file_type')
        }),
        ('Attachment', {
            'fields': ('assignment', 'submission', 'file')
        }),
        ('Metadata', {
            'fields': ('file_size', 'file_type_detected', 'uploaded_by')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('uploaded_at',),
            'classes': ('collapse',)
        }),
    )
