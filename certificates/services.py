from django.db import models, transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import CertificateTemplate, Certificate, CertificateVerification, CertificateBatch


class CertificateTemplateService:
    """
    Service layer for Certificate Template business logic
    """
    
    @staticmethod
    def create_template(data, creator=None):
        """Create new certificate template"""
        # Validate permissions
        if creator and not creator.is_admin_or_above():
            raise ValidationError("Only admins can create certificate templates")
        
        # Validate organization
        if not data.get('organization'):
            raise ValidationError("Organization is required")
        
        # Handle default template
        if data.get('is_default'):
            # Remove default flag from existing templates
            CertificateTemplate.objects.filter(
                organization=data['organization'],
                is_default=True
            ).update(is_default=False)
        
        template = CertificateTemplate.objects.create(**data)
        
        # Log template creation
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=creator,
            action='CERTIFICATE_TEMPLATE_CREATE',
            details={
                'template': str(template.id),
                'name': template.name,
                'organization': str(template.organization.id),
            },
            ip_address=creator.last_login_ip
        )
        
        return template
    
    @staticmethod
    def set_default_template(template, set_by=None):
        """Set template as default"""
        # Remove default flag from existing templates
        CertificateTemplate.objects.filter(
            organization=template.organization,
            is_default=True
        ).update(is_default=False)
        
        # Set new default
        template.is_default = True
        template.save(update_fields=['is_default'])
        
        # Log default change
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=set_by,
            action='CERTIFICATE_TEMPLATE_SET_DEFAULT',
            details={
                'template': str(template.id),
                'name': template.name,
                'organization': str(template.organization.id),
            },
            ip_address=set_by.last_login_ip
        )
    
    @staticmethod
    def get_template_statistics(template):
        """Get template statistics"""
        certificates = template.certificates.all()
        
        return {
            'total_certificates': certificates.count(),
            'issued_certificates': certificates.filter(status='ISSUED').count(),
            'revoked_certificates': certificates.filter(status='REVOKED').count(),
            'expired_certificates': certificates.filter(status='EXPIRED').count(),
            'valid_certificates': certificates.filter(status='ISSUED').filter(
                models.Q(expiry_date__gt=timezone.now()) | models.Q(expiry_date__isnull=True)
            ).count(),
        }


class CertificateService:
    """
    Service layer for Certificate business logic
    """
    
    @staticmethod
    def generate_certificate_number(organization):
        """Generate unique certificate number"""
        import random
        import string
        
        while True:
            # Generate certificate number: ORG-YYYY-XXXXX
            year = timezone.now().year
            random_part = ''.join(random.choices(string.digits, k=5))
            certificate_number = f"{organization.name[:3].upper()}-{year}-{random_part}"
            
            if not Certificate.objects.filter(certificate_number=certificate_number).exists():
                return certificate_number
    
    @staticmethod
    def generate_verification_code():
        """Generate unique verification code"""
        import random
        import string
        
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
            if not Certificate.objects.filter(verification_code=code).exists():
                return code
    
    @staticmethod
    def create_certificate(enrollment, template=None, issued_by=None):
        """Create certificate for enrollment"""
        # Validate enrollment is completed
        if enrollment.status != 'COMPLETED':
            raise ValidationError("Enrollment must be completed to issue certificate")
        
        # Validate course has certificate enabled
        if not enrollment.course.certificate_enabled:
            raise ValidationError("Course does not support certificates")
        
        # Get template
        if not template:
            template = CertificateTemplate.objects.get(
                organization=enrollment.course.organization,
                is_default=True,
                is_active=True
            )
        
        # Check if certificate already exists
        if Certificate.objects.filter(enrollment=enrollment, status='ISSUED').exists():
            raise ValidationError("Certificate already issued for this enrollment")
        
        # Create certificate
        certificate = Certificate.objects.create(
            template=template,
            user=enrollment.user,
            course=enrollment.course,
            enrollment=enrollment,
            certificate_number=CertificateService.generate_certificate_number(enrollment.course.organization),
            verification_code=CertificateService.generate_verification_code(),
            score=enrollment.progress_percentage,
            completion_date=enrollment.completion_date,
            issued_date=timezone.now(),
            issued_by=issued_by,
            recipient_name=enrollment.user.full_name,
            course_name=enrollment.course.title,
        )
        
        # Issue certificate
        certificate.issue(issued_by)
        
        return certificate
    
    @staticmethod
    def issue_certificate(certificate, issued_by=None):
        """Issue certificate"""
        certificate.issue(issued_by)
        return certificate
    
    @staticmethod
    def revoke_certificate(certificate, revoked_by=None, reason=''):
        """Revoke certificate"""
        certificate.revoke(revoked_by, reason)
        return certificate
    
    @staticmethod
    def verify_certificate(verification_code, verified_by=None, ip_address=None, user_agent=''):
        """Verify certificate by verification code"""
        try:
            certificate = Certificate.objects.get(verification_code=verification_code)
            
            # Create verification record
            verification = CertificateVerification.objects.create(
                certificate=certificate,
                verification_code=verification_code,
                verified_by=verified_by,
                ip_address=ip_address,
                user_agent=user_agent,
                is_valid=certificate.is_valid
            )
            
            return {
                'valid': certificate.is_valid,
                'certificate': certificate,
                'verification': verification,
                'is_expired': certificate.is_expired,
            }
        except Certificate.DoesNotExist:
            # Create verification record for invalid code
            verification = CertificateVerification.objects.create(
                certificate=None,
                verification_code=verification_code,
                verified_by=verified_by,
                ip_address=ip_address,
                user_agent=user_agent,
                is_valid=False
            )
            
            return {
                'valid': False,
                'error': 'Certificate not found',
                'verification': verification,
            }
    
    @staticmethod
    def get_certificate_statistics(organization=None):
        """Get certificate statistics"""
        certificates = Certificate.objects.all()
        
        if organization:
            certificates = certificates.filter(template__organization=organization)
        
        return {
            'total_certificates': certificates.count(),
            'issued_certificates': certificates.filter(status='ISSUED').count(),
            'revoked_certificates': certificates.filter(status='REVOKED').count(),
            'expired_certificates': certificates.filter(status='EXPIRED').count(),
            'valid_certificates': certificates.filter(status='ISSUED').filter(
                models.Q(expiry_date__gt=timezone.now()) | models.Q(expiry_date__isnull=True)
            ).count(),
            'certificates_this_month': certificates.filter(
                issued_date__gte=timezone.now() - timezone.timedelta(days=30)
            ).count(),
            'certificates_this_year': certificates.filter(
                issued_date__gte=timezone.now() - timezone.timedelta(days=365)
            ).count(),
        }
    
    @staticmethod
    def get_user_certificates(user):
        """Get user's certificates"""
        return Certificate.objects.filter(user=user, status='ISSUED')
    
    @staticmethod
    def get_course_certificates(course):
        """Get course certificates"""
        return Certificate.objects.filter(course=course, status='ISSUED')


class CertificateBatchService:
    """
    Service layer for Certificate Batch business logic
    """
    
    @staticmethod
    def create_batch(data, creator=None):
        """Create new certificate batch"""
        # Validate permissions
        if creator and not creator.is_admin_or_above():
            raise ValidationError("Only admins can create certificate batches")
        
        # Validate organization
        if not data.get('organization'):
            raise ValidationError("Organization is required")
        
        batch = CertificateBatch.objects.create(**data)
        
        # Log batch creation
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=creator,
            action='CERTIFICATE_BATCH_CREATE',
            details={
                'batch': str(batch.id),
                'name': batch.name,
                'organization': str(batch.organization.id),
                'course': str(batch.course.id),
            },
            ip_address=creator.last_login_ip
        )
        
        return batch
    
    @staticmethod
    def process_batch(batch, processed_by=None):
        """Process certificate batch"""
        if batch.status != 'PENDING':
            raise ValidationError("Only pending batches can be processed")
        
        batch.start_processing(processed_by)
        
        try:
            # Get completed enrollments for the course
            from enrollments.models import Enrollment
            completed_enrollments = Enrollment.objects.filter(
                course=batch.course,
                status='COMPLETED'
            ).exclude(
                certificates__status='ISSUED'
            )
            
            batch.total_certificates = completed_enrollments.count()
            batch.save(update_fields=['total_certificates'])
            
            # Process each enrollment
            for enrollment in completed_enrollments:
                try:
                    certificate = CertificateService.create_certificate(
                        enrollment=enrollment,
                        template=batch.template,
                        issued_by=processed_by
                    )
                    batch.processed_certificates += 1
                    batch.save(update_fields=['processed_certificates'])
                except Exception as e:
                    batch.failed_certificates += 1
                    batch.save(update_fields=['failed_certificates'])
            
            batch.complete_processing(processed_by)
            
        except Exception as e:
            batch.fail_processing(str(e), processed_by)
            raise
        
        return batch
    
    @staticmethod
    def get_batch_statistics(batch):
        """Get batch statistics"""
        return {
            'total_certificates': batch.total_certificates,
            'processed_certificates': batch.processed_certificates,
            'failed_certificates': batch.failed_certificates,
            'success_rate': (batch.processed_certificates / batch.total_certificates * 100) if batch.total_certificates > 0 else 0,
            'progress_percentage': batch.progress_percentage,
            'processing_duration': batch.processing_completed_at - batch.processing_started_at if batch.processing_completed_at and batch.processing_started_at else None,
        }
    
    @staticmethod
    def get_organization_batches(organization):
        """Get organization's certificate batches"""
        return CertificateBatch.objects.filter(organization=organization)
