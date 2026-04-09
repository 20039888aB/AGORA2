from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg, Sum

from .models import Enrollment, LessonProgress, EnrollmentCertificate
from .serializers import (
    EnrollmentSerializer, EnrollmentCreateSerializer, EnrollmentUpdateSerializer,
    LessonProgressSerializer, LessonProgressUpdateSerializer,
    EnrollmentCertificateSerializer, CertificateVerifySerializer, CertificateRevokeSerializer,
    EnrollmentStatisticsSerializer, LessonProgressStatisticsSerializer, CertificateStatisticsSerializer
)
from .permissions import (
    IsEnrollmentOwner, CanManageEnrollment, CanViewEnrollment,
    IsLessonProgressOwner, CanManageLessonProgress, CanEnrollInCourse,
    CanViewEnrollmentStatistics, CanManageCertificates, IsCertificateOwner
)
from .services import EnrollmentService, LessonProgressService, CertificateService


class EnrollmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Enrollment model
    """
    queryset = Enrollment.objects.filter(is_active=True)
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user', 'course', 'status', 'payment_status']
    search_fields = ['user__email', 'course__title']
    ordering_fields = ['enrollment_date', 'progress_percentage', 'created_at']
    ordering = ['-enrollment_date']
    
    def get_queryset(self):
        """Filter enrollments based on user role"""
        user = self.request.user
        
        if user.is_superadmin():
            return self.queryset
        
        elif user.is_admin():
            return self.queryset.filter(course__organization=user.organization)
        
        elif user.is_manager():
            return self.queryset.filter(
                course__instructor=user
            )
        
        elif user.is_student():
            return self.queryset.filter(user=user)
        
        return self.queryset.none()
    
    def get_permissions(self):
        """Return permissions based on action"""
        if self.action == 'create':
            permission_classes = [CanEnrollInCourse]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [CanManageEnrollment]
        elif self.action == 'retrieve':
            permission_classes = [CanViewEnrollment]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=False, methods=['post'], permission_classes=[CanEnrollInCourse])
    def create_enrollment(self, request):
        """Create new enrollment"""
        serializer = EnrollmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            from courses.models import Course
            course = Course.objects.get(id=serializer.validated_data['course_id'])
            
            enrollment = EnrollmentService.create_enrollment(
                user=request.user,
                course=course,
                payment_status=serializer.validated_data['payment_status'],
                payment_amount=serializer.validated_data['payment_amount'],
                enrolled_by=request.user
            )
            
            return Response({
                'message': 'Enrollment created successfully',
                'enrollment': EnrollmentSerializer(enrollment).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageEnrollment])
    def activate(self, request, pk=None):
        """Activate enrollment"""
        enrollment = self.get_object()
        
        try:
            EnrollmentService.activate_enrollment(enrollment, request.user)
            return Response({
                'message': 'Enrollment activated successfully',
                'enrollment': EnrollmentSerializer(enrollment).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageEnrollment])
    def suspend(self, request, pk=None):
        """Suspend enrollment"""
        enrollment = self.get_object()
        reason = request.data.get('reason', '')
        
        try:
            EnrollmentService.suspend_enrollment(enrollment, request.user, reason)
            return Response({
                'message': 'Enrollment suspended successfully',
                'enrollment': EnrollmentSerializer(enrollment).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageEnrollment])
    def complete(self, request, pk=None):
        """Complete enrollment"""
        enrollment = self.get_object()
        
        try:
            EnrollmentService.complete_enrollment(enrollment, request.user)
            return Response({
                'message': 'Enrollment completed successfully',
                'enrollment': EnrollmentSerializer(enrollment).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageEnrollment])
    def update_progress(self, request, pk=None):
        """Update enrollment progress"""
        enrollment = self.get_object()
        progress_percentage = request.data.get('progress_percentage')
        
        if progress_percentage is None:
            return Response(
                {'error': 'Progress percentage is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            EnrollmentService.update_progress(enrollment, float(progress_percentage), request.user)
            return Response({
                'message': 'Progress updated successfully',
                'enrollment': EnrollmentSerializer(enrollment).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageEnrollment])
    def issue_certificate(self, request, pk=None):
        """Issue certificate for enrollment"""
        enrollment = self.get_object()
        
        try:
            certificate = EnrollmentService.issue_certificate(enrollment, request.user)
            return Response({
                'message': 'Certificate issued successfully',
                'certificate': EnrollmentCertificateSerializer(
                    enrollment.certificate
                ).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'], permission_classes=[CanViewEnrollment])
    def statistics(self, request, pk=None):
        """Get enrollment statistics"""
        enrollment = self.get_object()
        stats = EnrollmentService.get_enrollment_statistics(enrollment)
        
        return Response(stats)
    
    @action(detail=False, methods=['get'], permission_classes=[CanViewEnrollmentStatistics])
    def my_enrollments(self, request):
        """Get current user's enrollments"""
        user = request.user
        enrollments = self.get_queryset().filter(user=user)
        
        return Response({
            'count': enrollments.count(),
            'results': EnrollmentSerializer(enrollments, many=True).data
        })
    
    @action(detail=False, methods=['get'], permission_classes=[CanViewEnrollmentStatistics])
    def user_statistics(self, request):
        """Get user enrollment statistics"""
        user = request.user
        stats = EnrollmentService.get_user_enrollment_statistics(user)
        
        return Response(stats)
    
    @action(detail=False, methods=['get'], permission_classes=[CanViewEnrollmentStatistics])
    def course_statistics(self, request):
        """Get course enrollment statistics"""
        course_id = request.query_params.get('course_id')
        
        if not course_id:
            return Response(
                {'error': 'Course ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from courses.models import Course
            course = Course.objects.get(id=course_id)
            stats = EnrollmentService.get_course_enrollment_statistics(course)
            
            return Response(stats)
        except Course.DoesNotExist:
            return Response(
                {'error': 'Course not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class LessonProgressViewSet(viewsets.ModelViewSet):
    """
    ViewSet for LessonProgress model
    """
    queryset = LessonProgress.objects.all()
    serializer_class = LessonProgressSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['enrollment', 'lesson', 'status']
    search_fields = ['lesson__title']
    ordering_fields = ['progress_percentage', 'last_accessed_at', 'created_at']
    ordering = ['enrollment', 'lesson']
    
    def get_queryset(self):
        """Filter lesson progress based on user role"""
        user = self.request.user
        
        if user.is_superadmin():
            return self.queryset
        
        elif user.is_admin():
            return self.queryset.filter(
                enrollment__course__organization=user.organization
            )
        
        elif user.is_manager():
            return self.queryset.filter(
                enrollment__course__instructor=user
            )
        
        elif user.is_student():
            return self.queryset.filter(enrollment__user=user)
        
        return self.queryset.none()
    
    def get_permissions(self):
        """Return permissions based on action"""
        if self.action in ['update', 'partial_update']:
            permission_classes = [CanManageLessonProgress]
        elif self.action == 'retrieve':
            permission_classes = [IsLessonProgressOwner]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageLessonProgress])
    def update_progress(self, request, pk=None):
        """Update lesson progress"""
        lesson_progress = self.get_object()
        serializer = LessonProgressUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            LessonProgressService.update_lesson_progress(
                lesson_progress,
                float(serializer.validated_data['progress_percentage']),
                serializer.validated_data.get('time_spent'),
                request.user
            )
            
            return Response({
                'message': 'Lesson progress updated successfully',
                'lesson_progress': LessonProgressSerializer(lesson_progress).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageLessonProgress])
    def complete(self, request, pk=None):
        """Complete lesson"""
        lesson_progress = self.get_object()
        
        try:
            LessonProgressService.complete_lesson(lesson_progress, request.user)
            return Response({
                'message': 'Lesson completed successfully',
                'lesson_progress': LessonProgressSerializer(lesson_progress).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def lesson_statistics(self, request):
        """Get lesson statistics"""
        lesson_id = request.query_params.get('lesson_id')
        
        if not lesson_id:
            return Response(
                {'error': 'Lesson ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from courses.models import Lesson
            lesson = Lesson.objects.get(id=lesson_id)
            stats = LessonProgressService.get_lesson_statistics(lesson)
            
            return Response(stats)
        except Lesson.DoesNotExist:
            return Response(
                {'error': 'Lesson not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class EnrollmentCertificateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for EnrollmentCertificate model
    """
    queryset = EnrollmentCertificate.objects.all()
    serializer_class = EnrollmentCertificateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['enrollment', 'certificate', 'is_revoked']
    search_fields = ['verification_code']
    ordering_fields = ['issued_date', 'expiry_date']
    ordering = ['-issued_date']
    
    def get_queryset(self):
        """Filter certificates based on user role"""
        user = self.request.user
        
        if user.is_superadmin():
            return self.queryset
        
        elif user.is_admin():
            return self.queryset.filter(
                enrollment__course__organization=user.organization
            )
        
        elif user.is_student():
            return self.queryset.filter(enrollment__user=user)
        
        return self.queryset.none()
    
    def get_permissions(self):
        """Return permissions based on action"""
        if self.action == 'retrieve':
            permission_classes = [IsCertificateOwner]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [CanManageCertificates]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def verify(self, request):
        """Verify certificate by verification code"""
        serializer = CertificateVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        result = CertificateService.verify_certificate(
            serializer.validated_data['verification_code']
        )
        
        if result['valid']:
            return Response({
                'valid': True,
                'certificate': EnrollmentCertificateSerializer(result['certificate']).data,
                'is_expired': result['is_expired']
            })
        else:
            return Response({
                'valid': False,
                'error': result['error']
            })
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageCertificates])
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
                'certificate': EnrollmentCertificateSerializer(certificate).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'], permission_classes=[CanManageCertificates])
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
    
    @action(detail=False, methods=['get'], permission_classes=[IsCertificateOwner])
    def my_certificates(self, request):
        """Get current user's certificates"""
        user = request.user
        certificates = self.get_queryset().filter(enrollment__user=user)
        
        return Response({
            'count': certificates.count(),
            'results': EnrollmentCertificateSerializer(certificates, many=True).data
        })
