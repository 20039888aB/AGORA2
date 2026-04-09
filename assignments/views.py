from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg, Sum

from .models import Assignment, AssignmentQuestion, AssignmentSubmission, AssignmentFile
from .serializers import (
    AssignmentSerializer, AssignmentCreateSerializer, AssignmentPublishSerializer, AssignmentCloseSerializer,
    AssignmentQuestionSerializer, AssignmentQuestionCreateSerializer, AssignmentQuestionReorderSerializer,
    AssignmentSubmissionSerializer, AssignmentSubmissionCreateSerializer, AssignmentSubmissionUpdateSerializer, AssignmentSubmissionGradeSerializer,
    AssignmentFileSerializer, AssignmentFileUploadSerializer,
    AssignmentStatisticsSerializer, AssignmentQuestionStatisticsSerializer
)
from .permissions import (
    IsAssignmentOwner, CanManageAssignment, CanViewAssignment,
    IsSubmissionOwner, CanManageSubmission, CanGradeSubmission,
    CanManageQuestion, CanSubmitAssignment, CanViewAssignmentStatistics,
    IsFileOwner, CanManageFile
)
from .services import (
    AssignmentService, AssignmentQuestionService, AssignmentSubmissionService, AssignmentFileService
)


class AssignmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Assignment model
    """
    queryset = Assignment.objects.filter(is_active=True)
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['course', 'lesson', 'assignment_type', 'status', 'is_published']
    search_fields = ['title', 'description', 'instructions']
    ordering_fields = ['course', '-created_at', 'title', 'due_date']
    ordering = ['course', '-created_at']
    
    def get_queryset(self):
        """Filter assignments based on user role"""
        user = self.request.user
        
        if user.is_superadmin():
            return self.queryset
        
        elif user.is_admin():
            return self.queryset.filter(course__organization=user.organization)
        
        elif user.is_manager():
            return self.queryset.filter(course__instructor=user)
        
        elif user.is_student():
            # Students can see assignments from courses they're enrolled in
            from enrollments.models import Enrollment
            enrolled_courses = Enrollment.objects.filter(
                user=user,
                status='ACTIVE'
            ).values_list('course_id', flat=True)
            return self.queryset.filter(course_id__in=enrolled_courses)
        
        return self.queryset.none()
    
    def get_permissions(self):
        """Return permissions based on action"""
        if self.action == 'create':
            permission_classes = [CanManageAssignment]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [CanManageAssignment]
        elif self.action == 'retrieve':
            permission_classes = [CanViewAssignment]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=False, methods=['post'], permission_classes=[CanManageAssignment])
    def create_assignment(self, request):
        """Create new assignment"""
        serializer = AssignmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            from courses.models import Course
            course = Course.objects.get(id=serializer.validated_data['course_id'])
            
            lesson_id = serializer.validated_data.get('lesson_id')
            lesson = None
            if lesson_id:
                lesson = Course.objects.get(id=lesson_id)
            
            assignment_data = {
                'title': serializer.validated_data['title'],
                'description': serializer.validated_data['description'],
                'instructions': serializer.validated_data['instructions'],
                'assignment_type': serializer.validated_data['assignment_type'],
                'course': course,
                'lesson': lesson,
                'max_score': serializer.validated_data['max_score'],
                'passing_score': serializer.validated_data['passing_score'],
                'duration_minutes': serializer.validated_data['duration_minutes'],
                'attempts_allowed': serializer.validated_data['attempts_allowed'],
                'randomize_questions': serializer.validated_data['randomize_questions'],
                'allow_late_submission': serializer.validated_data['allow_late_submission'],
                'available_from': serializer.validated_data['available_from'],
                'available_until': serializer.validated_data['available_until'],
                'due_date': serializer.validated_data['due_date'],
                'grace_period': serializer.validated_data['grace_period'],
                'created_by': request.user,
            }
            
            assignment = AssignmentService.create_assignment(assignment_data, request.user)
            
            return Response({
                'message': 'Assignment created successfully',
                'assignment': AssignmentSerializer(assignment).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageAssignment])
    def publish(self, request, pk=None):
        """Publish assignment"""
        assignment = self.get_object()
        
        try:
            AssignmentService.publish_assignment(assignment, request.user)
            return Response({
                'message': 'Assignment published successfully',
                'assignment': AssignmentSerializer(assignment).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageAssignment])
    def close(self, request, pk=None):
        """Close assignment"""
        assignment = self.get_object()
        
        try:
            AssignmentService.close_assignment(assignment, request.user)
            return Response({
                'message': 'Assignment closed successfully',
                'assignment': AssignmentSerializer(assignment).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageAssignment])
    def duplicate(self, request, pk=None):
        """Duplicate assignment"""
        assignment = self.get_object()
        
        try:
            new_assignment = AssignmentService.duplicate_assignment(assignment, request.user)
            return Response({
                'message': 'Assignment duplicated successfully',
                'assignment': AssignmentSerializer(new_assignment).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'], permission_classes=[CanViewAssignmentStatistics])
    def statistics(self, request, pk=None):
        """Get assignment statistics"""
        assignment = self.get_object()
        stats = AssignmentService.get_assignment_statistics(assignment)
        
        return Response(stats)


class AssignmentQuestionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AssignmentQuestion model
    """
    queryset = AssignmentQuestion.objects.all()
    serializer_class = AssignmentQuestionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['assignment', 'question_type', 'is_required']
    search_fields = ['question_text']
    ordering_fields = ['assignment', 'order']
    ordering = ['assignment', 'order']
    
    def get_queryset(self):
        """Filter questions based on user role"""
        user = self.request.user
        
        if user.is_superadmin():
            return self.queryset
        
        elif user.is_admin():
            return self.queryset.filter(assignment__course__organization=user.organization)
        
        elif user.is_manager():
            return self.queryset.filter(assignment__course__instructor=user)
        
        return self.queryset.none()
    
    def get_permissions(self):
        """Return permissions based on action"""
        if self.action == 'create':
            permission_classes = [CanManageQuestion]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [CanManageQuestion]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=False, methods=['post'], permission_classes=[CanManageQuestion])
    def create_question(self, request):
        """Create new assignment question"""
        serializer = AssignmentQuestionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            from assignments.models import Assignment
            assignment = Assignment.objects.get(id=serializer.validated_data['assignment_id'])
            
            question_data = {
                'assignment': assignment,
                'question_text': serializer.validated_data['question_text'],
                'question_type': serializer.validated_data['question_type'],
                'question_data': serializer.validated_data['question_data'],
                'points': serializer.validated_data['points'],
                'order': serializer.validated_data['order'],
                'is_required': serializer.validated_data['is_required'],
                'explanation': serializer.validated_data['explanation'],
            }
            
            question = AssignmentQuestionService.create_question(question_data, request.user)
            
            return Response({
                'message': 'Question created successfully',
                'question': AssignmentQuestionSerializer(question).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageQuestion])
    def reorder(self, request, pk=None):
        """Reorder questions in assignment"""
        assignment = self.get_object().assignment
        serializer = AssignmentQuestionReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            AssignmentQuestionService.reorder_questions(
                assignment,
                serializer.validated_data['question_orders'],
                request.user
            )
            
            return Response({
                'message': 'Questions reordered successfully'
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def statistics(self, request, pk=None):
        """Get question statistics"""
        question = self.get_object()
        stats = AssignmentQuestionService.get_question_statistics(question)
        
        return Response(stats)


class AssignmentSubmissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AssignmentSubmission model
    """
    queryset = AssignmentSubmission.objects.filter(is_active=True)
    serializer_class = AssignmentSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['assignment', 'student', 'status']
    search_fields = ['student__email']
    ordering_fields = ['assignment', 'student', '-submitted_at', '-created_at']
    ordering = ['assignment', 'student', '-attempt_number']
    
    def get_queryset(self):
        """Filter submissions based on user role"""
        user = self.request.user
        
        if user.is_superadmin():
            return self.queryset
        
        elif user.is_admin():
            return self.queryset.filter(assignment__course__organization=user.organization)
        
        elif user.is_manager():
            return self.queryset.filter(assignment__course__instructor=user)
        
        elif user.is_student():
            return self.queryset.filter(student=user)
        
        return self.queryset.none()
    
    def get_permissions(self):
        """Return permissions based on action"""
        if self.action == 'create':
            permission_classes = [CanSubmitAssignment]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [CanManageSubmission]
        elif self.action == 'retrieve':
            permission_classes = [IsSubmissionOwner]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=False, methods=['post'], permission_classes=[CanSubmitAssignment])
    def create_submission(self, request):
        """Create new assignment submission"""
        serializer = AssignmentSubmissionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            from assignments.models import Assignment
            assignment = Assignment.objects.get(id=serializer.validated_data['assignment_id'])
            
            submission = AssignmentSubmissionService.create_submission(
                student=request.user,
                assignment=assignment,
                attempt_number=serializer.validated_data['attempt_number']
            )
            
            return Response({
                'message': 'Submission created successfully',
                'submission': AssignmentSubmissionSerializer(submission).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageSubmission])
    def update_submission(self, request, pk=None):
        """Update assignment submission"""
        submission = self.get_object()
        serializer = AssignmentSubmissionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            AssignmentSubmissionService.update_submission(
                submission,
                answers=serializer.validated_data.get('answers'),
                text_content=serializer.validated_data.get('text_content'),
                attached_files=serializer.validated_data.get('attached_files'),
                updated_by=request.user
            )
            
            return Response({
                'message': 'Submission updated successfully',
                'submission': AssignmentSubmissionSerializer(submission).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageSubmission])
    def submit(self, request, pk=None):
        """Submit assignment"""
        submission = self.get_object()
        
        try:
            AssignmentSubmissionService.submit_assignment(submission, request.user)
            return Response({
                'message': 'Assignment submitted successfully',
                'submission': AssignmentSubmissionSerializer(submission).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[CanGradeSubmission])
    def grade(self, request, pk=None):
        """Grade assignment submission"""
        submission = self.get_object()
        serializer = AssignmentSubmissionGradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            AssignmentSubmissionService.grade_submission(
                submission,
                float(serializer.validated_data['score']),
                serializer.validated_data.get('feedback'),
                request.user
            )
            
            return Response({
                'message': 'Assignment graded successfully',
                'submission': AssignmentSubmissionSerializer(submission).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[CanGradeSubmission])
    def auto_grade(self, request, pk=None):
        """Auto-grade assignment submission"""
        submission = self.get_object()
        
        try:
            AssignmentSubmissionService.auto_grade_submission(submission)
            return Response({
                'message': 'Assignment auto-graded successfully',
                'submission': AssignmentSubmissionSerializer(submission).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'], permission_classes=[IsSubmissionOwner])
    def my_submissions(self, request):
        """Get current user's submissions"""
        user = request.user
        submissions = self.get_queryset().filter(student=user)
        
        return Response({
            'count': submissions.count(),
            'results': AssignmentSubmissionSerializer(submissions, many=True).data
        })


class AssignmentFileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AssignmentFile model
    """
    queryset = AssignmentFile.objects.filter(is_active=True)
    serializer_class = AssignmentFileSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['assignment', 'submission', 'file_type']
    search_fields = ['title']
    ordering_fields = ['assignment', 'submission', '-uploaded_at']
    ordering = ['-uploaded_at']
    
    def get_queryset(self):
        """Filter files based on user role"""
        user = self.request.user
        
        if user.is_superadmin():
            return self.queryset
        
        elif user.is_admin():
            return self.queryset.filter(
                models.Q(assignment__course__organization=user.organization) |
                models.Q(submission__assignment__course__organization=user.organization)
            )
        
        elif user.is_manager():
            return self.queryset.filter(
                models.Q(assignment__course__instructor=user) |
                models.Q(submission__assignment__course__instructor=user)
            )
        
        elif user.is_student():
            return self.queryset.filter(
                models.Q(uploaded_by=user) |
                models.Q(submission__student=user)
            )
        
        return self.queryset.none()
    
    def get_permissions(self):
        """Return permissions based on action"""
        if self.action == 'create':
            permission_classes = [CanManageFile]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [CanManageFile]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=False, methods=['post'], permission_classes=[CanManageFile])
    def upload_file(self, request):
        """Upload assignment file"""
        serializer = AssignmentFileUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            assignment = None
            submission = None
            
            if serializer.validated_data.get('assignment_id'):
                from assignments.models import Assignment
                assignment = Assignment.objects.get(id=serializer.validated_data['assignment_id'])
            
            if serializer.validated_data.get('submission_id'):
                from assignments.models import AssignmentSubmission
                submission = AssignmentSubmission.objects.get(id=serializer.validated_data['submission_id'])
            
            file = AssignmentFileService.upload_file(
                assignment=assignment,
                submission=submission,
                file=serializer.validated_data['file'],
                title=serializer.validated_data['title'],
                uploaded_by=request.user
            )
            
            return Response({
                'message': 'File uploaded successfully',
                'file': AssignmentFileSerializer(file).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageFile])
    def delete_file(self, request, pk=None):
        """Delete assignment file"""
        file = self.get_object()
        
        try:
            AssignmentFileService.delete_file(file, request.user)
            return Response({
                'message': 'File deleted successfully'
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
