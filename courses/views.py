from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg

from .models import Course, Module, Lesson, Resource, Category, CourseReview
from .serializers import (
    CourseSerializer, CourseCreateSerializer, CoursePublishSerializer, CourseArchiveSerializer,
    ModuleSerializer, ModuleCreateSerializer, ModuleReorderSerializer,
    LessonSerializer, LessonCreateSerializer,
    ResourceSerializer, ResourceCreateSerializer,
    CategorySerializer, CategoryCreateSerializer,
    CourseReviewSerializer
)
from .permissions import (
    IsCourseInstructor, CanManageCourse, IsCourseMember, CanAccessCourseContent,
    CanManageModule, CanManageLesson, CanManageResource
)
from .services import CourseService, ModuleService, LessonService, ResourceService, CategoryService


class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Category model
    """
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['organization', 'parent', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['organization', 'name']
    ordering = ['organization', 'name']
    
    def get_queryset(self):
        """Filter categories based on user role"""
        user = self.request.user
        
        if user.is_superadmin():
            return self.queryset
        
        elif user.is_admin():
            return self.queryset.filter(organization=user.organization)
        
        return self.queryset.none()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return CategoryCreateSerializer
        return CategorySerializer
    
    def get_permissions(self):
        """Return permissions based on action"""
        if self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]  # Anyone authenticated can create
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [CanManageCourse]  # Only course managers
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageCourse])
    def move_category(self, request, pk=None):
        """Move category in hierarchy"""
        category = self.get_object()
        new_parent_id = request.data.get('parent')
        
        if new_parent_id is None:
            return Response(
                {'error': 'Parent ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            if new_parent_id == 'root':
                new_parent = None
            else:
                new_parent = Category.objects.get(id=new_parent_id)
            
            CategoryService.move_category(category, new_parent, request.user)
            
            return Response({
                'message': 'Category moved successfully',
                'category': CategorySerializer(category).data
            })
        except Category.DoesNotExist:
            return Response(
                {'error': 'Parent category not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class CourseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Course model
    """
    queryset = Course.objects.filter(is_active=True)
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['organization', 'category', 'instructor', 'status', 'difficulty', 'is_featured']
    search_fields = ['title', 'description', 'short_description']
    ordering_fields = ['organization', '-created_at', 'title']
    ordering = ['organization', '-created_at']
    
    def get_queryset(self):
        """Filter courses based on user role"""
        user = self.request.user
        
        if user.is_superadmin():
            return self.queryset
        
        elif user.is_admin():
            return self.queryset.filter(organization=user.organization)
        
        elif user.is_manager():
            return self.queryset.filter(
                organization=user.organization,
                instructor=user
            )
        
        return self.queryset.none()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return CourseCreateSerializer
        return CourseSerializer
    
    def get_permissions(self):
        """Return permissions based on action"""
        if self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]  # Anyone authenticated can create
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [CanManageCourse]
        else:
            permission_classes = [IsCourseMember]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageCourse])
    def publish(self, request, pk=None):
        """Publish course"""
        course = self.get_object()
        serializer = CoursePublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            CourseService.publish_course(course, request.user)
            return Response({
                'message': 'Course published successfully',
                'course': CourseSerializer(course).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageCourse])
    def archive(self, request, pk=None):
        """Archive course"""
        course = self.get_object()
        serializer = CourseArchiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            CourseService.archive_course(course, request.user)
            return Response({
                'message': 'Course archived successfully',
                'course': CourseSerializer(course).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageCourse])
    def duplicate(self, request, pk=None):
        """Duplicate course with modules and lessons"""
        course = self.get_object()
        include_modules = request.data.get('include_modules', False)
        include_lessons = request.data.get('include_lessons', False)
        
        try:
            new_course = CourseService.duplicate_course(
                course, request.user, include_modules, include_lessons
            )
            return Response({
                'message': 'Course duplicated successfully',
                'course': CourseSerializer(new_course).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'], permission_classes=[CanManageCourse])
    def statistics(self, request, pk=None):
        """Get course statistics"""
        course = self.get_object()
        stats = CourseService.get_course_statistics(course)
        
        return Response(stats)
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_courses(self, request):
        """Get courses accessible to current user"""
        user = request.user
        courses = self.get_queryset()
        
        return Response({
            'count': courses.count(),
            'results': CourseSerializer(courses, many=True).data
        })


class ModuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Module model
    """
    queryset = Module.objects.filter(is_active=True)
    serializer_class = ModuleSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['course', 'is_active', 'is_published']
    search_fields = ['title', 'description']
    ordering_fields = ['course', 'order']
    ordering = ['course', 'order']
    
    def get_queryset(self):
        """Filter modules based on user role"""
        user = self.request.user
        
        if user.is_superadmin():
            return self.queryset
        
        elif user.is_admin():
            return self.queryset.filter(course__organization=user.organization)
        
        elif user.is_manager():
            return self.queryset.filter(
                course__instructor=user
            )
        
        return self.queryset.none()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return ModuleCreateSerializer
        return ModuleSerializer
    
    def get_permissions(self):
        """Return permissions based on action"""
        if self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [CanManageModule]
        else:
            permission_classes = [CanAccessCourseContent]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageModule])
    def create_module(self, request, pk=None):
        """Create new module"""
        course_id = request.data.get('course')
        
        if not course_id:
            return Response(
                {'error': 'Course ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from courses.models import Course
            course = Course.objects.get(id=course_id)
            ModuleService.create_module(request.data, creator=request.user)
            return Response({
                'message': 'Module created successfully',
                'module': ModuleSerializer(module).data
            })
        except Course.DoesNotExist:
            return Response(
                {'error': 'Course not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageModule])
    def reorder(self, request, pk=None):
        """Reorder modules in course"""
        course = self.get_object()
        serializer = ModuleReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            ModuleService.reorder_modules(course, serializer.validated_data['module_orders'], request.user)
            return Response({
                'message': 'Modules reordered successfully'
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class LessonViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Lesson model
    """
    queryset = Lesson.objects.filter(is_published=True)
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['module', 'lesson_type', 'is_published', 'is_free', 'is_locked']
    search_fields = ['title', 'description']
    ordering_fields = ['module', 'order']
    ordering = ['module', 'order']
    
    def get_queryset(self):
        """Filter lessons based on user role"""
        user = self.request.user
        
        if user.is_superadmin():
            return self.queryset
        
        elif user.is_admin():
            return self.queryset.filter(module__course__organization=user.organization)
        
        elif user.is_manager():
            return self.queryset.filter(
                module__course__instructor=user
            )
        
        return self.queryset.none()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return LessonCreateSerializer
        return LessonSerializer
    
    def get_permissions(self):
        """Return permissions based on action"""
        if self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [CanManageLesson]
        else:
            permission_classes = [CanAccessCourseContent]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageLesson])
    def create_lesson(self, request, pk=None):
        """Create new lesson"""
        module_id = request.data.get('module')
        
        if not module_id:
            return Response(
                {'error': 'Module ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from courses.models import Module
            module = Module.objects.get(id=module_id)
            LessonService.create_lesson(request.data, creator=request.user)
            return Response({
                'message': 'Lesson created successfully',
                'lesson': LessonSerializer(lesson).data
            })
        except Module.DoesNotExist:
            return Response(
                {'error': 'Module not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageLesson])
    def publish(self, request, pk=None):
        """Publish lesson"""
        lesson = self.get_object()
        
        try:
            LessonService.publish_lesson(lesson, request.user)
            return Response({
                'message': 'Lesson published successfully',
                'lesson': LessonSerializer(lesson).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'], permission_classes=[CanManageLesson])
    def statistics(self, request, pk=None):
        """Get lesson statistics"""
        lesson = self.get_object()
        stats = LessonService.get_lesson_statistics(lesson)
        
        return Response(stats)


class ResourceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Resource model
    """
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['lesson', 'resource_type', 'is_required']
    search_fields = ['title', 'description']
    ordering_fields = ['lesson', 'order']
    ordering = ['lesson', 'order']
    
    def get_queryset(self):
        """Filter resources based on user role"""
        user = self.request.user
        
        if user.is_superadmin():
            return self.queryset
        
        elif user.is_admin():
            return self.queryset.filter(lesson__module__course__organization=user.organization)
        
        elif user.is_manager():
            return self.queryset.filter(
                lesson__module__course__instructor=user
            )
        
        return self.queryset.none()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return ResourceCreateSerializer
        return ResourceSerializer
    
    def get_permissions(self):
        """Return permissions based on action"""
        if self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [CanManageResource]
        else:
            permission_classes = [CanAccessCourseContent]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageResource])
    def create_resource(self, request, pk=None):
        """Create new resource"""
        lesson_id = request.data.get('lesson')
        
        if not lesson_id:
            return Response(
                {'error': 'Lesson ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from courses.models import Lesson
            lesson = Lesson.objects.get(id=lesson_id)
            ResourceService.create_resource(request.data, creator=request.user)
            return Response({
                'message': 'Resource created successfully',
                'resource': ResourceSerializer(resource).data
            })
        except Lesson.DoesNotExist:
            return Response(
                {'error': 'Lesson not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageResource])
    def track_download(self, request, pk=None):
        """Track resource download"""
        resource = self.get_object()
        user = request.user
        
        try:
            ResourceService.track_download(resource, user)
            return Response({
                'message': 'Download tracked successfully'
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class CourseReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CourseReview model
    """
    queryset = CourseReview.objects.all()
    serializer_class = CourseReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['course', 'user', 'rating']
    search_fields = ['review', 'user__email']
    ordering_fields = ['-created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter reviews based on user role"""
        user = self.request.user
        
        if user.is_superadmin():
            return self.queryset
        
        elif user.is_admin():
            return self.queryset.filter(course__organization=user.organization)
        
        return self.queryset.filter(user=user)
    
    def get_permissions(self):
        """Return permissions based on action"""
        if self.action == 'create':
            permission_classes = [IsCourseMember]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=True, methods=['post'], permission_classes=[IsCourseMember])
    def create_review(self, request, pk=None):
        """Create course review"""
        course_id = request.data.get('course')
        rating = request.data.get('rating')
        review = request.data.get('review')
        
        if not all([course_id, rating, review]):
            return Response(
                {'error': 'Course ID, rating, and review are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from courses.models import Course
            course = Course.objects.get(id=course_id)
            
            # Check if user is enrolled and has completed the course
            from enrollments.models import Enrollment
            if not Enrollment.objects.filter(
                user=request.user,
                course=course,
                status='COMPLETED'
            ).exists():
                return Response(
                    {'error': 'You must complete the course before reviewing'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            review = CourseReview.objects.create(
                course=course,
                user=request.user,
                rating=rating,
                review=review,
                is_verified=False
            )
            
            return Response({
                'message': 'Review created successfully',
                'review': CourseReviewSerializer(review).data
            })
        except Course.DoesNotExist:
            return Response(
                {'error': 'Course not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
