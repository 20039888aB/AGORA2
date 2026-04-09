from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid


class UserQuerySet(models.QuerySet):
    """Custom QuerySet for User model with soft delete support"""
    
    def active(self):
        """Return only active (non-deleted) users"""
        return self.filter(is_deleted=False)
    
    def by_role(self, role):
        """Filter users by role"""
        return self.active().filter(role=role)
    
    def by_organization(self, organization):
        """Filter active users by organization"""
        return self.active().filter(organization=organization)
    
    def managed_by(self, manager):
        """Filter users managed by a specific manager"""
        return self.active().filter(managed_by=manager)


class UserManager(BaseUserManager):
    """
    Custom user manager using email as username
    """
    
    def active(self):
        """Return active users"""
        return self.get_queryset().active()
    
    def by_role(self, role):
        """Return users by role"""
        return self.get_queryset().by_role(role)
    
    def by_organization(self, organization):
        """Return users by organization"""
        return self.get_queryset().by_organization(organization)
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create superuser with explicit role and validation"""
        extra_fields['role'] = 'SUPERADMIN'
        extra_fields['is_staff'] = True
        extra_fields['is_superuser'] = True
        
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model with role-based access control and activity tracking
    """
    
    ROLE_CHOICES = [
        ('SUPERADMIN', 'Super Admin'),
        ('ADMIN', 'Admin'),
        ('MANAGER', 'Manager'),
        ('STUDENT', 'Student'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    username = models.CharField(max_length=150, blank=True, null=True)  # For Django admin compatibility
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='STUDENT', db_index=True)
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,  # Allow blank for students
        related_name='users',
        db_index=True
    )
    managed_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_users',
        db_index=True,
        help_text="Manager who manages this user (for hierarchical management)"
    )
    
    # Activity tracking fields
    login_count = models.PositiveIntegerField(default=0)
    last_active_at = models.DateTimeField(null=True, blank=True)
    role_update_count = models.PositiveIntegerField(default=0)
    
    # Soft delete
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    # Additional fields
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    bio = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)
    original_email = models.EmailField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Custom manager
    objects = UserManager.from_queryset(UserQuerySet)()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['email', 'is_deleted']),
            models.Index(fields=['role', 'organization']),
            models.Index(fields=['managed_by']),
            models.Index(fields=['last_active_at']),
            # Advanced partial index for active users (PostgreSQL)
            models.Index(
                fields=['email'],
                name='active_email_idx',
                condition=models.Q(is_deleted=False)
            ),
        ]
    
    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"
    
    # Role checking methods
    def is_superadmin(self):
        return self.role == 'SUPERADMIN'
    
    def is_admin(self):
        return self.role == 'ADMIN'
    
    def is_admin_or_above(self):
        return self.role in ['SUPERADMIN', 'ADMIN']
    
    def is_manager(self):
        return self.role == 'MANAGER'
    
    def is_manager_or_above(self):
        return self.role in ['SUPERADMIN', 'ADMIN', 'MANAGER']
    
    def is_instructor(self):
        return self.role == 'INSTRUCTOR'
    
    def is_student(self):
        return self.role == 'STUDENT'
    
    # Permission checking methods
    def can_manage_organization(self, organization):
        """Check if user can manage the given organization"""
        if self.is_superadmin():
            return True
        if self.is_admin_or_above() and self.organization == organization:
            return True
        return False
    
    def can_manage_course(self, course):
        """Check if user can manage the given course - Clean, reusable, and scalable"""
        return (
            self.is_admin_or_above or
            self == course.instructor or
            (self.organization and course.organization and self.organization == course.organization and self.role == 'INSTRUCTOR')
        )
    
    def can_manage_user(self, user):
        """Check if user can manage another user"""
        if self.is_superadmin():
            return True
        if self.is_admin_or_above() and self.organization == user.organization:
            return True
        if self.is_manager() and user.managed_by == self:
            return True
        return False
    
    def can_access_user_data(self, user):
        """Check if user can access another user's data"""
        if self.id == user.id:
            return True  # Can always access own data
        return self.can_manage_user(user)
    
    def get_accessible_users_queryset(self):
        """Get queryset of users this user can access"""
        from .services import UserService
        return UserService.get_accessible_users_queryset(self)
    
    # Activity tracking methods
    def increment_login_count(self):
        """Increment login count and update last active"""
        self.login_count += 1
        self.last_active_at = timezone.now()
        self.save(update_fields=['login_count', 'last_active_at'])
    
    def increment_role_update_count(self):
        """Increment role update count"""
        self.role_update_count += 1
        self.save(update_fields=['role_update_count'])
    
    def soft_delete(self):
        """Soft delete user"""
        self.original_email = self.email  # Preserve original email
        self.email = f"deleted_{self.id}@deleted.com"
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['original_email', 'email', 'is_deleted', 'deleted_at'])
    
    def save(self, *args, **kwargs):
        """Override save to handle custom validation logic"""
        # Check if we should skip validation for superuser creation
        skip_validation = kwargs.pop('skip_validation', False)
        
        if not skip_validation:
            # Enforce validation for normal users
            self.full_clean()
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Model validation for business rules"""
        errors = {}
        
        # Set username to email for Django admin compatibility
        if not self.username:
            self.username = self.email
        
        # Remove username validation since we use email as username
        # Check if _errors attribute exists before trying to access it
        if hasattr(self, '_errors') and 'username' in self._errors:
            del self._errors['username']
        
        # Validate managed_by role
        if self.managed_by and self.managed_by.role not in ['MANAGER', 'ADMIN', 'SUPERADMIN']:
            errors['managed_by'] = "Manager must have a managerial role"
        
        # Validate organization requirement
        if self.role not in ['SUPERADMIN', 'STUDENT'] and not self.organization:
            errors['organization'] = "User must belong to an organization"
        
        if errors:
            raise ValidationError(errors)
    
    def restore(self):
        """Restore soft deleted user"""
        self.is_deleted = False
        self.deleted_at = None
        # Restore original email if available
        if self.original_email:
            self.email = self.original_email
        self.save(update_fields=['is_deleted', 'deleted_at', 'email'])
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def is_active_user(self):
        """Check if user is active (not soft deleted and Django active)"""
        return self.is_active and not self.is_deleted
    
    def has_permission(self, resource_type, action_type, scope_object=None, scope_object_type=None):
        """Check if user has specific permission using permissions system"""
        from permissions.services import PermissionService
        return PermissionService.check_user_permission(
            self, resource_type, action_type, scope_object, scope_object_type
        )


class UserProfile(models.Model):
    """
    Extended user profile information
    """
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    employee_id = models.CharField(max_length=50, null=True, blank=True, unique=True)
    department = models.ForeignKey(
        'organizations.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_profiles'
    )
    team = models.ForeignKey(
        'organizations.Team',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_profiles'
    )
    job_title = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=200, blank=True)
    timezone = models.CharField(max_length=50, default='UTC')
    language = models.CharField(max_length=10, default='en')
    notification_preferences = models.JSONField(default=dict)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profiles'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        constraints = [
            models.UniqueConstraint(fields=['user'], name='unique_user_profile')
        ]
        indexes = [
            models.Index(fields=['employee_id']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"{self.user.email} Profile"


class RoleRequest(models.Model):
    """
    Track role change requests for approval workflow
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='role_requests'
    )
    requested_role = models.CharField(max_length=20, choices=User.ROLE_CHOICES)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_role_requests'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_comments = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'role_requests'
        verbose_name = 'Role Request'
        verbose_name_plural = 'Role Requests'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.requested_role} ({self.status})"


# Signal to create UserProfile automatically
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile when User is created"""
    if created:
        UserProfile.objects.create(user=instance)
