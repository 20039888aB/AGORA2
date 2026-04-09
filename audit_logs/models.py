from django.db import models
from django.contrib.auth import get_user_model
import uuid


User = get_user_model()


class AuditLog(models.Model):
    """
    Comprehensive audit logging for all system actions
    """
    
    ACTION_CHOICES = [
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('ROLE_CHANGE', 'Role Change'),
        ('USER_CREATE', 'User Create'),
        ('USER_UPDATE', 'User Update'),
        ('USER_DELETE', 'User Delete'),
        ('ORGANIZATION_CREATE', 'Organization Create'),
        ('ORGANIZATION_UPDATE', 'Organization Update'),
        ('DEPARTMENT_CREATE', 'Department Create'),
        ('DEPARTMENT_UPDATE', 'Department Update'),
        ('DEPARTMENT_MOVE', 'Department Move'),
        ('DEPARTMENT_HEAD_CHANGE', 'Department Head Change'),
        ('TEAM_CREATE', 'Team Create'),
        ('TEAM_UPDATE', 'Team Update'),
        ('TEAM_LEAD_CHANGE', 'Team Lead Change'),
        ('TEAM_MEMBER_ADD', 'Team Member Add'),
        ('TEAM_MEMBER_REMOVE', 'Team Member Remove'),
        ('COURSE_CREATE', 'Course Create'),
        ('COURSE_UPDATE', 'Course Update'),
        ('ENROLLMENT_CREATE', 'Enrollment Create'),
        ('ASSIGNMENT_CREATE', 'Assignment Create'),
        ('SUBSCRIPTION_CHANGE', 'Subscription Change'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        db_index=True
    )
    target_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='target_audit_logs',
        db_index=True
    )
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        db_index=True
    )
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'audit_logs'
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        indexes = [
            models.Index(fields=['user', 'action', 'created_at']),
            models.Index(fields=['target_user', 'action']),
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email if self.user else 'System'} - {self.action} - {self.created_at}"
