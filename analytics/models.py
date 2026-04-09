from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class LearningMetric(models.Model):
    """
    Track individual learning metrics and progress
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='learning_metrics',
        db_index=True
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='learning_metrics',
        db_index=True
    )
    
    # Progress metrics
    lessons_completed = models.PositiveIntegerField(default=0)
    total_lessons = models.PositiveIntegerField(default=0)
    progress_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    time_spent_minutes = models.PositiveIntegerField(default=0)
    
    # Performance metrics
    quiz_score_average = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    assignments_completed = models.PositiveIntegerField(default=0)
    assignments_total = models.PositiveIntegerField(default=0)
    
    # Engagement metrics
    login_count = models.PositiveIntegerField(default=0)
    last_activity = models.DateTimeField(null=True, blank=True)
    streak_days = models.PositiveIntegerField(default=0)
    
    # Timestamps
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'learning_metrics'
        verbose_name = 'Learning Metric'
        verbose_name_plural = 'Learning Metrics'
        indexes = [
            models.Index(fields=['user', 'course']),
            models.Index(fields=['user', 'recorded_at']),
            models.Index(fields=['course', 'recorded_at']),
            models.Index(fields=['progress_percentage']),
            models.Index(fields=['streak_days']),
        ]
        ordering = ['-recorded_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.course.title} ({self.progress_percentage}%)"


class OrganizationMetric(models.Model):
    """
    Track organization-wide metrics and analytics
    """
    
    METRIC_TYPES = [
        ('USER_ENGAGEMENT', 'User Engagement'),
        ('COURSE_COMPLETION', 'Course Completion'),
        ('PERFORMANCE', 'Performance'),
        ('FINANCIAL', 'Financial'),
        ('COMPLIANCE', 'Compliance'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='metrics',
        db_index=True
    )
    metric_type = models.CharField(
        max_length=20,
        choices=METRIC_TYPES,
        db_index=True
    )
    
    # Metric values
    metric_value = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    metric_count = models.PositiveIntegerField(default=0)
    previous_value = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    
    # Additional data (JSON for flexibility)
    additional_data = models.JSONField(default=dict, blank=True)
    
    # Period
    period_start = models.DateTimeField(db_index=True)
    period_end = models.DateTimeField(db_index=True)
    period_type = models.CharField(
        max_length=10,
        choices=[
            ('DAILY', 'Daily'),
            ('WEEKLY', 'Weekly'),
            ('MONTHLY', 'Monthly'),
            ('YEARLY', 'Yearly'),
        ],
        default='MONTHLY'
    )
    
    # Timestamps
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'organization_metrics'
        verbose_name = 'Organization Metric'
        verbose_name_plural = 'Organization Metrics'
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'metric_type', 'period_start', 'period_end'],
                name='unique_org_metric_period'
            ),
        ]
        indexes = [
            models.Index(fields=['organization', 'metric_type']),
            models.Index(fields=['metric_type', 'period_start']),
            models.Index(fields=['period_type', 'recorded_at']),
        ]
        ordering = ['-recorded_at']
    
    def __str__(self):
        return f"{self.organization.name} - {self.get_metric_type_display()} - {self.period_end.strftime('%Y-%m-%d')}"
    
    @property
    def change_percentage(self):
        """Calculate percentage change from previous period"""
        if self.previous_value == 0:
            return 0
        return ((self.metric_value - self.previous_value) / self.previous_value) * 100


class PlatformMetric(models.Model):
    """
    Track platform-wide metrics for SuperAdmin analytics
    """
    
    METRIC_TYPES = [
        ('USER_GROWTH', 'User Growth'),
        ('ORGANIZATION_GROWTH', 'Organization Growth'),
        ('COURSE_ENGAGEMENT', 'Course Engagement'),
        ('SYSTEM_PERFORMANCE', 'System Performance'),
        ('REVENUE', 'Revenue'),
        ('RETENTION', 'Retention'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    metric_type = models.CharField(
        max_length=25,
        choices=METRIC_TYPES,
        db_index=True
    )
    
    # Metric values
    metric_value = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    metric_count = models.PositiveIntegerField(default=0)
    previous_value = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    
    # Additional data
    additional_data = models.JSONField(default=dict, blank=True)
    
    # Period
    period_start = models.DateTimeField(db_index=True)
    period_end = models.DateTimeField(db_index=True)
    period_type = models.CharField(
        max_length=10,
        choices=[
            ('DAILY', 'Daily'),
            ('WEEKLY', 'Weekly'),
            ('MONTHLY', 'Monthly'),
            ('YEARLY', 'Yearly'),
        ],
        default='MONTHLY'
    )
    
    # Timestamps
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'platform_metrics'
        verbose_name = 'Platform Metric'
        verbose_name_plural = 'Platform Metrics'
        constraints = [
            models.UniqueConstraint(
                fields=['metric_type', 'period_start', 'period_end'],
                name='unique_platform_metric_period'
            ),
        ]
        indexes = [
            models.Index(fields=['metric_type', 'period_start']),
            models.Index(fields=['period_type', 'recorded_at']),
        ]
        ordering = ['-recorded_at']
    
    def __str__(self):
        return f"Platform - {self.get_metric_type_display()} - {self.period_end.strftime('%Y-%m-%d')}"
    
    @property
    def change_percentage(self):
        """Calculate percentage change from previous period"""
        if self.previous_value == 0:
            return 0
        return ((self.metric_value - self.previous_value) / self.previous_value) * 100


class LearningPath(models.Model):
    """
    Learning paths for structured skill development
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, db_index=True)
    description = models.TextField(blank=True)
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
    
    # Path settings
    difficulty_level = models.CharField(
        max_length=20,
        choices=[
            ('BEGINNER', 'Beginner'),
            ('INTERMEDIATE', 'Intermediate'),
            ('ADVANCED', 'Advanced'),
        ],
        default='BEGINNER'
    )
    estimated_hours = models.PositiveIntegerField(default=0)
    is_public = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'learning_paths'
        verbose_name = 'Learning Path'
        verbose_name_plural = 'Learning Paths'
        indexes = [
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['difficulty_level']),
            models.Index(fields=['is_public']),
        ]
        ordering = ['organization', 'name']
    
    def __str__(self):
        return f"{self.organization.name} - {self.name}"


class LearningPathStep(models.Model):
    """
    Individual steps within a learning path
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    learning_path = models.ForeignKey(
        LearningPath,
        on_delete=models.CASCADE,
        related_name='steps',
        db_index=True
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='path_steps',
        db_index=True
    )
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=True)
    
    # Prerequisites
    prerequisites = models.ManyToManyField(
        'self',
        symmetrical=False,
        blank=True,
        related_name='dependent_steps'
    )
    
    class Meta:
        db_table = 'learning_path_steps'
        verbose_name = 'Learning Path Step'
        verbose_name_plural = 'Learning Path Steps'
        constraints = [
            models.UniqueConstraint(
                fields=['learning_path', 'course'],
                name='unique_path_course'
            ),
        ]
        indexes = [
            models.Index(fields=['learning_path', 'order']),
            models.Index(fields=['course']),
        ]
        ordering = ['learning_path', 'order']
    
    def __str__(self):
        return f"{self.learning_path.name} - Step {self.order}: {self.course.title}"


class UserLearningPath(models.Model):
    """
    Track user progress through learning paths
    """
    
    STATUS_CHOICES = [
        ('NOT_STARTED', 'Not Started'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('ABANDONED', 'Abandoned'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='learning_paths',
        db_index=True
    )
    learning_path = models.ForeignKey(
        LearningPath,
        on_delete=models.CASCADE,
        related_name='user_progress',
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='NOT_STARTED',
        db_index=True
    )
    
    # Progress tracking
    current_step = models.PositiveIntegerField(default=0)
    completed_steps = models.PositiveIntegerField(default=0)
    total_steps = models.PositiveIntegerField(default=0)
    progress_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    # Time tracking
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    estimated_completion = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_learning_paths'
        verbose_name = 'User Learning Path'
        verbose_name_plural = 'User Learning Paths'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'learning_path'],
                name='unique_user_learning_path'
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['learning_path', 'status']),
            models.Index(fields=['progress_percentage']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.learning_path.name} ({self.status})"


class Achievement(models.Model):
    """
    Achievements and badges for gamification
    """
    
    ACHIEVEMENT_TYPES = [
        ('COURSE_COMPLETION', 'Course Completion'),
        ('STREAK', 'Learning Streak'),
        ('PERFORMANCE', 'Performance'),
        ('ENGAGEMENT', 'Engagement'),
        ('SPECIAL', 'Special Achievement'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, db_index=True)
    description = models.TextField()
    icon = models.CharField(max_length=50, default='🏆')
    achievement_type = models.CharField(
        max_length=20,
        choices=ACHIEVEMENT_TYPES,
        db_index=True
    )
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='achievements',
        db_index=True,
        null=True,
        blank=True
    )
    
    # Achievement criteria
    criteria = models.JSONField(default=dict, help_text="Criteria for unlocking achievement")
    points = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'achievements'
        verbose_name = 'Achievement'
        verbose_name_plural = 'Achievements'
        indexes = [
            models.Index(fields=['achievement_type', 'is_active']),
            models.Index(fields=['organization', 'is_active']),
        ]
        ordering = ['achievement_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_achievement_type_display()})"


class UserAchievement(models.Model):
    """
    Track user achievements and badges
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='achievements',
        db_index=True
    )
    achievement = models.ForeignKey(
        Achievement,
        on_delete=models.CASCADE,
        related_name='recipients',
        db_index=True
    )
    
    # Award details
    awarded_at = models.DateTimeField(default=timezone.now, db_index=True)
    awarded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='awarded_achievements'
    )
    
    # Progress (for achievements that track progress)
    progress_value = models.PositiveIntegerField(default=0)
    progress_max = models.PositiveIntegerField(default=1)
    
    class Meta:
        db_table = 'user_achievements'
        verbose_name = 'User Achievement'
        verbose_name_plural = 'User Achievements'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'achievement'],
                name='unique_user_achievement'
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'awarded_at']),
            models.Index(fields=['achievement', 'awarded_at']),
        ]
        ordering = ['-awarded_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.achievement.name}"
