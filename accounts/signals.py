from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User
from audit_logs.models import AuditLog


@receiver(post_save, sender=User)
def log_role_change(sender, instance, created, **kwargs):
    """
    Signal to log role changes automatically
    """
    if created:
        return  # Don't log on creation
    
    # Check if role was updated
    if hasattr(instance, '_original_role'):
        if instance._original_role != instance.role:
            # Get the user who made the change (from request context if available)
            changed_by = getattr(instance, '_role_change_user', None)
            
            if changed_by:
                AuditLog.objects.create(
                    user=changed_by,
                    action='ROLE_CHANGE',
                    target_user=instance,
                    details={
                        'old_role': instance._original_role,
                        'new_role': instance.role,
                        'changed_via': 'signal'
                    },
                    ip_address=getattr(changed_by, 'last_login_ip', None)
                )


@receiver(post_save, sender=User)
def store_original_role(sender, instance, **kwargs):
    """
    Store original role before save for comparison
    """
    if not instance._state.adding:  # Only for updates, not new creation
        instance._original_role = getattr(instance, 'role', None)


# Custom signal for role changes
from django.dispatch import Signal

role_change_signal = Signal()


def trigger_role_change(user, old_role, new_role, changed_by, ip_address=None):
    """
    Helper function to trigger role change signal
    """
    role_change_signal.send(
        sender=User,
        user=user,
        old_role=old_role,
        new_role=new_role,
        changed_by=changed_by,
        ip_address=ip_address
    )
