from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class Department(models.Model):
    """
    Department model for organizational structure
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, db_index=True)
    description = models.TextField(blank=True)
    organization = models.ForeignKey(
        'Organization',
        on_delete=models.CASCADE,
        related_name='departments',
        db_index=True
    )
    manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_departments',
        db_index=True,
        help_text="Department manager (must be ADMIN or MANAGER role)"
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sub_departments',
        db_index=True,
        help_text="Parent department for hierarchical structure"
    )
    
    # Status and timestamps
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'departments'
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'slug'],
                name='unique_org_department_slug'
            ),
        ]
        indexes = [
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['parent']),
            models.Index(fields=['manager']),
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
    def total_employees(self):
        """Get total employees in this department"""
        return User.objects.filter(department=self, is_active=True).count()
    
    @property
    def total_teams(self):
        """Get total teams in this department"""
        return self.teams.filter(is_active=True).count()


class Team(models.Model):
    """
    Team model for department-level organization
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, db_index=True)
    description = models.TextField(blank=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='teams',
        db_index=True
    )
    team_lead = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='led_teams',
        db_index=True,
        help_text="Team lead (must be MANAGER role)"
    )
    organization = models.ForeignKey(
        'Organization',
        on_delete=models.CASCADE,
        related_name='teams',
        db_index=True
    )
    
    # Team settings
    max_members = models.PositiveIntegerField(default=0, help_text="Maximum team members (0 for unlimited)")
    is_cross_functional = models.BooleanField(default=False, help_text="Cross-functional team")
    
    # Status and timestamps
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'teams'
        verbose_name = 'Team'
        verbose_name_plural = 'Teams'
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'slug'],
                name='unique_org_team_slug'
            ),
        ]
        indexes = [
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['department']),
            models.Index(fields=['team_lead']),
        ]
        ordering = ['organization', 'department', 'name']
    
    def __str__(self):
        return f"{self.organization.name} - {self.department.name} - {self.name}"
    
    @property
    def total_members(self):
        """Get total team members"""
        return User.objects.filter(team=self, is_active=True).count()
    
    @property
    def is_full(self):
        """Check if team is at capacity"""
        return self.max_members > 0 and self.total_members >= self.max_members


class OrganizationSettings(models.Model):
    """
    Organization-specific settings and configurations
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.OneToOneField(
        'Organization',
        on_delete=models.CASCADE,
        related_name='settings',
        db_index=True
    )
    
    # Learning settings
    default_course_duration = models.PositiveIntegerField(default=30, help_text="Default course duration in days")
    max_concurrent_courses = models.PositiveIntegerField(default=5, help_text="Maximum concurrent courses per user")
    auto_certificate_generation = models.BooleanField(default=True)
    require_manager_approval = models.BooleanField(default=False, help_text="Require manager approval for course enrollment")
    
    # Notification settings
    email_notifications_enabled = models.BooleanField(default=True)
    push_notifications_enabled = models.BooleanField(default=False)
    weekly_progress_reports = models.BooleanField(default=True)
    
    # Security settings
    two_factor_auth_required = models.BooleanField(default=False)
    session_timeout_minutes = models.PositiveIntegerField(default=480, help_text="Session timeout in minutes")
    
    # Branding settings
    primary_color = models.CharField(max_length=7, default='#4F46E5', help_text="Primary color in hex format")
    secondary_color = models.CharField(max_length=7, default='#7C3AED', help_text="Secondary color in hex format")
    logo_url = models.URLField(max_length=500, blank=True)
    custom_domain = models.CharField(max_length=100, blank=True)
    
    # Status and timestamps
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'organization_settings'
        verbose_name = 'Organization Settings'
        verbose_name_plural = 'Organization Settings'
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.organization.name} Settings"


class OrganizationMetrics(models.Model):
    """
    Track organization metrics and analytics
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'Organization',
        on_delete=models.CASCADE,
        related_name='metrics',
        db_index=True
    )
    
    # User metrics
    total_users = models.PositiveIntegerField(default=0)
    active_users = models.PositiveIntegerField(default=0)
    new_users_this_month = models.PositiveIntegerField(default=0)
    
    # Course metrics
    total_courses = models.PositiveIntegerField(default=0)
    published_courses = models.PositiveIntegerField(default=0)
    total_enrollments = models.PositiveIntegerField(default=0)
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    # Performance metrics
    avg_completion_time_days = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    avg_quiz_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    user_satisfaction_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    # Financial metrics
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    monthly_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    cost_per_user = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    
    # Timestamp
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)
    
    class Meta:
        db_table = 'organization_metrics'
        verbose_name = 'Organization Metrics'
        verbose_name_plural = 'Organization Metrics'
        indexes = [
            models.Index(fields=['organization', 'recorded_at']),
            models.Index(fields=['recorded_at']),
        ]
        ordering = ['-recorded_at']
    
    def __str__(self):
        return f"{self.organization.name} Metrics - {self.recorded_at.strftime('%Y-%m-%d')}"
