from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Enrollment
from certificates.models import Certificate, CertificateTemplate
import uuid


@receiver(post_save, sender=Enrollment)
def generate_certificate_on_completion(sender, instance, created, **kwargs):
    """
    Automatically generate certificate when enrollment is marked as completed
    """
    # Only process if this is not a new enrollment and status is COMPLETED
    if not created and instance.status == 'COMPLETED':
        try:
            # Check if certificate already exists
            existing_certificate = Certificate.objects.filter(
                user=instance.user,
                course=instance.course,
                enrollment=instance
            ).first()
            
            if existing_certificate:
                # Certificate already exists, update if needed
                if existing_certificate.status != 'ISSUED':
                    existing_certificate.status = 'ISSUED'
                    existing_certificate.issued_date = timezone.now()
                    existing_certificate.save(update_fields=['status', 'issued_date'])
                return
            
            # Get or create default certificate template
            template = CertificateTemplate.objects.filter(
                organization=instance.course.organization
            ).first()
            
            if not template:
                # Create default template
                template = CertificateTemplate.objects.create(
                    name='Default Template',
                    organization=instance.course.organization,
                    header_text='Certificate of Completion',
                    subheader_text='This is to certify that',
                    recipient_text='has successfully completed',
                    course_text='the course',
                    completion_text='with distinction',
                    footer_text='Issued on'
                )
            
            # Generate unique certificate number
            certificate_number = f'CERT-{instance.user.id}-{str(instance.course.id)[:8].upper()}'
            
            # Generate unique verification code
            verification_code = str(uuid.uuid4())[:8].upper()
            
            # Create certificate
            certificate = Certificate.objects.create(
                template=template,
                user=instance.user,
                course=instance.course,
                enrollment=instance,
                certificate_number=certificate_number,
                verification_code=verification_code,
                completion_date=instance.completion_date or timezone.now(),
                issued_date=timezone.now(),
                issued_by=instance.user,  # Self-issued
                status='ISSUED'
            )
            
            # Log certificate creation
            from audit_logs.models import AuditLog
            AuditLog.objects.create(
                user=instance.user,
                action='CERTIFICATE_GENERATED',
                details=f'Certificate automatically generated for course completion: {instance.course.title}'
            )
            
        except Exception as e:
            # Log error but don't break the enrollment process
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error generating certificate for enrollment {instance.id}: {str(e)}")


@receiver(post_save, sender=Enrollment)
def update_certificate_on_enrollment_change(sender, instance, **kwargs):
    """
    Update certificate status if enrollment status changes
    """
    try:
        # Get existing certificate
        certificate = Certificate.objects.filter(
            user=instance.user,
            course=instance.course,
            enrollment=instance
        ).first()
        
        if certificate:
            # If enrollment is no longer completed, revoke certificate
            if instance.status != 'COMPLETED' and certificate.status == 'ISSUED':
                certificate.status = 'REVOKED'
                certificate.save(update_fields=['status'])
                
                # Log certificate revocation
                from audit_logs.models import AuditLog
                AuditLog.objects.create(
                    user=instance.user,
                    action='CERTIFICATE_REVOKED',
                    details=f'Certificate revoked due to enrollment status change: {instance.status}'
                )
            
            # If enrollment is completed again, reissue certificate
            elif instance.status == 'COMPLETED' and certificate.status == 'REVOKED':
                certificate.status = 'ISSUED'
                certificate.issued_date = timezone.now()
                certificate.save(update_fields=['status', 'issued_date'])
                
                # Log certificate reissuance
                from audit_logs.models import AuditLog
                AuditLog.objects.create(
                    user=instance.user,
                    action='CERTIFICATE_REISSUED',
                    details=f'Certificate reissued for course completion: {instance.course.title}'
                )
                
    except Exception as e:
        # Log error but don't break the enrollment process
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error updating certificate for enrollment {instance.id}: {str(e)}")
