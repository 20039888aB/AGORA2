"""
Centralized Signal Handlers - Automation System

This module contains all signal handlers for automation
instead of putting logic in individual apps.
"""

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

User = get_user_model()


# User Signals
@receiver(post_save, sender=User)
def user_created(sender, instance, created, **kwargs):
    """
    Handle user creation - send welcome email, create audit log
    """
    if created:
        # Create audit log
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=instance,
            action='USER_CREATE',
            details={
                'user_id': str(instance.id),
                'email': instance.email,
                'role': instance.role,
            },
            ip_address='127.0.0.1'  # System generated
        )
        
        # Send welcome email
        try:
            send_mail(
                subject='Welcome to AgoraProf LMS',
                message=f'Hello {instance.full_name},\n\nWelcome to AgoraProf Learning Management System. Your account has been created successfully.\n\nLogin: {instance.email}\nRole: {instance.role}\n\nBest regards,\nAgoraProf Team',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.email],
                fail_silently=True,
            )
        except Exception as e:
            # Log email failure
            from audit_logs.models import AuditLog
            AuditLog.objects.create(
                user=instance,
                action='EMAIL_SEND_FAILED',
                details={
                    'user_id': str(instance.id),
                    'email': instance.email,
                    'error': str(e),
                    'email_type': 'welcome'
                },
                ip_address='127.0.0.1'
            )


@receiver(pre_save, sender=User)
def user_pre_save(sender, instance, **kwargs):
    """
    Handle user pre-save - validate and set staff flags
    """
    if instance.role == 'SUPERADMIN':
        instance.is_staff = True
        instance.is_superuser = True
    elif instance.role == 'ADMIN':
        instance.is_staff = True
        instance.is_superuser = False
    else:
        instance.is_staff = False
        instance.is_superuser = False


# Course Signals
@receiver(post_save, sender='courses.Course')
def course_created(sender, instance, created, **kwargs):
    """
    Handle course creation - create audit log
    """
    if created:
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=instance.created_by,
            action='COURSE_CREATE',
            details={
                'course_id': str(instance.id),
                'title': instance.title,
                'organization_id': str(instance.organization.id),
            },
            ip_address='127.0.0.1'  # System generated
        )


# Enrollment Signals
@receiver(post_save, sender='enrollments.Enrollment')
def enrollment_created(sender, instance, created, **kwargs):
    """
    Handle enrollment creation - create audit log, send notification
    """
    if created:
        # Create audit log
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=instance.user,
            action='ENROLLMENT_CREATE',
            details={
                'enrollment_id': str(instance.id),
                'course_id': str(instance.course.id),
                'payment_status': instance.payment_status,
            },
            ip_address='127.0.0.1'  # System generated
        )
        
        # Send enrollment confirmation email
        try:
            send_mail(
                subject='Course Enrollment Confirmation',
                message=f'Hello {instance.user.full_name},\n\nYou have successfully enrolled in {instance.course.title}.\n\nEnrollment Date: {instance.enrollment_date}\nPayment Status: {instance.payment_status}\n\nBest regards,\nAgoraProf Team',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.user.email],
                fail_silently=True,
            )
        except Exception as e:
            # Log email failure
            from audit_logs.models import AuditLog
            AuditLog.objects.create(
                user=instance.user,
                action='EMAIL_SEND_FAILED',
                details={
                    'enrollment_id': str(instance.id),
                    'email': instance.user.email,
                    'error': str(e),
                    'email_type': 'enrollment_confirmation'
                },
                ip_address='127.0.0.1'
            )


# Assignment Signals
@receiver(post_save, sender='assignments.AssignmentSubmission')
def assignment_submitted(sender, instance, created, **kwargs):
    """
    Handle assignment submission - create audit log, notify instructor
    """
    if created and instance.status == 'SUBMITTED':
        # Create audit log
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=instance.student,
            action='ASSIGNMENT_SUBMIT',
            details={
                'submission_id': str(instance.id),
                'assignment_id': str(instance.assignment.id),
                'attempt': instance.attempt_number,
            },
            ip_address='127.0.0.1'  # System generated
        )
        
        # Notify instructor
        try:
            instructor = instance.assignment.course.instructor
            send_mail(
                subject='New Assignment Submission',
                message=f'Hello {instructor.full_name},\n\n{instance.student.full_name} has submitted an assignment for {instance.assignment.course.title}.\n\nAssignment: {instance.assignment.title}\nSubmitted: {instance.submitted_at}\n\nBest regards,\nAgoraProf Team',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instructor.email],
                fail_silently=True,
            )
        except Exception as e:
            # Log email failure
            from audit_logs.models import AuditLog
            AuditLog.objects.create(
                user=instance.student,
                action='EMAIL_SEND_FAILED',
                details={
                    'submission_id': str(instance.id),
                    'email': instructor.email,
                    'error': str(e),
                    'email_type': 'assignment_notification'
                },
                ip_address='127.0.0.1'
            )


# Certificate Signals
@receiver(post_save, sender='certificates.Certificate')
def certificate_issued(sender, instance, created, **kwargs):
    """
    Handle certificate issuance - create audit log, send notification
    """
    if created and instance.status == 'ISSUED':
        # Create audit log
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=instance.user,
            action='CERTIFICATE_ISSUE',
            details={
                'certificate_id': str(instance.id),
                'course_id': str(instance.course.id),
                'certificate_number': instance.certificate_number,
            },
            ip_address='127.0.0.1'  # System generated
        )
        
        # Send certificate notification email
        try:
            send_mail(
                subject='Certificate Issued',
                message=f'Congratulations {instance.user.full_name}!\n\nYou have successfully completed {instance.course.title} and a certificate has been issued.\n\nCertificate Number: {instance.certificate_number}\nIssued Date: {instance.issued_date}\n\nYou can download your certificate from your dashboard.\n\nBest regards,\nAgoraProf Team',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.user.email],
                fail_silently=True,
            )
        except Exception as e:
            # Log email failure
            from audit_logs.models import AuditLog
            AuditLog.objects.create(
                user=instance.user,
                action='EMAIL_SEND_FAILED',
                details={
                    'certificate_id': str(instance.id),
                    'email': instance.user.email,
                    'error': str(e),
                    'email_type': 'certificate_notification'
                },
                ip_address='127.0.0.1'
            )


# Login Signals
@receiver(post_save, sender=User)
def user_login(sender, instance, created, **kwargs):
    """
    Handle user login - create audit log
    """
    # Only create audit log if this is not a new user creation
    if not created and hasattr(instance, 'last_login'):
        # Check if last_login was recently updated (login detected)
        from audit_logs.models import AuditLog
        recent_login_logs = AuditLog.objects.filter(
            user=instance,
            action='USER_LOGIN',
            created_at__gte=timezone.now() - timezone.timedelta(minutes=5)
        ).count()
        
        if recent_login_logs == 0:  # Avoid duplicate logs
            AuditLog.objects.create(
                user=instance,
                action='USER_LOGIN',
                details={
                    'user_id': str(instance.id),
                    'ip_address': instance.last_login_ip,
                    'login_count': instance.login_count or 1,
                },
                ip_address=instance.last_login_ip or '127.0.0.1'
            )


# Course Completion Signals
@receiver(post_save, sender='enrollments.Enrollment')
def course_completion(sender, instance, **kwargs):
    """
    Handle course completion - issue certificate automatically
    """
    if (instance.status == 'COMPLETED' and 
        instance.course.certificate_enabled and 
        not instance.certificate_issued):
        
        # Issue certificate automatically
        from services.certificate_service import CertificateService
        try:
            CertificateService.create_certificate(instance)
        except Exception as e:
            # Log certificate issuance failure
            from audit_logs.models import AuditLog
            AuditLog.objects.create(
                user=instance.user,
                action='CERTIFICATE_ISSUE_FAILED',
                details={
                    'enrollment_id': str(instance.id),
                    'course_id': str(instance.course.id),
                    'error': str(e),
                },
                ip_address='127.0.0.1'
            )


# Assignment Grading Signals
@receiver(post_save, sender='assignments.AssignmentSubmission')
def assignment_graded(sender, instance, **kwargs):
    """
    Handle assignment grading - notify student
    """
    if (instance.status == 'GRADED' and 
        instance.score is not None and 
        instance.graded_by):
        
        # Send grading notification email
        try:
            send_mail(
                subject='Assignment Graded',
                message=f'Hello {instance.student.full_name},\n\nYour assignment {instance.assignment.title} has been graded.\n\nScore: {instance.score}/{instance.max_possible_score}\nFeedback: {instance.feedback or "No feedback provided"}\n\nYou can view the detailed feedback in your dashboard.\n\nBest regards,\nAgoraProf Team',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.student.email],
                fail_silently=True,
            )
        except Exception as e:
            # Log email failure
            from audit_logs.models import AuditLog
            AuditLog.objects.create(
                user=instance.student,
                action='EMAIL_SEND_FAILED',
                details={
                    'submission_id': str(instance.id),
                    'email': instance.student.email,
                    'error': str(e),
                    'email_type': 'grading_notification'
                },
                ip_address='127.0.0.1'
            )


# Role Change Signals
def post_role_change(sender, user, old_role, new_role, changed_by=None, **kwargs):
    """
    Handle role change - create audit log, send notification
    """
    # Create audit log
    from audit_logs.models import AuditLog
    AuditLog.objects.create(
        user=changed_by,
        action='USER_ROLE_CHANGE',
        details={
            'user_id': str(user.id),
            'old_role': old_role,
            'new_role': new_role,
            'changed_by': str(changed_by.id) if changed_by else None,
        },
        ip_address=changed_by.last_login_ip if changed_by else '127.0.0.1'
    )
    
    # Send role change notification email
    try:
        send_mail(
            subject='Role Change Notification',
            message=f'Hello {user.full_name},\n\nYour role has been changed from {old_role} to {new_role}.\n\nChanged by: {changed_by.full_name if changed_by else "System"}\nDate: {timezone.now()}\n\nBest regards,\nAgoraProf Team',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
    except Exception as e:
        # Log email failure
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=user,
            action='EMAIL_SEND_FAILED',
            details={
                'user_id': str(user.id),
                'email': user.email,
                'error': str(e),
                'email_type': 'role_change_notification'
            },
            ip_address='127.0.0.1'
        )
