from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class Assignment(models.Model):
    """
    Assignment model with comprehensive metadata
    """
    
    ASSIGNMENT_TYPES = [
        ('ESSAY', 'Essay'),
        ('PROJECT', 'Project'),
        ('QUIZ', 'Quiz'),
        ('PRESENTATION', 'Presentation'),
        ('CODING', 'Coding'),
        ('RESEARCH', 'Research'),
        ('CASE_STUDY', 'Case Study'),
        ('PRACTICAL', 'Practical'),
    ]
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PUBLISHED', 'Published'),
        ('CLOSED', 'Closed'),
        ('ARCHIVED', 'Archived'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300, db_index=True)
    description = models.TextField()
    instructions = models.TextField()
    assignment_type = models.CharField(
        max_length=20,
        choices=ASSIGNMENT_TYPES,
        default='ESSAY',
        db_index=True
    )
    
    # Course and lesson relationships
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='assignments',
        db_index=True
    )
    lesson = models.ForeignKey(
        'courses.Lesson',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assignments',
        db_index=True
    )
    
    # Assignment metadata
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    passing_score = models.DecimalField(max_digits=5, decimal_places=2, default=60.00)
    duration_minutes = models.PositiveIntegerField(default=60)
    attempts_allowed = models.PositiveIntegerField(default=3)
    randomize_questions = models.BooleanField(default=False)
    allow_late_submission = models.BooleanField(default=False)
    
    # Dates and timing
    available_from = models.DateTimeField(db_index=True)
    available_until = models.DateTimeField(db_index=True)
    due_date = models.DateTimeField(db_index=True)
    grace_period = models.DurationField(default=timezone.timedelta(0))
    
    # Status and permissions
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        db_index=True
    )
    is_published = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Created by
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_assignments',
        db_index=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'assignments'
        verbose_name = 'Assignment'
        verbose_name_plural = 'Assignments'
        constraints = [
            models.UniqueConstraint(
                fields=['course', 'title'],
                name='unique_course_assignment_title'
            ),
        ]
        indexes = [
            models.Index(fields=['course', 'status']),
            models.Index(fields=['lesson']),
            models.Index(fields=['assignment_type']),
            models.Index(fields=['available_from', 'available_until']),
            models.Index(fields=['due_date']),
            models.Index(fields=['is_published']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['course', '-created_at']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"
    
    @property
    def is_available(self):
        """Check if assignment is currently available"""
        now = timezone.now()
        return self.is_published and self.available_from <= now <= self.available_until
    
    @property
    def is_overdue(self):
        """Check if assignment is overdue"""
        return timezone.now() > (self.due_date + self.grace_period)
    
    @property
    def total_submissions(self):
        """Get total submissions"""
        return self.submissions.filter(is_active=True).count()
    
    @property
    def graded_submissions(self):
        """Get graded submissions"""
        return self.submissions.filter(
            is_active=True,
            score__isnull=False
        ).count()
    
    @property
    def average_score(self):
        """Get average score"""
        graded_submissions = self.submissions.filter(
            is_active=True,
            score__isnull=False
        )
        if graded_submissions.exists():
            return graded_submissions.aggregate(
                avg_score=models.Avg('score')
            )['avg_score'] or 0
        return 0
    
    def clean(self):
        """Model validation"""
        errors = {}
        
        # Validate dates
        if self.available_from >= self.available_until:
            errors['available_from'] = "Available from must be before available until"
        
        if self.due_date < self.available_from:
            errors['due_date'] = "Due date must be after available from"
        
        if self.due_date > self.available_until:
            errors['due_date'] = "Due date must be before available until"
        
        # Validate scores
        if self.max_score <= 0:
            errors['max_score'] = "Max score must be greater than 0"
        
        if self.passing_score < 0 or self.passing_score > self.max_score:
            errors['passing_score'] = "Passing score must be between 0 and max score"
        
        # Validate attempts
        if self.attempts_allowed <= 0:
            errors['attempts_allowed'] = "Attempts allowed must be greater than 0"
        
        # Validate duration
        if self.duration_minutes <= 0:
            errors['duration_minutes'] = "Duration must be greater than 0"
        
        # Validate lesson belongs to same course
        if self.lesson and self.lesson.module.course != self.course:
            errors['lesson'] = "Lesson must belong to same course"
        
        # Validate created_by belongs to same organization
        if self.created_by and self.created_by.organization != self.course.organization:
            errors['created_by'] = "Created by must belong to same organization"
        
        if errors:
            raise ValidationError(errors)


class AssignmentQuestion(models.Model):
    """
    Questions for assignments
    """
    
    QUESTION_TYPES = [
        ('MULTIPLE_CHOICE', 'Multiple Choice'),
        ('TRUE_FALSE', 'True/False'),
        ('SHORT_ANSWER', 'Short Answer'),
        ('ESSAY', 'Essay'),
        ('FILL_BLANK', 'Fill in the Blank'),
        ('MATCHING', 'Matching'),
        ('CODING', 'Coding'),
        ('FILE_UPLOAD', 'File Upload'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name='questions',
        db_index=True
    )
    question_text = models.TextField()
    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPES,
        default='MULTIPLE_CHOICE',
        db_index=True
    )
    question_data = models.JSONField(default=dict, blank=True)  # For options, correct answers, etc.
    points = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=True, db_index=True)
    explanation = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'assignment_questions'
        verbose_name = 'Assignment Question'
        verbose_name_plural = 'Assignment Questions'
        constraints = [
            models.UniqueConstraint(
                fields=['assignment', 'order'],
                name='unique_assignment_question_order'
            ),
        ]
        indexes = [
            models.Index(fields=['assignment', 'order']),
            models.Index(fields=['question_type']),
            models.Index(fields=['is_required']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['assignment', 'order']
    
    def __str__(self):
        return f"{self.assignment.title} - Question {self.order + 1}"
    
    @property
    def question_type_display(self):
        """Get question type display name"""
        return dict(AssignmentQuestion.QUESTION_TYPES).get(self.question_type, self.question_type)


class AssignmentSubmission(models.Model):
    """
    Assignment submissions by students
    """
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('GRADED', 'Graded'),
        ('RETURNED', 'Returned'),
        ('EXPIRED', 'Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name='submissions',
        db_index=True
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='assignment_submissions',
        db_index=True
    )
    
    # Submission content
    answers = models.JSONField(default=dict, blank=True)
    text_content = models.TextField(blank=True)
    attached_files = models.JSONField(default=list, blank=True)
    
    # Grading
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    max_possible_score = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    feedback = models.TextField(blank=True)
    graded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='graded_submissions',
        db_index=True
    )
    graded_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Status and timing
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        db_index=True
    )
    submitted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_saved_at = models.DateTimeField(auto_now=True, db_index=True)
    time_spent = models.DurationField(default=timezone.timedelta(0))
    attempt_number = models.PositiveIntegerField(default=1)
    
    # Access control
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'assignment_submissions'
        verbose_name = 'Assignment Submission'
        verbose_name_plural = 'Assignment Submissions'
        constraints = [
            models.UniqueConstraint(
                fields=['assignment', 'student', 'attempt_number'],
                name='unique_assignment_student_attempt'
            ),
        ]
        indexes = [
            models.Index(fields=['assignment', 'student']),
            models.Index(fields=['assignment', 'status']),
            models.Index(fields=['student', 'status']),
            models.Index(fields=['submitted_at']),
            models.Index(fields=['graded_at']),
            models.Index(fields=['score']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['assignment', 'student', '-attempt_number']
    
    def __str__(self):
        return f"{self.student.email} - {self.assignment.title} (Attempt {self.attempt_number})"
    
    @property
    def is_submitted(self):
        """Check if submission is submitted"""
        return self.status == 'SUBMITTED'
    
    @property
    def is_graded(self):
        """Check if submission is graded"""
        return self.status == 'GRADED'
    
    @property
    def is_passed(self):
        """Check if submission passed"""
        if self.score is not None:
            return self.score >= self.assignment.passing_score
        return False
    
    @property
    def percentage_score(self):
        """Get percentage score"""
        if self.score is not None and self.max_possible_score > 0:
            return (self.score / self.max_possible_score) * 100
        return 0
    
    @property
    def is_late(self):
        """Check if submission is late"""
        if self.submitted_at:
            return self.submitted_at > (self.assignment.due_date + self.assignment.grace_period)
        return False
    
    def submit(self, submitted_by=None):
        """Submit assignment"""
        if self.status == 'SUBMITTED':
            raise ValidationError("Assignment is already submitted")
        
        if not self.assignment.is_available:
            raise ValidationError("Assignment is not available for submission")
        
        self.status = 'SUBMITTED'
        self.submitted_at = timezone.now()
        self.save(update_fields=['status', 'submitted_at'])
        
        # Log submission
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=submitted_by or self.student,
            action='ASSIGNMENT_SUBMIT',
            details={
                'submission': str(self.id),
                'assignment': str(self.assignment.id),
                'attempt': self.attempt_number,
            },
            ip_address=(submitted_by or self.student).last_login_ip
        )
    
    def grade(self, score, feedback=None, graded_by=None):
        """Grade assignment submission"""
        if score < 0 or score > self.max_possible_score:
            raise ValidationError("Score must be between 0 and max possible score")
        
        self.score = score
        self.feedback = feedback or ''
        self.graded_by = graded_by
        self.graded_at = timezone.now()
        self.status = 'GRADED'
        self.save(update_fields=['score', 'feedback', 'graded_by', 'graded_at', 'status'])
        
        # Log grading
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=graded_by,
            action='ASSIGNMENT_GRADE',
            details={
                'submission': str(self.id),
                'assignment': str(self.assignment.id),
                'score': float(score),
                'feedback': feedback,
            },
            ip_address=graded_by.last_login_ip
        )
    
    def clean(self):
        """Model validation"""
        errors = {}
        
        # Validate student belongs to same organization as assignment
        if self.student.organization != self.assignment.course.organization:
            errors['student'] = "Student must belong to same organization as assignment"
        
        # Validate attempt number
        if self.attempt_number > self.assignment.attempts_allowed:
            errors['attempt_number'] = f"Attempt number cannot exceed {self.assignment.attempts_allowed}"
        
        # Validate graded_by belongs to same organization
        if self.graded_by and self.graded_by.organization != self.assignment.course.organization:
            errors['graded_by'] = "Graded by must belong to same organization as assignment"
        
        if errors:
            raise ValidationError(errors)


class AssignmentFile(models.Model):
    """
    Files attached to assignments or submissions
    """
    
    FILE_TYPES = [
        ('ASSIGNMENT', 'Assignment File'),
        ('SUBMISSION', 'Submission File'),
        ('FEEDBACK', 'Feedback File'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='files',
        db_index=True
    )
    submission = models.ForeignKey(
        AssignmentSubmission,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='files',
        db_index=True
    )
    file_type = models.CharField(
        max_length=20,
        choices=FILE_TYPES,
        default='ASSIGNMENT',
        db_index=True
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='assignments/files/')
    file_size = models.BigIntegerField(default=0)
    file_type_detected = models.CharField(max_length=100, blank=True)
    
    # Upload metadata
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_assignment_files',
        db_index=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Status
    is_active = models.BooleanField(default=True, db_index=True)
    
    class Meta:
        db_table = 'assignment_files'
        verbose_name = 'Assignment File'
        verbose_name_plural = 'Assignment Files'
        constraints = [
            models.CheckConstraint(
                check=models.Q(assignment__isnull=False) | models.Q(submission__isnull=False),
                name='assignment_or_submission_required'
            ),
        ]
        indexes = [
            models.Index(fields=['assignment']),
            models.Index(fields=['submission']),
            models.Index(fields=['file_type']),
            models.Index(fields=['uploaded_by']),
            models.Index(fields=['uploaded_at']),
        ]
        ordering = ['-uploaded_at']
    
    def __str__(self):
        if self.assignment:
            return f"{self.assignment.title} - {self.title}"
        elif self.submission:
            return f"{self.submission.student.email} - {self.title}"
        return self.title
    
    @property
    def file_size_display(self):
        """Get file size in human readable format"""
        size = self.file_size
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
    
    def save(self, *args, **kwargs):
        """Override save to detect file size and type"""
        if self.file and not self.file_size:
            self.file_size = self.file.size
        
        super().save(*args, **kwargs)
