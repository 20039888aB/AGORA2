"""
Enrollment Service - Centralized Enrollment Business Logic

This service contains all enrollment-related business logic that should be used
instead of putting logic directly in models or views.
"""

from django.db import models, transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db.models import Q, Avg, Count, Sum
import uuid

User = get_user_model()


class EnrollmentService:
    """
    Service layer for Enrollment business logic
    """
    
    @staticmethod
    def create_enrollment(user, course, payment_status='PENDING', payment_amount=0.00, enrolled_by=None):
        """
        Create new enrollment with validation and business logic
        """
        # Validate user and course belong to same organization
        if course.organization != user.organization:
            raise ValidationError("Course must belong to same organization as user")
        
        # Check if user is already enrolled
        from enrollments.models import Enrollment
        if Enrollment.objects.filter(user=user, course=course, is_active=True).exists():
            raise ValidationError("User is already enrolled in this course")
        
        # Check course capacity
        if course.max_students > 0:
            current_enrollments = Enrollment.objects.filter(
                course=course,
                status='ACTIVE',
                is_active=True
            ).count()
            if current_enrollments >= course.max_students:
                raise ValidationError("Course has reached maximum capacity")
        
        # Check course is accessible
        if not course.is_accessible:
            raise ValidationError("Course is not accessible for enrollment")
        
        # Create enrollment
        enrollment = Enrollment.objects.create(
            user=user,
            course=course,
            payment_status=payment_status,
            payment_amount=payment_amount,
            status='PENDING' if payment_status != 'COMPLETED' else 'ACTIVE',
            start_date=timezone.now() if payment_status == 'COMPLETED' else None
        )
        
        # Create lesson progress records
        from courses.models import Lesson
        lessons = Lesson.objects.filter(module__course=course, is_active=True)
        for lesson in lessons:
            from enrollments.models import LessonProgress
            LessonProgress.objects.create(
                enrollment=enrollment,
                lesson=lesson
            )
        
        # Log enrollment creation
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=enrolled_by or user,
            action='ENROLLMENT_CREATE',
            details={
                'enrollment_id': str(enrollment.id),
                'course_id': str(course.id),
                'user_id': str(user.id),
                'payment_status': payment_status,
                'payment_amount': float(payment_amount),
            },
            ip_address=(enrolled_by or user).last_login_ip
        )
        
        return enrollment
    
    @staticmethod
    def activate_enrollment(enrollment, activated_by=None):
        """
        Activate enrollment
        """
        if enrollment.status == 'ACTIVE':
            raise ValidationError("Enrollment is already active")
        
        if enrollment.payment_status != 'COMPLETED':
            raise ValidationError("Payment must be completed before activation")
        
        enrollment.status = 'ACTIVE'
        enrollment.start_date = timezone.now()
        enrollment.save(update_fields=['status', 'start_date'])
        
        # Log enrollment activation
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=activated_by,
            action='ENROLLMENT_ACTIVATE',
            details={
                'enrollment_id': str(enrollment.id),
                'course_id': str(enrollment.course.id)
            },
            ip_address=activated_by.last_login_ip if activated_by else None
        )
        
        return enrollment
    
    @staticmethod
    def complete_enrollment(enrollment, completed_by=None):
        """
        Complete enrollment
        """
        if enrollment.status == 'COMPLETED':
            raise ValidationError("Enrollment is already completed")
        
        # Check if all lessons are completed
        from courses.models import Lesson
        total_lessons = Lesson.objects.filter(module__course=enrollment.course, is_active=True).count()
        completed_lessons = enrollment.lesson_progress.filter(status='COMPLETED').count()
        
        if completed_lessons < total_lessons:
            raise ValidationError("All lessons must be completed before course completion")
        
        enrollment.status = 'COMPLETED'
        enrollment.completion_date = timezone.now()
        enrollment.progress_percentage = 100.00
        enrollment.save(update_fields=['status', 'completion_date', 'progress_percentage'])
        
        # Issue certificate if course has certificate enabled
        if enrollment.course.certificate_enabled:
            EnrollmentService.issue_certificate(enrollment, completed_by)
        
        # Log enrollment completion
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=completed_by,
            action='ENROLLMENT_COMPLETE',
            details={
                'enrollment_id': str(enrollment.id),
                'course_id': str(enrollment.course.id),
                'completion_date': enrollment.completion_date.isoformat()
            },
            ip_address=completed_by.last_login_ip if completed_by else None
        )
        
        return enrollment
    
    @staticmethod
    def update_progress(enrollment, progress_percentage, updated_by=None):
        """
        Update enrollment progress
        """
        if progress_percentage < 0:
            progress_percentage = 0
        elif progress_percentage > 100:
            progress_percentage = 100
        
        enrollment.progress_percentage = progress_percentage
        enrollment.last_accessed_at = timezone.now()
        enrollment.save(update_fields=['progress_percentage', 'last_accessed_at'])
        
        # Check if enrollment should be completed
        if progress_percentage >= 100 and enrollment.status != 'COMPLETED':
            EnrollmentService.complete_enrollment(enrollment, updated_by)
        
        return enrollment
    
    @staticmethod
    def issue_certificate(enrollment, issued_by=None):
        """
        Issue certificate for completed enrollment
        """
        if enrollment.status != 'COMPLETED':
            raise ValidationError("Enrollment must be completed before issuing certificate")
        
        if enrollment.certificate_issued:
            raise ValidationError("Certificate already issued for this enrollment")
        
        # Get default certificate template
        from certificates.models import CertificateTemplate
        try:
            template = CertificateTemplate.objects.get(
                organization=enrollment.course.organization,
                is_default=True,
                is_active=True
            )
        except CertificateTemplate.DoesNotExist:
            raise ValidationError("No certificate template found")
        
        # Create certificate
        from certificates.models import Certificate
        certificate = Certificate.objects.create(
            template=template,
            user=enrollment.user,
            course=enrollment.course,
            enrollment=enrollment,
            issued_by=issued_by,
            issued_date=timezone.now(),
            recipient_name=enrollment.user.full_name,
            course_name=enrollment.course.title,
            status='ISSUED'
        )
        
        # Create enrollment certificate record
        from enrollments.models import EnrollmentCertificate
        enrollment_certificate = EnrollmentCertificate.objects.create(
            enrollment=enrollment,
            certificate=certificate,
            verification_code=certificate.verification_code
        )
        
        # Update enrollment
        enrollment.certificate_issued = True
        enrollment.certificate_url = certificate.download_url
        enrollment.save(update_fields=['certificate_issued', 'certificate_url'])
        
        # Log certificate issuance
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=issued_by,
            action='CERTIFICATE_ISSUE',
            details={
                'certificate_id': str(certificate.id),
                'enrollment_id': str(enrollment.id),
                'verification_code': certificate.verification_code
            },
            ip_address=issued_by.last_login_ip if issued_by else None
        )
        
        return certificate
    
    @staticmethod
    def update_lesson_progress(lesson_progress, progress_percentage, time_spent=None, updated_by=None):
        """
        Update lesson progress
        """
        lesson_progress.progress_percentage = progress_percentage
        lesson_progress.last_accessed_at = timezone.now()
        
        if time_spent:
            lesson_progress.time_spent = time_spent
        
        if progress_percentage >= 100:
            lesson_progress.status = 'COMPLETED'
            lesson_progress.completed_at = timezone.now()
        elif lesson_progress.status == 'NOT_STARTED':
            lesson_progress.status = 'IN_PROGRESS'
        
        lesson_progress.save()
        
        # Update enrollment progress
        enrollment = lesson_progress.enrollment
        all_lesson_progress = enrollment.lesson_progress.all()
        
        if all_lesson_progress.exists():
            total_progress = sum(lp.progress_percentage for lp in all_lesson_progress)
            average_progress = total_progress / all_lesson_progress.count()
            EnrollmentService.update_progress(enrollment, average_progress, updated_by)
        
        # Log lesson progress update
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=updated_by or lesson_progress.user,
            action='LESSON_PROGRESS_UPDATE',
            details={
                'lesson_progress_id': str(lesson_progress.id),
                'lesson_id': str(lesson_progress.lesson.id),
                'enrollment_id': str(enrollment.id),
                'progress': float(progress_percentage)
            },
            ip_address=(updated_by or lesson_progress.user).last_login_ip
        )
        
        return lesson_progress
    
    @staticmethod
    def get_enrollment_statistics(enrollment):
        """
        Get comprehensive enrollment statistics
        """
        lesson_progress = enrollment.lesson_progress.all()
        
        return {
            'total_lessons': lesson_progress.count(),
            'completed_lessons': lesson_progress.filter(status='COMPLETED').count(),
            'in_progress_lessons': lesson_progress.filter(status='IN_PROGRESS').count(),
            'not_started_lessons': lesson_progress.filter(status='NOT_STARTED').count(),
            'average_lesson_progress': lesson_progress.aggregate(
                avg_progress=Avg('progress_percentage')
            )['avg_progress'] or 0,
            'total_time_spent': enrollment.total_time_spent,
            'days_since_enrollment': enrollment.days_since_enrollment,
            'completion_rate': enrollment.completion_rate,
        }
    
    @staticmethod
    def get_user_enrollment_statistics(user):
        """
        Get user's enrollment statistics
        """
        from enrollments.models import Enrollment
        enrollments = Enrollment.objects.filter(user=user, is_active=True)
        
        return {
            'total_enrollments': enrollments.count(),
            'active_enrollments': enrollments.filter(status='ACTIVE').count(),
            'completed_enrollments': enrollments.filter(status='COMPLETED').count(),
            'suspended_enrollments': enrollments.filter(status='SUSPENDED').count(),
            'average_progress': enrollments.aggregate(
                avg_progress=Avg('progress_percentage')
            )['avg_progress'] or 0,
            'certificates_issued': enrollments.filter(certificate_issued=True).count(),
            'total_spent': enrollments.aggregate(
                total=Sum('payment_amount')
            )['total'] or 0,
        }
    
    @staticmethod
    def get_course_enrollment_statistics(course):
        """
        Get course enrollment statistics
        """
        from enrollments.models import Enrollment
        enrollments = Enrollment.objects.filter(course=course, is_active=True)
        
        return {
            'total_enrollments': enrollments.count(),
            'active_enrollments': enrollments.filter(status='ACTIVE').count(),
            'completed_enrollments': enrollments.filter(status='COMPLETED').count(),
            'suspended_enrollments': enrollments.filter(status='SUSPENDED').count(),
            'average_progress': enrollments.aggregate(
                avg_progress=Avg('progress_percentage')
            )['avg_progress'] or 0,
            'completion_rate': (enrollments.filter(status='COMPLETED').count() / enrollments.count() * 100) if enrollments.exists() else 0,
            'total_revenue': enrollments.aggregate(
                total=Sum('payment_amount')
            )['total'] or 0,
            'certificates_issued': enrollments.filter(certificate_issued=True).count(),
        }
    
    @staticmethod
    def get_organization_enrollment_statistics(organization):
        """
        Get organization enrollment statistics
        """
        from enrollments.models import Enrollment
        enrollments = Enrollment.objects.filter(course__organization=organization, is_active=True)
        
        return {
            'total_enrollments': enrollments.count(),
            'active_enrollments': enrollments.filter(status='ACTIVE').count(),
            'completed_enrollments': enrollments.filter(status='COMPLETED').count(),
            'suspended_enrollments': enrollments.filter(status='SUSPENDED').count(),
            'average_progress': enrollments.aggregate(
                avg_progress=Avg('progress_percentage')
            )['avg_progress'] or 0,
            'total_revenue': enrollments.aggregate(
                total=Sum('payment_amount')
            )['total'] or 0,
            'certificates_issued': enrollments.filter(certificate_issued=True).count(),
            'enrollments_this_month': enrollments.filter(
                enrollment_date__gte=timezone.now() - timezone.timedelta(days=30)
            ).count(),
            'completions_this_month': enrollments.filter(
                completion_date__gte=timezone.now() - timezone.timedelta(days=30)
            ).count(),
        }
    
    @staticmethod
    def get_user_enrollments(user, status=None, course=None):
        """
        Get user enrollments with filters
        """
        from enrollments.models import Enrollment
        enrollments = Enrollment.objects.filter(user=user, is_active=True)
        
        if status:
            enrollments = enrollments.filter(status=status)
        
        if course:
            enrollments = enrollments.filter(course=course)
        
        return enrollments
    
    @staticmethod
    def get_course_enrollments(course, status=None):
        """
        Get course enrollments with filters
        """
        from enrollments.models import Enrollment
        enrollments = Enrollment.objects.filter(course=course, is_active=True)
        
        if status:
            enrollments = enrollments.filter(status=status)
        
        return enrollments
    
    @staticmethod
    def validate_enrollment_access(user, enrollment, action='view'):
        """
        Validate if user has access to enrollment
        """
        if user.is_superadmin():
            return True
        
        if action == 'view':
            return (enrollment.user == user or 
                    enrollment.course.organization == user.organization)
        
        if action in ['edit', 'delete', 'grade']:
            return (enrollment.course.organization == user.organization and 
                    user.is_admin_or_above())
        
        if action == 'progress':
            return enrollment.user == user
        
        return False
    
    @staticmethod
    def get_recent_completions(organization=None, limit=10):
        """
        Get recent course completions
        """
        from enrollments.models import Enrollment
        enrollments = Enrollment.objects.filter(
            status='COMPLETED',
            is_active=True
        )
        
        if organization:
            enrollments = enrollments.filter(course__organization=organization)
        
        return enrollments.order_by('-completion_date')[:limit]
    
    @staticmethod
    def get_popular_courses(organization=None, limit=10):
        """
        Get popular courses by enrollment count
        """
        from enrollments.models import Enrollment
        courses = Enrollment.objects.filter(
            is_active=True
        ).values('course').annotate(
            enrollment_count=Count('id')
        ).order_by('-enrollment_count')[:limit]
        
        if organization:
            courses = courses.filter(course__organization=organization)
        
        return courses
