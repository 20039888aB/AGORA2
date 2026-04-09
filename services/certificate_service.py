"""
Certificate Service - Centralized Certificate Business Logic

This service contains all certificate-related business logic that should be used
instead of putting logic directly in models or views.
"""

from django.db import models, transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db.models import Q, Avg, Count, Sum
import uuid

User = get_user_model()


class CertificateService:
    """
    Service layer for Certificate business logic
    """
    
    @staticmethod
    def create_template(data, creator=None):
        """
        Create new certificate template with validation and business logic
        """
        # Validate permissions
        if creator and not creator.is_admin_or_above():
            raise ValidationError("Only admins can create certificate templates")
        
        # Extract and validate required fields
        name = data.get('name')
        organization = data.get('organization')
        
        if not name:
            raise ValidationError("Template name is required")
        if not organization:
            raise ValidationError("Organization is required")
        
        # Check if template already exists in organization
        from certificates.models import CertificateTemplate
        if CertificateTemplate.objects.filter(organization=organization, name=name).exists():
            raise ValidationError("Template with this name already exists in this organization")
        
        # Handle default template
        if data.get('is_default'):
            # Remove default flag from existing templates
            CertificateTemplate.objects.filter(
                organization=organization,
                is_default=True
            ).update(is_default=False)
        
        # Create template
        template = CertificateTemplate.objects.create(
            name=name,
            description=data.get('description', ''),
            organization=organization,
            background_color=data.get('background_color', '#ffffff'),
            text_color=data.get('text_color', '#333333'),
            accent_color=data.get('accent_color', '#007bff'),
            font_family=data.get('font_family', 'Arial'),
            font_size=data.get('font_size', 16),
            layout=data.get('layout', 'MODERN'),
            header_text=data.get('header_text', 'Certificate of Completion'),
            subheader_text=data.get('subheader_text', 'This is to certify that'),
            recipient_text=data.get('recipient_text', 'has successfully completed'),
            course_text=data.get('course_text', 'the course'),
            completion_text=data.get('completion_text', 'with distinction'),
            footer_text=data.get('footer_text', 'Issued on'),
            width=data.get('width', 800),
            height=data.get('height', 600),
            margin_top=data.get('margin_top', 50),
            margin_bottom=data.get('margin_bottom', 50),
            margin_left=data.get('margin_left', 50),
            margin_right=data.get('margin_right', 50),
            is_default=data.get('is_default', False),
            is_active=data.get('is_active', True)
        )
        
        # Log template creation
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=creator,
            action='CERTIFICATE_TEMPLATE_CREATE',
            details={
                'template_id': str(template.id),
                'name': template.name,
                'organization_id': str(organization.id),
                'layout': template.layout
            },
            ip_address=creator.last_login_ip if creator else None
        )
        
        return template
    
    @staticmethod
    def set_default_template(template, set_by=None):
        """
        Set template as default for organization
        """
        # Remove default flag from existing templates
        from certificates.models import CertificateTemplate
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
                'template_id': str(template.id),
                'name': template.name,
                'organization_id': str(template.organization.id)
            },
            ip_address=set_by.last_login_ip if set_by else None
        )
        
        return template
    
    @staticmethod
    def generate_certificate_number(organization):
        """
        Generate unique certificate number
        """
        import random
        import string
        
        while True:
            # Generate certificate number: ORG-YYYY-XXXXX
            year = timezone.now().year
            random_part = ''.join(random.choices(string.digits, k=5))
            certificate_number = f"{organization.name[:3].upper()}-{year}-{random_part}"
            
            from certificates.models import Certificate
            if not Certificate.objects.filter(certificate_number=certificate_number).exists():
                return certificate_number
    
    @staticmethod
    def generate_verification_code():
        """
        Generate unique verification code
        """
        import random
        import string
        
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
            from certificates.models import Certificate
            if not Certificate.objects.filter(verification_code=code).exists():
                return code
    
    @staticmethod
    def create_certificate(enrollment, template=None, issued_by=None):
        """
        Create certificate for enrollment
        """
        # Validate enrollment is completed
        if enrollment.status != 'COMPLETED':
            raise ValidationError("Enrollment must be completed to issue certificate")
        
        # Validate course has certificate enabled
        if not enrollment.course.certificate_enabled:
            raise ValidationError("Course does not support certificates")
        
        # Get template
        if not template:
            from certificates.models import CertificateTemplate
            template = CertificateTemplate.objects.get(
                organization=enrollment.course.organization,
                is_default=True,
                is_active=True
            )
        
        # Check if certificate already exists
        from certificates.models import Certificate
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
            status='DRAFT'
        )
        
        # Issue certificate
        CertificateService.issue_certificate(certificate, issued_by)
        
        return certificate
    
    @staticmethod
    def issue_certificate(certificate, issued_by=None):
        """
        Issue certificate
        """
        if certificate.status != 'DRAFT':
            raise ValidationError("Only draft certificates can be issued")
        
        certificate.status = 'ISSUED'
        certificate.issued_date = timezone.now()
        certificate.issued_by = issued_by
        certificate.save(update_fields=['status', 'issued_date', 'issued_by'])
        
        # Generate PDF
        CertificateService.generate_pdf(certificate)
        
        # Log certificate issuance
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=issued_by,
            action='CERTIFICATE_ISSUE',
            details={
                'certificate_id': str(certificate.id),
                'user_id': str(certificate.user.id),
                'course_id': str(certificate.course.id),
                'certificate_number': certificate.certificate_number
            },
            ip_address=issued_by.last_login_ip if issued_by else None
        )
        
        return certificate
    
    @staticmethod
    def revoke_certificate(certificate, revoked_by=None, reason=''):
        """
        Revoke certificate
        """
        if certificate.status != 'ISSUED':
            raise ValidationError("Only issued certificates can be revoked")
        
        certificate.status = 'REVOKED'
        certificate.save(update_fields=['status'])
        
        # Log certificate revocation
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=revoked_by,
            action='CERTIFICATE_REVOKE',
            details={
                'certificate_id': str(certificate.id),
                'user_id': str(certificate.user.id),
                'course_id': str(certificate.course.id),
                'reason': reason
            },
            ip_address=revoked_by.last_login_ip if revoked_by else None
        )
        
        return certificate
    
    @staticmethod
    def verify_certificate(verification_code, verified_by=None, ip_address=None, user_agent=''):
        """
        Verify certificate by verification code
        """
        from certificates.models import Certificate, CertificateVerification
        
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
    def generate_pdf(certificate):
        """
        Generate PDF certificate
        """
        # This would integrate with a PDF generation library
        # For now, we'll just set a placeholder URL
        certificate.download_url = f"/api/certificates/{certificate.id}/download/"
        certificate.save(update_fields=['download_url'])
    
    @staticmethod
    def create_batch(data, creator=None):
        """
        Create new certificate batch
        """
        # Validate permissions
        if creator and not creator.is_admin_or_above():
            raise ValidationError("Only admins can create certificate batches")
        
        # Extract and validate required fields
        name = data.get('name')
        organization = data.get('organization')
        template = data.get('template')
        course = data.get('course')
        
        if not name:
            raise ValidationError("Batch name is required")
        if not organization:
            raise ValidationError("Organization is required")
        if not template:
            raise ValidationError("Template is required")
        if not course:
            raise ValidationError("Course is required")
        
        # Validate entities belong to same organization
        if template.organization != organization:
            raise ValidationError("Template must belong to same organization")
        if course.organization != organization:
            raise ValidationError("Course must belong to same organization")
        
        # Create batch
        from certificates.models import CertificateBatch
        batch = CertificateBatch.objects.create(
            name=name,
            description=data.get('description', ''),
            organization=organization,
            template=template,
            course=course,
            created_by=creator
        )
        
        # Log batch creation
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=creator,
            action='CERTIFICATE_BATCH_CREATE',
            details={
                'batch_id': str(batch.id),
                'name': batch.name,
                'organization_id': str(organization.id),
                'course_id': str(course.id)
            },
            ip_address=creator.last_login_ip if creator else None
        )
        
        return batch
    
    @staticmethod
    def process_batch(batch, processed_by=None):
        """
        Process certificate batch
        """
        if batch.status != 'PENDING':
            raise ValidationError("Only pending batches can be processed")
        
        batch.status = 'PROCESSING'
        batch.processing_started_at = timezone.now()
        batch.save(update_fields=['status', 'processing_started_at'])
        
        try:
            # Get completed enrollments for course
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
            
            batch.status = 'COMPLETED'
            batch.processing_completed_at = timezone.now()
            batch.save(update_fields=['status', 'processing_completed_at'])
            
        except Exception as e:
            batch.status = 'FAILED'
            batch.error_message = str(e)
            batch.save(update_fields=['status', 'error_message'])
            raise
        
        return batch
    
    @staticmethod
    def get_certificate_statistics(organization=None):
        """
        Get certificate statistics
        """
        from certificates.models import Certificate
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
    def get_template_statistics(template):
        """
        Get template statistics
        """
        from certificates.models import Certificate
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
    
    @staticmethod
    def get_batch_statistics(batch):
        """
        Get batch statistics
        """
        return {
            'total_certificates': batch.total_certificates,
            'processed_certificates': batch.processed_certificates,
            'failed_certificates': batch.failed_certificates,
            'success_rate': (batch.processed_certificates / batch.total_certificates * 100) if batch.total_certificates > 0 else 0,
            'progress_percentage': batch.progress_percentage,
            'processing_duration': batch.processing_completed_at - batch.processing_started_at if batch.processing_completed_at and batch.processing_started_at else None,
        }
    
    @staticmethod
    def get_user_certificates(user, status=None):
        """
        Get user's certificates
        """
        from certificates.models import Certificate
        certificates = Certificate.objects.filter(user=user)
        
        if status:
            certificates = certificates.filter(status=status)
        
        return certificates
    
    @staticmethod
    def get_course_certificates(course, status=None):
        """
        Get course certificates
        """
        from certificates.models import Certificate
        certificates = Certificate.objects.filter(course=course)
        
        if status:
            certificates = certificates.filter(status=status)
        
        return certificates
    
    @staticmethod
    def get_organization_certificates(organization, status=None):
        """
        Get organization certificates
        """
        from certificates.models import Certificate
        certificates = Certificate.objects.filter(template__organization=organization)
        
        if status:
            certificates = certificates.filter(status=status)
        
        return certificates
    
    @staticmethod
    def validate_certificate_access(user, certificate, action='view'):
        """
        Validate if user has access to certificate
        """
        if user.is_superadmin():
            return True
        
        if certificate.template.organization != user.organization:
            return False
        
        if action == 'view':
            return True
        
        if action in ['edit', 'delete', 'revoke']:
            return user.is_admin_or_above()
        
        if action == 'download':
            return certificate.user == user or user.is_admin_or_above()
        
        return False
    
    @staticmethod
    def get_recent_certificates(organization=None, limit=10):
        """
        Get recent certificates
        """
        from certificates.models import Certificate
        certificates = Certificate.objects.filter(status='ISSUED')
        
        if organization:
            certificates = certificates.filter(template__organization=organization)
        
        return certificates.order_by('-issued_date')[:limit]
    
    @staticmethod
    def search_certificates(query, organization=None):
        """
        Search certificates by recipient name, course name, or certificate number
        """
        from certificates.models import Certificate
        certificates = Certificate.objects.all()
        
        if organization:
            certificates = certificates.filter(template__organization=organization)
        
        if query:
            certificates = certificates.filter(
                Q(recipient_name__icontains=query) |
                Q(course_name__icontains=query) |
                Q(certificate_number__icontains=query)
            )
        
        return certificates.distinct()
