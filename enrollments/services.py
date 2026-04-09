from django.db import models, transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Enrollment, LessonProgress, EnrollmentCertificate


class EnrollmentService:
    """
    Service layer for enrollment business logic
    """
    
    @staticmethod
    def create_enrollment(user, course, payment_status='PENDING', payment_amount=0.00, enrolled_by=None):
        """Create new enrollment with validation"""
        # Validate user and course belong to same organization
        if course.organization != user.organization:
            raise ValidationError("Course must belong to same organization as user")
        
        # Check if user is already enrolled
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
        for lesson in course.lessons.filter(is_active=True):
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
                'enrollment': str(enrollment.id),
                'course': str(course.id),
                'user': str(user.id),
                'payment_status': payment_status,
                'payment_amount': float(payment_amount),
            },
            ip_address=(enrolled_by or user).last_login_ip
        )
        
        return enrollment
    
    @staticmethod
    def activate_enrollment(enrollment, activated_by=None):
        """Activate enrollment"""
        if enrollment.status == 'ACTIVE':
            raise ValidationError("Enrollment is already active")
        
        if enrollment.payment_status != 'COMPLETED':
            raise ValidationError("Payment must be completed before activation")
        
        enrollment.activate(activated_by)
        return enrollment
    
    @staticmethod
    def suspend_enrollment(enrollment, suspended_by=None, reason=''):
        """Suspend enrollment"""
        if enrollment.status == 'SUSPENDED':
            raise ValidationError("Enrollment is already suspended")
        
        enrollment.suspend(suspended_by, reason)
        return enrollment
    
    @staticmethod
    def complete_enrollment(enrollment, completed_by=None):
        """Complete enrollment"""
        if enrollment.status == 'COMPLETED':
            raise ValidationError("Enrollment is already completed")
        
        # Check if all lessons are completed
        total_lessons = enrollment.course.lessons.filter(is_active=True).count()
        completed_lessons = enrollment.lesson_progress.filter(status='COMPLETED').count()
        
        if completed_lessons < total_lessons:
            raise ValidationError("All lessons must be completed before course completion")
        
        enrollment.mark_completed(completed_by)
        
        # Issue certificate if course has certificate enabled
        if enrollment.course.certificate_enabled:
            EnrollmentService.issue_certificate(enrollment, completed_by)
        
        return enrollment
    
    @staticmethod
    def update_progress(enrollment, progress_percentage, updated_by=None):
        """Update enrollment progress"""
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
        """Issue certificate for completed enrollment"""
        if enrollment.status != 'COMPLETED':
            raise ValidationError("Enrollment must be completed before issuing certificate")
        
        if enrollment.certificate_issued:
            raise ValidationError("Certificate already issued for this enrollment")
        
        # Get default certificate template
        from certificates.models import CertificateTemplate
        try:
            certificate_template = CertificateTemplate.objects.get(
                organization=enrollment.course.organization,
                is_default=True,
                is_active=True
            )
        except CertificateTemplate.DoesNotExist:
            raise ValidationError("No certificate template found")
        
        # Create certificate
        from certificates.models import Certificate
        certificate = Certificate.objects.create(
            template=certificate_template,
            user=enrollment.user,
            course=enrollment.course,
            enrollment=enrollment,
            issued_by=issued_by,
            issued_date=timezone.now(),
            verification_code=CertificateService.generate_verification_code()
        )
        
        # Create enrollment certificate record
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
                'certificate': str(certificate.id),
                'enrollment': str(enrollment.id),
                'verification_code': certificate.verification_code,
            },
            ip_address=issued_by.last_login_ip
        )
        
        return certificate
    
    @staticmethod
    def get_enrollment_statistics(enrollment):
        """Get comprehensive enrollment statistics"""
        lesson_progress = enrollment.lesson_progress.all()
        
        return {
            'total_lessons': lesson_progress.count(),
            'completed_lessons': lesson_progress.filter(status='COMPLETED').count(),
            'in_progress_lessons': lesson_progress.filter(status='IN_PROGRESS').count(),
            'not_started_lessons': lesson_progress.filter(status='NOT_STARTED').count(),
            'average_lesson_progress': lesson_progress.aggregate(
                avg_progress=models.Avg('progress_percentage')
            )['avg_progress'] or 0,
            'total_time_spent': enrollment.total_time_spent,
            'days_since_enrollment': enrollment.days_since_enrollment,
            'completion_rate': enrollment.completion_rate,
        }
    
    @staticmethod
    def get_user_enrollment_statistics(user):
        """Get user's enrollment statistics"""
        enrollments = Enrollment.objects.filter(user=user, is_active=True)
        
        return {
            'total_enrollments': enrollments.count(),
            'active_enrollments': enrollments.filter(status='ACTIVE').count(),
            'completed_enrollments': enrollments.filter(status='COMPLETED').count(),
            'suspended_enrollments': enrollments.filter(status='SUSPENDED').count(),
            'average_progress': enrollments.aggregate(
                avg_progress=models.Avg('progress_percentage')
            )['avg_progress'] or 0,
            'certificates_issued': enrollments.filter(certificate_issued=True).count(),
        }
    
    @staticmethod
    def get_course_enrollment_statistics(course):
        """Get course enrollment statistics"""
        enrollments = Enrollment.objects.filter(course=course, is_active=True)
        
        return {
            'total_enrollments': enrollments.count(),
            'active_enrollments': enrollments.filter(status='ACTIVE').count(),
            'completed_enrollments': enrollments.filter(status='COMPLETED').count(),
            'suspended_enrollments': enrollments.filter(status='SUSPENDED').count(),
            'average_progress': enrollments.aggregate(
                avg_progress=models.Avg('progress_percentage')
            )['avg_progress'] or 0,
            'completion_rate': enrollments.filter(status='COMPLETED').count() / enrollments.count() * 100 if enrollments.exists() else 0,
            'total_revenue': enrollments.aggregate(
                total=models.Sum('payment_amount')
            )['total'] or 0,
        }


class LessonProgressService:
    """
    Service layer for lesson progress business logic
    """
    
    @staticmethod
    def create_lesson_progress(enrollment, lesson):
        """Create lesson progress record"""
        return LessonProgress.objects.create(
            enrollment=enrollment,
            lesson=lesson
        )
    
    @staticmethod
    def update_lesson_progress(lesson_progress, progress_percentage, time_spent=None, updated_by=None):
        """Update lesson progress"""
        lesson_progress.update_progress(progress_percentage, updated_by)
        
        if time_spent:
            lesson_progress.time_spent = time_spent
            lesson_progress.save(update_fields=['time_spent'])
        
        # Update enrollment progress
        enrollment = lesson_progress.enrollment
        all_lesson_progress = enrollment.lesson_progress.all()
        
        if all_lesson_progress.exists():
            total_progress = sum(lp.progress_percentage for lp in all_lesson_progress)
            average_progress = total_progress / all_lesson_progress.count()
            EnrollmentService.update_progress(enrollment, average_progress, updated_by)
        
        return lesson_progress
    
    @staticmethod
    def complete_lesson(lesson_progress, completed_by=None):
        """Complete lesson"""
        lesson_progress.mark_completed(completed_by)
        
        # Update enrollment progress
        enrollment = lesson_progress.enrollment
        all_lesson_progress = enrollment.lesson_progress.all()
        
        if all_lesson_progress.exists():
            total_progress = sum(lp.progress_percentage for lp in all_lesson_progress)
            average_progress = total_progress / all_lesson_progress.count()
            EnrollmentService.update_progress(enrollment, average_progress, completed_by)
        
        return lesson_progress
    
    @staticmethod
    def get_lesson_statistics(lesson):
        """Get lesson statistics"""
        progress_records = LessonProgress.objects.filter(lesson=lesson)
        
        return {
            'total_students': progress_records.count(),
            'completed_students': progress_records.filter(status='COMPLETED').count(),
            'in_progress_students': progress_records.filter(status='IN_PROGRESS').count(),
            'not_started_students': progress_records.filter(status='NOT_STARTED').count(),
            'average_progress': progress_records.aggregate(
                avg_progress=models.Avg('progress_percentage')
            )['avg_progress'] or 0,
            'average_time_spent': progress_records.aggregate(
                avg_time=models.Avg('time_spent')
            )['avg_time'] or timezone.timedelta(0),
        }


class CertificateService:
    """
    Service layer for certificate business logic
    """
    
    @staticmethod
    def generate_verification_code():
        """Generate unique verification code"""
        import random
        import string
        
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
            if not EnrollmentCertificate.objects.filter(verification_code=code).exists():
                return code
    
    @staticmethod
    def verify_certificate(verification_code):
        """Verify certificate by verification code"""
        try:
            certificate = EnrollmentCertificate.objects.get(
                verification_code=verification_code,
                is_revoked=False
            )
            
            return {
                'valid': True,
                'certificate': certificate,
                'is_expired': certificate.is_expired,
            }
        except EnrollmentCertificate.DoesNotExist:
            return {
                'valid': False,
                'error': 'Certificate not found or revoked'
            }
    
    @staticmethod
    def revoke_certificate(certificate, revoked_by=None, reason=''):
        """Revoke certificate"""
        certificate.revoke(revoked_by, reason)
        return certificate
    
    @staticmethod
    def get_certificate_statistics(organization=None):
        """Get certificate statistics"""
        certificates = EnrollmentCertificate.objects.all()
        
        if organization:
            certificates = certificates.filter(
                enrollment__course__organization=organization
            )
        
        return {
            'total_certificates': certificates.count(),
            'active_certificates': certificates.filter(is_revoked=False).count(),
            'revoked_certificates': certificates.filter(is_revoked=True).count(),
            'expired_certificates': certificates.filter(
                expiry_date__lt=timezone.now()
            ).count(),
            'certificates_this_month': certificates.filter(
                issued_date__gte=timezone.now() - timezone.timedelta(days=30)
            ).count(),
        }
