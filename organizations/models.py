from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid


class Organization(models.Model):
    """
    Multi-tenant organization with subscription tiers and approval workflow
    """
    
    SUBSCRIPTION_TIERS = [
        ('FREE', 'Free'),
        ('BASIC', 'Basic'),
        ('PRO', 'Professional'),
        ('ENTERPRISE', 'Enterprise'),
    ]
    
    APPROVAL_WORKFLOW_CHOICES = [
        ('AUTO_APPROVE', 'Auto Approve'),
        ('MANUAL_APPROVE', 'Manual Approve'),
        ('REQUIRES_APPROVAL', 'Requires Approval'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='organizations/logos/', blank=True, null=True)
    website = models.URLField(max_length=500, blank=True)
    email = models.EmailField(max_length=254, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    
    # Subscription and approval
    subscription_tier = models.CharField(
        max_length=20, 
        choices=SUBSCRIPTION_TIERS, 
        default='FREE',
        db_index=True
    )
    user_limit = models.PositiveIntegerField(default=10)
    approval_workflow = models.CharField(
        max_length=20, 
        choices=APPROVAL_WORKFLOW_CHOICES, 
        default='AUTO_APPROVE'
    )
    
    # Status and timestamps
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'organizations'
        verbose_name = 'Organization'
        verbose_name_plural = 'Organizations'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['subscription_tier', 'is_active']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def total_users(self):
        """Get total active users in organization"""
        from accounts.models import User
        return User.objects.active().filter(organization=self).count()
    
    @property
    def total_departments(self):
        """Get total departments in organization"""
        return self.departments.filter(is_active=True).count()
    
    @property
    def is_at_user_limit(self):
        """Check if organization has reached user limit"""
        return self.total_users >= self.user_limit
    
    def can_add_user(self):
        """Check if organization can add more users"""
        if self.subscription_tier == 'FREE':
            return not self.is_at_user_limit
        return True
    
    def clean(self):
        """Model validation"""
        errors = {}
        
        if self.user_limit <= 0:
            errors['user_limit'] = "User limit must be greater than 0"
        
        if self.subscription_tier == 'FREE' and self.user_limit > 10:
            errors['user_limit'] = "Free tier cannot have more than 10 users"
        
        if errors:
            raise ValidationError(errors)


class Department(models.Model):
    """
    Hierarchical department structure with parent-child relationships
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='departments',
        db_index=True
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        db_index=True
    )
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, db_index=True)
    description = models.TextField(blank=True)
    head = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='headed_departments',
        db_index=True
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
            models.UniqueConstraint(
                fields=['organization', 'name'],
                name='unique_org_department_name'
            ),
        ]
        indexes = [
            models.Index(fields=['organization', 'parent']),
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['head']),
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
        """Get department level in hierarchy"""
        level = 0
        current = self.parent
        while current:
            level += 1
            current = current.parent
        return level
    
    @property
    def total_users(self):
        """Get total users in this department"""
        from accounts.models import User
        return User.objects.active().filter(profile__department=self).count()
    
    @property
    def total_subdepartments(self):
        """Get total subdepartments"""
        return self.children.filter(is_active=True).count()
    
    def clean(self):
        """Model validation"""
        errors = {}
        
        # Validate hierarchy - prevent cycles
        if self.parent and self.parent == self:
            errors['parent'] = "Department cannot be its own parent"
        
        # Validate head belongs to same organization
        if self.head and self.head.organization != self.organization:
            errors['head'] = "Department head must belong to same organization"
        
        if errors:
            raise ValidationError(errors)


class Team(models.Model):
    """
    Team model for department-level organization
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='teams',
        db_index=True
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='teams',
        db_index=True
    )
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, db_index=True)
    description = models.TextField(blank=True)
    lead = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='led_teams',
        db_index=True
    )
    
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
            models.UniqueConstraint(
                fields=['organization', 'name'],
                name='unique_org_team_name'
            ),
        ]
        indexes = [
            models.Index(fields=['organization', 'department']),
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['lead']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['organization', 'department', 'name']
    
    def __str__(self):
        return f"{self.organization.name} - {self.name}"
    
    @property
    def full_name(self):
        """Get full team name with department"""
        if self.department:
            return f"{self.department.name} - {self.name}"
        return f"{self.organization.name} - {self.name}"
    
    @property
    def total_members(self):
        """Get total team members"""
        from accounts.models import User
        return User.objects.active().filter(profile__team=self).count()
    
    def clean(self):
        """Model validation"""
        errors = {}
        
        # Validate lead belongs to same organization
        if self.lead and self.lead.organization != self.organization:
            errors['lead'] = "Team lead must belong to same organization"
        
        # Validate department belongs to same organization
        if self.department and self.department.organization != self.organization:
            errors['department'] = "Department must belong to same organization"
        
        if errors:
            raise ValidationError(errors)


class DepartmentMembership(models.Model):
    """
    Many-to-many relationship between users and departments
    """
    
    ROLE_CHOICES = [
        ('MEMBER', 'Member'),
        ('LEAD', 'Lead'),
        ('ASSISTANT', 'Assistant'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='department_memberships',
        db_index=True
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='members',
        db_index=True
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='MEMBER',
        db_index=True
    )
    
    # Timestamps
    joined_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'department_memberships'
        verbose_name = 'Department Membership'
        verbose_name_plural = 'Department Memberships'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'department'],
                name='unique_user_department'
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'role']),
            models.Index(fields=['department', 'role']),
            models.Index(fields=['joined_at']),
        ]
        ordering = ['-joined_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.department.name} ({self.role})"


class TeamMembership(models.Model):
    """
    Many-to-many relationship between users and teams
    """
    
    ROLE_CHOICES = [
        ('MEMBER', 'Member'),
        ('LEAD', 'Lead'),
        ('ASSISTANT', 'Assistant'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='team_memberships',
        db_index=True
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='members',
        db_index=True
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='MEMBER',
        db_index=True
    )
    
    # Timestamps
    joined_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'team_memberships'
        verbose_name = 'Team Membership'
        verbose_name_plural = 'Team Memberships'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'team'],
                name='unique_user_team'
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'role']),
            models.Index(fields=['team', 'role']),
            models.Index(fields=['joined_at']),
        ]
        ordering = ['-joined_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.team.name} ({self.role})"
