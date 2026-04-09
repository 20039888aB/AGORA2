from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg, Sum

from .models import CertificateTemplate, Certificate, CertificateVerification, CertificateBatch
from .serializers import (
    CertificateTemplateSerializer, CertificateTemplateCreateSerializer, CertificateTemplateStatisticsSerializer,
    CertificateSerializer, CertificateCreateSerializer, CertificateIssueSerializer, CertificateRevokeSerializer,
    CertificateVerificationSerializer, CertificateVerifySerializer, CertificateStatisticsSerializer,
    CertificateBatchSerializer, CertificateBatchCreateSerializer, CertificateBatchProcessSerializer, CertificateBatchStatisticsSerializer
)
from .permissions import (
    IsTemplateOwner, CanManageTemplate, IsCertificateOwner, CanManageCertificate, CanViewCertificate,
    CanVerifyCertificate, IsBatchOwner, CanManageBatch, CanViewBatch, CanViewCertificateStatistics,
    CanIssueCertificate, CanCreateBatch
)
from .services import (
    CertificateTemplateService, CertificateService, CertificateBatchService
)


class CertificateTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CertificateTemplate model
    """
    queryset = CertificateTemplate.objects.filter(is_active=True)
    serializer_class = CertificateTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['organization', 'layout', 'is_default', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['organization', 'name', 'created_at']
    ordering = ['organization', 'name']
    
    def get_queryset(self):
        """Filter templates based on user role"""
        user = self.request.user
        
        if user.is_superadmin():
            return self.queryset
        
        elif user.is_admin():
            return self.queryset.filter(organization=user.organization)
        
        return self.queryset.none()
    
    def get_permissions(self):
        """Return permissions based on action"""
        if self.action == 'create':
            permission_classes = [CanManageTemplate]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [CanManageTemplate]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=False, methods=['post'], permission_classes=[CanManageTemplate])
    def create_template(self, request):
        """Create new certificate template"""
        serializer = CertificateTemplateCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            from organizations.models import Organization
            organization = Organization.objects.get(id=serializer.validated_data['organization_id'])
            
            template_data = {
                'name': serializer.validated_data['name'],
                'description': serializer.validated_data.get('description', ''),
                'organization': organization,
                'background_color': serializer.validated_data['background_color'],
                'text_color': serializer.validated_data['text_color'],
                'accent_color': serializer.validated_data['accent_color'],
                'font_family': serializer.validated_data['font_family'],
                'font_size': serializer.validated_data['font_size'],
                'layout': serializer.validated_data['layout'],
                'header_text': serializer.validated_data['header_text'],
                'subheader_text': serializer.validated_data['subheader_text'],
                'recipient_text': serializer.validated_data['recipient_text'],
                'course_text': serializer.validated_data['course_text'],
                'completion_text': serializer.validated_data['completion_text'],
                'footer_text': serializer.validated_data['footer_text'],
                'width': serializer.validated_data['width'],
                'height': serializer.validated_data['height'],
                'margin_top': serializer.validated_data['margin_top'],
                'margin_bottom': serializer.validated_data['margin_bottom'],
                'margin_left': serializer.validated_data['margin_left'],
                'margin_right': serializer.validated_data['margin_right'],
                'is_default': serializer.validated_data['is_default'],
            }
            
            template = CertificateTemplateService.create_template(template_data, request.user)
            
            return Response({
                'message': 'Template created successfully',
                'template': CertificateTemplateSerializer(template).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageTemplate])
    def set_default(self, request, pk=None):
        """Set template as default"""
        template = self.get_object()
        
        try:
            CertificateTemplateService.set_default_template(template, request.user)
            return Response({
                'message': 'Template set as default successfully',
                'template': CertificateTemplateSerializer(template).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'], permission_classes=[CanViewCertificateStatistics])
    def statistics(self, request, pk=None):
        """Get template statistics"""
        template = self.get_object()
        stats = CertificateTemplateService.get_template_statistics(template)
        
        return Response(stats)


class CertificateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Certificate model
    """
    queryset = Certificate.objects.all()
    serializer_class = CertificateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['template', 'user', 'course', 'status']
    search_fields = ['certificate_number', 'recipient_name', 'course_name']
    ordering_fields = ['issued_date', 'completion_date', 'created_at']
    ordering = ['-issued_date']
    
    def get_queryset(self):
        """Filter certificates based on user role"""
        user = self.request.user
        
        if user.is_superadmin():
            return self.queryset
        
        elif user.is_admin():
            return self.queryset.filter(template__organization=user.organization)
        
        elif user.is_student():
            return self.queryset.filter(user=user)
        
        return self.queryset.none()
    
    def get_permissions(self):
        """Return permissions based on action"""
        if self.action == 'create':
            permission_classes = [CanIssueCertificate]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [CanManageCertificate]
        elif self.action == 'retrieve':
            permission_classes = [CanViewCertificate]
        elif self.action == 'destroy':
            permission_classes = [CanManageCertificate]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=False, methods=['post'], permission_classes=[CanIssueCertificate])
    def create_certificate(self, request):
        """Create new certificate"""
        serializer = CertificateCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            from enrollments.models import Enrollment
            enrollment = Enrollment.objects.get(id=serializer.validated_data['enrollment_id'])
            
            template = None
            if serializer.validated_data.get('template_id'):
                template = CertificateTemplate.objects.get(id=serializer.validated_data['template_id'])
            
            certificate = CertificateService.create_certificate(
                enrollment=enrollment,
                template=template,
                issued_by=request.user
            )
            
            return Response({
                'message': 'Certificate created successfully',
                'certificate': CertificateSerializer(certificate).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageCertificate])
    def issue(self, request, pk=None):
        """Issue certificate"""
        certificate = self.get_object()
        
        try:
            CertificateService.issue_certificate(certificate, request.user)
            return Response({
                'message': 'Certificate issued successfully',
                'certificate': CertificateSerializer(certificate).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageCertificate])
    def revoke(self, request, pk=None):
        """Revoke certificate"""
        certificate = self.get_object()
        serializer = CertificateRevokeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            CertificateService.revoke_certificate(
                certificate, 
                request.user, 
                serializer.validated_data.get('reason', '')
            )
            return Response({
                'message': 'Certificate revoked successfully',
                'certificate': CertificateSerializer(certificate).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'], permission_classes=[permissions.AllowAny])
    def download(self, request, pk=None):
        """Download certificate PDF"""
        certificate = self.get_object()
        
        if not certificate.is_valid:
            return Response(
                {'error': 'Certificate is not valid'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # For now, return a placeholder response
        return Response({
            'message': 'Certificate download URL',
            'download_url': certificate.download_url,
            'certificate_number': certificate.certificate_number,
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsCertificateOwner])
    def my_certificates(self, request):
        """Get current user's certificates"""
        user = request.user
        certificates = CertificateService.get_user_certificates(user)
        
        return Response({
            'count': certificates.count(),
            'results': CertificateSerializer(certificates, many=True).data
        })
    
    @action(detail=False, methods=['get'], permission_classes=[CanViewCertificateStatistics])
    def statistics(self, request):
        """Get certificate statistics"""
        organization_id = request.query_params.get('organization_id')
        
        if organization_id:
            from organizations.models import Organization
            organization = Organization.objects.get(id=organization_id)
            stats = CertificateService.get_certificate_statistics(organization)
        else:
            stats = CertificateService.get_certificate_statistics()
        
        return Response(stats)


class CertificateVerificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CertificateVerification model
    """
    queryset = CertificateVerification.objects.all()
    serializer_class = CertificateVerificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['certificate', 'is_valid']
    search_fields = ['verification_code']
    ordering_fields = ['-verified_at']
    ordering = ['-verified_at']
    
    def get_queryset(self):
        """Filter verifications based on user role"""
        user = self.request.user
        
        if user.is_superadmin():
            return self.queryset
        
        elif user.is_admin():
            return self.queryset.filter(
                certificate__template__organization=user.organization
            )
        
        return self.queryset.none()
    
    @action(detail=False, methods=['post'], permission_classes=[CanVerifyCertificate])
    def verify(self, request):
        """Verify certificate by verification code"""
        serializer = CertificateVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        result = CertificateService.verify_certificate(
            serializer.validated_data['verification_code'],
            verified_by=request.user if request.user.is_authenticated else None,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        if result['valid']:
            return Response({
                'valid': True,
                'certificate': CertificateSerializer(result['certificate']).data,
                'verification': CertificateVerificationSerializer(result['verification']).data,
                'is_expired': result['is_expired']
            })
        else:
            return Response({
                'valid': False,
                'error': result.get('error', 'Certificate not found'),
                'verification': CertificateVerificationSerializer(result['verification']).data
            })


class CertificateBatchViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CertificateBatch model
    """
    queryset = CertificateBatch.objects.all()
    serializer_class = CertificateBatchSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['organization', 'template', 'course', 'status']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'processing_started_at', 'processing_completed_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter batches based on user role"""
        user = self.request.user
        
        if user.is_superadmin():
            return self.queryset
        
        elif user.is_admin():
            return self.queryset.filter(organization=user.organization)
        
        return self.queryset.none()
    
    def get_permissions(self):
        """Return permissions based on action"""
        if self.action == 'create':
            permission_classes = [CanCreateBatch]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [CanManageBatch]
        elif self.action == 'retrieve':
            permission_classes = [CanViewBatch]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=False, methods=['post'], permission_classes=[CanCreateBatch])
    def create_batch(self, request):
        """Create new certificate batch"""
        serializer = CertificateBatchCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            from organizations.models import Organization
            from certificates.models import CertificateTemplate
            from courses.models import Course
            
            organization = Organization.objects.get(id=serializer.validated_data['organization_id'])
            template = CertificateTemplate.objects.get(id=serializer.validated_data['template_id'])
            course = Course.objects.get(id=serializer.validated_data['course_id'])
            
            batch_data = {
                'name': serializer.validated_data['name'],
                'description': serializer.validated_data.get('description', ''),
                'organization': organization,
                'template': template,
                'course': course,
                'created_by': request.user,
            }
            
            batch = CertificateBatchService.create_batch(batch_data, request.user)
            
            return Response({
                'message': 'Batch created successfully',
                'batch': CertificateBatchSerializer(batch).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageBatch])
    def process(self, request, pk=None):
        """Process certificate batch"""
        batch = self.get_object()
        
        try:
            CertificateBatchService.process_batch(batch, request.user)
            return Response({
                'message': 'Batch processed successfully',
                'batch': CertificateBatchSerializer(batch).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'], permission_classes=[CanViewBatch])
    def statistics(self, request, pk=None):
        """Get batch statistics"""
        batch = self.get_object()
        stats = CertificateBatchService.get_batch_statistics(batch)
        
        return Response(stats)


class CertificatePublicViewSet(viewsets.ViewSet):
    """
    Public ViewSet for certificate verification (no authentication required)
    """
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def verify_public(self, request):
        """Public certificate verification endpoint"""
        serializer = CertificateVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        result = CertificateService.verify_certificate(
            serializer.validated_data['verification_code'],
            verified_by=None,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        if result['valid']:
            return Response({
                'valid': True,
                'certificate': {
                    'certificate_number': result['certificate'].certificate_number,
                    'recipient_name': result['certificate'].recipient_name,
                    'course_name': result['certificate'].course_name,
                    'issued_date': result['certificate'].issued_date,
                    'is_expired': result['is_expired'],
                },
                'is_expired': result['is_expired'],
            })
        else:
            return Response({
                'valid': False,
                'error': result.get('error', 'Certificate not found')
            })


# Certificate view for completed courses
from django.contrib.auth.decorators import login_required

@login_required
def course_certificate(request, course_id):
    """
    Display and allow download of course certificate
    """
    from django.shortcuts import render, redirect, get_object_or_404
    from django.contrib import messages
    from courses.models import Course
    from enrollments.models import Enrollment
    from django.http import HttpResponse
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.colors import HexColor, white, black
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from io import BytesIO
    from django.utils import timezone
    
    user = request.user
    
    try:
        course = get_object_or_404(Course, id=course_id)
        enrollment = get_object_or_404(Enrollment, user=user, course=course, status='COMPLETED')
        certificate = get_object_or_404(Certificate, user=user, course=course)
        
        if request.GET.get('download') == 'pdf':
            return generate_certificate_pdf(user, course, enrollment, certificate)
        
        context = {
            'user': user,
            'course': course,
            'enrollment': enrollment,
            'certificate': certificate,
            'page_title': 'Course Certificate',
        }
        
        return render(request, 'courses/certificate_download.html', context)
        
    except ImportError:
        messages.error(request, 'Certificate system not available.')
        return redirect('dashboard')
    except Exception as e:
        messages.error(request, f'Error loading certificate: {str(e)}')
        return redirect('dashboard')


def generate_certificate_pdf(user, course, enrollment, certificate):
    """
    Generate PDF certificate using ReportLab
    """
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.colors import HexColor, white, black
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from io import BytesIO
    from django.http import HttpResponse
    
    # Create PDF buffer
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # Certificate content
    story = []
    
    # Title
    title_style = styles['Title']
    title_style.textColor = HexColor('#2d3748')
    title_style.alignment = 1  # Center
    
    story.append(Paragraph("CERTIFICATE OF COMPLETION", title_style))
    story.append(Spacer(1, 20))
    
    # Subtitle
    subtitle_style = styles['Heading2']
    subtitle_style.textColor = HexColor('#64748b')
    subtitle_style.alignment = 1
    
    story.append(Paragraph("This is to certify that", subtitle_style))
    story.append(Spacer(1, 12))
    
    # Student name
    name_style = styles['Heading1']
    name_style.textColor = HexColor('#1a202c')
    name_style.alignment = 1
    
    story.append(Paragraph(user.get_full_name() or user.email, name_style))
    story.append(Spacer(1, 20))
    
    # Course name
    course_style = styles['Heading2']
    course_style.textColor = HexColor('#2d3748')
    course_style.alignment = 1
    
    story.append(Paragraph("has successfully completed the course", course_style))
    story.append(Spacer(1, 12))
    story.append(Paragraph(course.title, course_style))
    story.append(Spacer(1, 20))
    
    # Course details
    normal_style = styles['Normal']
    normal_style.textColor = HexColor('#64748b')
    
    details = [
        f"Duration: {course.duration_hours} hours",
        f"Difficulty: {course.difficulty or 'Beginner'}",
        f"Completion Date: {enrollment.completion_date.strftime('%B %d, %Y')}",
        f"Certificate ID: {certificate.certificate_number}"
    ]
    
    for detail in details:
        story.append(Paragraph(detail, normal_style))
        story.append(Spacer(1, 8))
    
    # Verification code
    story.append(Spacer(1, 20))
    story.append(Paragraph("Verification Code:", normal_style))
    story.append(Spacer(1, 8))
    
    code_style = styles['Code']
    code_style.textColor = HexColor('#667eea')
    code_style.alignment = 1
    code_style.fontSize = 14
    
    story.append(Paragraph(certificate.verification_code, code_style))
    
    # Build PDF
    doc.build(story)
    
    # Create response
    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Certificate_{course.title}_{user.get_full_name() or user.email}.pdf"'
    response['Cache-Control'] = 'no-cache'
    
    return response
