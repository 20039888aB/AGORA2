from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class TrainingEvent(models.Model):
    """
    Training events for calendar scheduling
    """
    
    EVENT_TYPES = [
        ('TRAINING', 'Training Session'),
        ('WORKSHOP', 'Workshop'),
        ('WEBINAR', 'Webinar'),
        ('MEETING', 'Meeting'),
        ('DEADLINE', 'Deadline'),
        ('REVIEW', 'Performance Review'),
        ('OTHER', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('POSTPONED', 'Postponed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300, db_index=True)
    description = models.TextField(blank=True)
    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPES,
        default='TRAINING',
        db_index=True
    )
    
    # Relationships
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='training_events',
        db_index=True
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_events',
        db_index=True
    )
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='training_events',
        db_index=True
    )
    
    # Participants
    participants = models.ManyToManyField(
        User,
        related_name='training_events',
        blank=True,
        db_index=True
    )
    max_participants = models.PositiveIntegerField(default=0, blank=True)
    
    # Timing
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(db_index=True)
    timezone = models.CharField(max_length=50, default='UTC')
    all_day = models.BooleanField(default=False, db_index=True)
    
    # Location
    location = models.CharField(max_length=500, blank=True)
    virtual_meeting_url = models.URLField(max_length=500, blank=True)
    is_virtual = models.BooleanField(default=False, db_index=True)
    
    # Status and settings
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='SCHEDULED',
        db_index=True
    )
    is_recurring = models.BooleanField(default=False, db_index=True)
    recurring_pattern = models.JSONField(default=dict, blank=True)
    
    # Reminders
    reminder_sent = models.BooleanField(default=False, db_index=True)
    reminder_minutes_before = models.PositiveIntegerField(default=60)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'training_events'
        verbose_name = 'Training Event'
        verbose_name_plural = 'Training Events'
        indexes = [
            models.Index(fields=['organization', 'start_time']),
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['created_by', 'start_time']),
            models.Index(fields=['event_type']),
            models.Index(fields=['status']),
            models.Index(fields=['start_time']),
            models.Index(fields=['end_time']),
            models.Index(fields=['is_virtual']),
            models.Index(fields=['is_recurring']),
        ]
        ordering = ['start_time']
    
    def __str__(self):
        return f"{self.title} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def duration_minutes(self):
        """Get event duration in minutes"""
        if self.all_day:
            return 24 * 60  # 24 hours in minutes
        
        if self.end_time and self.start_time:
            delta = self.end_time - self.start_time
            return int(delta.total_seconds() / 60)
        return 0
    
    @property
    def duration_display(self):
        """Get human-readable duration"""
        minutes = self.duration_minutes
        if minutes == 0:
            return "No duration"
        elif minutes < 60:
            return f"{minutes} minutes"
        elif minutes == 60:
            return "1 hour"
        elif minutes < 1440:  # Less than 24 hours
            hours = minutes // 60
            remaining_minutes = minutes % 60
            if remaining_minutes == 0:
                return f"{hours} hours"
            else:
                return f"{hours}h {remaining_minutes}m"
        else:
            days = minutes // (24 * 60)
            return f"{days} days"
    
    @property
    def participant_count(self):
        """Get number of participants"""
        return self.participants.count()
    
    @property
    def is_full(self):
        """Check if event is at maximum capacity"""
        if self.max_participants == 0:
            return False
        return self.participant_count >= self.max_participants
    
    @property
    def is_upcoming(self):
        """Check if event is upcoming"""
        return self.start_time > timezone.now()
    
    @property
    def is_past(self):
        """Check if event is in the past"""
        return self.end_time < timezone.now()
    
    @property
    def is_now(self):
        """Check if event is currently happening"""
        now = timezone.now()
        return self.start_time <= now <= self.end_time
    
    def can_user_join(self, user):
        """Check if user can join this event"""
        if not user or not user.is_authenticated:
            return False
        
        # Check organization access
        if user.organization != self.organization:
            return False
        
        # Check if already a participant
        if self.participants.filter(id=user.id).exists():
            return True
        
        # Check if event is full
        if self.is_full:
            return False
        
        # Check if event is still accepting participants
        if self.status in ['CANCELLED', 'COMPLETED']:
            return False
        
        return True
    
    def add_participant(self, user):
        """Add user as participant"""
        if self.can_user_join(user):
            self.participants.add(user)
            return True
        return False
    
    def remove_participant(self, user):
        """Remove user from participants"""
        if self.participants.filter(id=user.id).exists():
            self.participants.remove(user)
            return True
        return False
    
    def clean(self):
        """Model validation"""
        errors = {}
        
        # Validate timing
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                errors['end_time'] = "End time must be after start time"
        
        # Validate created_by belongs to same organization
        if self.created_by and self.created_by.organization != self.organization:
            errors['created_by'] = "Event creator must belong to same organization"
        
        # Validate course belongs to same organization
        if self.course and self.course.organization != self.organization:
            errors['course'] = "Course must belong to same organization"
        
        # Validate virtual meeting requirements
        if self.is_virtual and not self.virtual_meeting_url:
            errors['virtual_meeting_url'] = "Virtual events must have a meeting URL"
        
        if errors:
            raise ValidationError(errors)


class EventAttendance(models.Model):
    """
    Track attendance for training events
    """
    
    ATTENDANCE_STATUS = [
        ('ATTENDED', 'Attended'),
        ('ABSENT', 'Absent'),
        ('LATE', 'Late'),
        ('EXCUSED', 'Excused'),
        ('PENDING', 'Pending'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        TrainingEvent,
        on_delete=models.CASCADE,
        related_name='attendances',
        db_index=True
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='event_attendances',
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=ATTENDANCE_STATUS,
        default='PENDING',
        db_index=True
    )
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'event_attendances'
        verbose_name = 'Event Attendance'
        verbose_name_plural = 'Event Attendances'
        constraints = [
            models.UniqueConstraint(
                fields=['event', 'user'],
                name='unique_event_user_attendance'
            ),
        ]
        indexes = [
            models.Index(fields=['event', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.event.title} ({self.status})"
    
    @property
    def attendance_duration(self):
        """Calculate attendance duration in minutes"""
        if self.check_in_time and self.check_out_time:
            delta = self.check_out_time - self.check_in_time
            return int(delta.total_seconds() / 60)
        return 0
    
    def check_in(self):
        """Check in user to event"""
        if not self.check_in_time:
            self.check_in_time = timezone.now()
            self.status = 'ATTENDED'
            self.save(update_fields=['check_in_time', 'status', 'updated_at'])
            return True
        return False
    
    def check_out(self):
        """Check out user from event"""
        if self.check_in_time and not self.check_out_time:
            self.check_out_time = timezone.now()
            self.save(update_fields=['check_out_time', 'updated_at'])
            return True
        return False
