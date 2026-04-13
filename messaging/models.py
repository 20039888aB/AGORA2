from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class Message(models.Model):
    """
    Messages for team communication
    """
    
    MESSAGE_TYPES = [
        ('ANNOUNCEMENT', 'Announcement'),
        ('DIRECT', 'Direct Message'),
        ('GROUP', 'Group Message'),
        ('NOTIFICATION', 'Notification'),
        ('REMINDER', 'Reminder'),
    ]
    
    PRIORITY_LEVELS = [
        ('LOW', 'Low'),
        ('NORMAL', 'Normal'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.CharField(max_length=300, db_index=True)
    content = models.TextField()
    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPES,
        default='ANNOUNCEMENT',
        db_index=True
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_LEVELS,
        default='NORMAL',
        db_index=True
    )
    
    # Relationships
    sender = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_messages',
        db_index=True
    )
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='messages',
        db_index=True
    )
    
    # Recipients
    recipients = models.ManyToManyField(
        User,
        related_name='received_messages',
        blank=True,
        db_index=True
    )
    recipient_groups = models.JSONField(default=list, blank=True)  # Store group types
    
    # Message settings
    allow_replies = models.BooleanField(default=True, db_index=True)
    requires_acknowledgment = models.BooleanField(default=False, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Status and timestamps
    is_draft = models.BooleanField(default=False, db_index=True)
    is_sent = models.BooleanField(default=False, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'messages'
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        indexes = [
            models.Index(fields=['organization', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
            models.Index(fields=['message_type']),
            models.Index(fields=['priority']),
            models.Index(fields=['is_sent']),
            models.Index(fields=['sent_at']),
            models.Index(fields=['expires_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.subject} - {self.sender.email if self.sender else 'System'}"
    
    @property
    def recipient_count(self):
        """Get number of recipients"""
        return self.recipients.count()
    
    @property
    def is_expired(self):
        """Check if message has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    @property
    def can_be_replied_to(self):
        """Check if message can be replied to"""
        return self.allow_replies and not self.is_expired and self.is_sent
    
    def send_message(self, recipients=None):
        """Send message to recipients"""
        if self.is_sent:
            return False
        
        if recipients:
            self.recipients.set(recipients)
        
        self.is_sent = True
        self.sent_at = timezone.now()
        self.save(update_fields=['is_sent', 'sent_at'])
        
        # Create message receipts for all recipients
        for recipient in self.recipients.all():
            MessageReceipt.objects.create(
                message=self,
                recipient=recipient,
                status='DELIVERED'
            )
        
        return True
    
    def add_recipient(self, user):
        """Add a recipient to the message"""
        if not self.recipients.filter(id=user.id).exists():
            self.recipients.add(user)
            
            # Create receipt if message is already sent
            if self.is_sent:
                MessageReceipt.objects.create(
                    message=self,
                    recipient=user,
                    status='DELIVERED'
                )
            return True
        return False
    
    def remove_recipient(self, user):
        """Remove a recipient from the message"""
        if self.recipients.filter(id=user.id).exists():
            self.recipients.remove(user)
            
            # Delete receipt if exists
            MessageReceipt.objects.filter(
                message=self,
                recipient=user
            ).delete()
            return True
        return False
    
    def clean(self):
        """Model validation"""
        errors = {}
        
        # Validate sender belongs to same organization
        if self.sender and self.sender.organization != self.organization:
            errors['sender'] = "Sender must belong to same organization"
        
        # Validate expiration date
        if self.expires_at and self.expires_at <= timezone.now():
            errors['expires_at'] = "Expiration date must be in the future"
        
        # Validate draft messages
        if self.is_draft and self.is_sent:
            errors['is_draft'] = "Message cannot be both draft and sent"
        
        if errors:
            raise ValidationError(errors)


class MessageReceipt(models.Model):
    """
    Track message delivery and read status
    """
    
    STATUS_CHOICES = [
        ('DELIVERED', 'Delivered'),
        ('READ', 'Read'),
        ('ACKNOWLEDGED', 'Acknowledged'),
        ('FAILED', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='receipts',
        db_index=True
    )
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='message_receipts',
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DELIVERED',
        db_index=True
    )
    read_at = models.DateTimeField(null=True, blank=True, db_index=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'message_receipts'
        verbose_name = 'Message Receipt'
        verbose_name_plural = 'Message Receipts'
        constraints = [
            models.UniqueConstraint(
                fields=['message', 'recipient'],
                name='unique_message_recipient_receipt'
            ),
        ]
        indexes = [
            models.Index(fields=['message', 'status']),
            models.Index(fields=['recipient', 'status']),
            models.Index(fields=['read_at']),
            models.Index(fields=['acknowledged_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.recipient.email} - {self.message.subject} ({self.status})"
    
    def mark_as_read(self):
        """Mark message as read"""
        if self.status == 'DELIVERED':
            self.status = 'READ'
            self.read_at = timezone.now()
            self.save(update_fields=['status', 'read_at', 'updated_at'])
            return True
        return False
    
    def acknowledge(self):
        """Acknowledge message"""
        if self.message.requires_acknowledgment:
            self.status = 'ACKNOWLEDGED'
            self.acknowledged_at = timezone.now()
            if not self.read_at:
                self.read_at = self.acknowledged_at
            self.save(update_fields=['status', 'read_at', 'acknowledged_at', 'updated_at'])
            return True
        return False


class MessageReply(models.Model):
    """
    Replies to messages
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parent_message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='replies',
        db_index=True
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='message_replies',
        db_index=True
    )
    content = models.TextField()
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'message_replies'
        verbose_name = 'Message Reply'
        verbose_name_plural = 'Message Replies'
        indexes = [
            models.Index(fields=['parent_message', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
        ]
        ordering = ['created_at']
    
    def __str__(self):
        return f"Reply to {self.parent_message.subject} by {self.sender.email if self.sender else 'Unknown'}"


class MessageTemplate(models.Model):
    """
    Predefined message templates
    """
    
    TEMPLATE_TYPES = [
        ('ANNOUNCEMENT', 'Announcement'),
        ('WELCOME', 'Welcome'),
        ('REMINDER', 'Reminder'),
        ('NOTIFICATION', 'Notification'),
        ('URGENT', 'Urgent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, db_index=True)
    template_type = models.CharField(
        max_length=20,
        choices=TEMPLATE_TYPES,
        db_index=True
    )
    subject = models.CharField(max_length=300)
    content = models.TextField()
    
    # Template variables (JSON field for storing variable names)
    variables = models.JSONField(default=list, blank=True)
    
    # Organization and status
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='message_templates',
        db_index=True
    )
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'message_templates'
        verbose_name = 'Message Template'
        verbose_name_plural = 'Message Templates'
        indexes = [
            models.Index(fields=['organization', 'template_type']),
            models.Index(fields=['organization', 'is_active']),
        ]
        ordering = ['template_type', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.organization.name}"
    
    def render(self, context=None):
        """Render template with context variables"""
        if context is None:
            context = {}
        
        # Simple template rendering
        rendered_subject = self.subject
        rendered_content = self.content
        
        for variable in self.variables:
            value = context.get(variable, f'{{{variable}}}')
            rendered_subject = rendered_subject.replace(f'{{{variable}}}', str(value))
            rendered_content = rendered_content.replace(f'{{{variable}}}', str(value))
        
        return rendered_subject, rendered_content
