from django.core.management.base import BaseCommand
from django.utils import timezone
from enrollments.models import Enrollment
from certificates.models import Certificate, CertificateTemplate
import uuid


class Command(BaseCommand):
    help = 'Generate certificates for all completed enrollments that don\'t have certificates yet'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be generated without actually creating certificates',
        )
        parser.add_argument(
            '--course-id',
            type=str,
            help='Generate certificates only for a specific course',
        )
        parser.add_argument(
            '--user-id',
            type=str,
            help='Generate certificates only for a specific user',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        course_id = options.get('course_id')
        user_id = options.get('user_id')
        
        # Filter enrollments
        enrollments = Enrollment.objects.filter(status='COMPLETED')
        
        if course_id:
            enrollments = enrollments.filter(course_id=course_id)
            
        if user_id:
            enrollments = enrollments.filter(user_id=user_id)
        
        # Exclude enrollments that already have certificates
        enrollments = enrollments.exclude(
            id__in=Certificate.objects.values_list('enrollment_id', flat=True)
        )
        
        if not enrollments.exists():
            self.stdout.write(self.style.WARNING('No completed enrollments without certificates found.'))
            return
        
        self.stdout.write(f"Found {enrollments.count()} completed enrollments without certificates:")
        
        generated_count = 0
        for enrollment in enrollments:
            self.stdout.write(f"  - {enrollment.user.email} - {enrollment.course.title}")
            
            if not dry_run:
                try:
                    # Get or create default certificate template
                    template = CertificateTemplate.objects.filter(
                        organization=enrollment.course.organization
                    ).first()
                    
                    if not template:
                        # Create default template
                        template = CertificateTemplate.objects.create(
                            name='Default Template',
                            organization=enrollment.course.organization,
                            header_text='Certificate of Completion',
                            subheader_text='This is to certify that',
                            recipient_text='has successfully completed',
                            course_text='the course',
                            completion_text='with distinction',
                            footer_text='Issued on'
                        )
                        self.stdout.write(f"    Created default certificate template for {enrollment.course.organization.name}")
                    
                    # Generate unique certificate number
                    certificate_number = f'CERT-{enrollment.user.id}-{str(enrollment.course.id)[:8].upper()}'
                    
                    # Generate unique verification code
                    verification_code = str(uuid.uuid4())[:8].upper()
                    
                    # Create certificate
                    certificate = Certificate.objects.create(
                        template=template,
                        user=enrollment.user,
                        course=enrollment.course,
                        enrollment=enrollment,
                        certificate_number=certificate_number,
                        verification_code=verification_code,
                        completion_date=enrollment.completion_date or timezone.now(),
                        issued_date=timezone.now(),
                        issued_by=enrollment.user,  # Self-issued
                        status='ISSUED'
                    )
                    
                    generated_count += 1
                    self.stdout.write(self.style.SUCCESS(f"    ✓ Certificate generated: {certificate.certificate_number}"))
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"    ✗ Error generating certificate: {str(e)}"))
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f"\nDry run completed. {enrollments.count()} certificates would be generated."))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nSuccessfully generated {generated_count} certificates."))
