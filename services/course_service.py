"""
Course Service - Centralized Course Business Logic

This service contains all course-related business logic that should be used
instead of putting logic directly in models or views.
"""

from django.db import models, transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db.models import Q, Avg, Count
import uuid

User = get_user_model()


class CourseService:
    """
    Service layer for Course business logic
    """
    
    @staticmethod
    def create_course(data, created_by=None):
        """
        Create new course with validation and business logic
        """
        # Extract and validate required fields
        title = data.get('title')
        organization = data.get('organization')
        instructor = data.get('instructor')
        
        if not title:
            raise ValidationError("Course title is required")
        if not organization:
            raise ValidationError("Organization is required")
        if not instructor:
            raise ValidationError("Instructor is required")
        
        # Validate instructor belongs to same organization
        if instructor.organization != organization:
            raise ValidationError("Instructor must belong to same organization")
        
        # Check if course already exists in organization
        from courses.models import Course
        if Course.objects.filter(organization=organization, title=title).exists():
            raise ValidationError("Course with this title already exists in this organization")
        
        # Create course
        course = Course.objects.create(
            title=title,
            slug=data.get('slug', ''),
            description=data.get('description', ''),
            short_description=data.get('short_description', ''),
            organization=organization,
            category=data.get('category', None),
            instructor=instructor,
            difficulty=data.get('difficulty', 'BEGINNER'),
            duration_hours=data.get('duration_hours', 0),
            price=data.get('price', 0.00),
            max_students=data.get('max_students', 0),
            prerequisites=data.get('prerequisites', []),
            objectives=data.get('objectives', []),
            outcomes=data.get('outcomes', []),
            tags=data.get('tags', []),
            language=data.get('language', 'en'),
            certificate_enabled=data.get('certificate_enabled', False),
            is_featured=data.get('is_featured', False),
            is_active=data.get('is_active', True)
        )
        
        # Log course creation
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=created_by,
            action='COURSE_CREATE',
            details={
                'course_id': str(course.id),
                'title': course.title,
                'organization_id': str(organization.id),
                'instructor_id': str(instructor.id)
            },
            ip_address=created_by.last_login_ip if created_by else None
        )
        
        return course
    
    @staticmethod
    def update_course(course, data, updated_by=None):
        """
        Update course with validation and business logic
        """
        # Check if title is being changed and validate uniqueness
        if 'title' in data and data['title'] != course.title:
            from courses.models import Course
            if Course.objects.filter(
                organization=course.organization,
                title=data['title']
            ).exclude(id=course.id).exists():
                raise ValidationError("Course with this title already exists in this organization")
        
        # Validate instructor change
        if 'instructor' in data and data['instructor']:
            if data['instructor'].organization != course.organization:
                raise ValidationError("Instructor must belong to same organization")
        
        # Update course fields
        for field, value in data.items():
            if hasattr(course, field) and field not in ['id']:
                setattr(course, field, value)
        
        course.save()
        
        # Log course update
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=updated_by,
            action='COURSE_UPDATE',
            details={
                'course_id': str(course.id),
                'title': course.title,
                'updated_fields': list(data.keys())
            },
            ip_address=updated_by.last_login_ip if updated_by else None
        )
        
        return course
    
    @staticmethod
    def publish_course(course, published_by=None):
        """
        Publish course
        """
        if course.status == 'PUBLISHED':
            raise ValidationError("Course is already published")
        
        # Validate course has required content
        if not course.modules.filter(is_active=True).exists():
            raise ValidationError("Course must have at least one active module to be published")
        
        course.status = 'PUBLISHED'
        course.published_at = timezone.now()
        course.save(update_fields=['status', 'published_at'])
        
        # Log course publication
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=published_by,
            action='COURSE_PUBLISH',
            details={
                'course_id': str(course.id),
                'title': course.title
            },
            ip_address=published_by.last_login_ip if published_by else None
        )
        
        return course
    
    @staticmethod
    def archive_course(course, archived_by=None):
        """
        Archive course
        """
        if course.status == 'ARCHIVED':
            raise ValidationError("Course is already archived")
        
        course.status = 'ARCHIVED'
        course.archived_at = timezone.now()
        course.save(update_fields=['status', 'archived_at'])
        
        # Log course archiving
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=archived_by,
            action='COURSE_ARCHIVE',
            details={
                'course_id': str(course.id),
                'title': course.title
            },
            ip_address=archived_by.last_login_ip if archived_by else None
        )
        
        return course
    
    @staticmethod
    def duplicate_course(course, creator=None, include_modules=False, include_lessons=False):
        """
        Duplicate course with optional content
        """
        from courses.models import Course, Module, Lesson
        
        # Create new course
        new_course = Course.objects.create(
            title=f"{course.title} (Copy)",
            slug=f"{course.slug}-copy-{uuid.uuid4().hex[:8]}",
            description=course.description,
            short_description=course.short_description,
            organization=course.organization,
            category=course.category,
            instructor=creator,
            difficulty=course.difficulty,
            duration_hours=course.duration_hours,
            price=course.price,
            max_students=course.max_students,
            prerequisites=course.prerequisites,
            objectives=course.objectives,
            outcomes=course.outcomes,
            tags=course.tags,
            language=course.language,
            certificate_enabled=course.certificate_enabled,
            is_featured=False,
            is_active=True,
            status='DRAFT'
        )
        
        # Duplicate modules if requested
        if include_modules:
            for module in course.modules.filter(is_active=True):
                new_module = Module.objects.create(
                    course=new_course,
                    title=module.title,
                    description=module.description,
                    order=module.order,
                    is_active=True,
                    is_published=False
                )
                
                # Duplicate lessons if requested
                if include_lessons:
                    for lesson in module.lessons.filter(is_active=True):
                        Lesson.objects.create(
                            module=new_module,
                            title=lesson.title,
                            description=lesson.description,
                            lesson_type=lesson.lesson_type,
                            content=lesson.content,
                            order=lesson.order,
                            duration_minutes=lesson.duration_minutes,
                            is_published=False,
                            is_active=True
                        )
        
        # Log course duplication
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=creator,
            action='COURSE_DUPLICATE',
            details={
                'original_course_id': str(course.id),
                'new_course_id': str(new_course.id),
                'include_modules': include_modules,
                'include_lessons': include_lessons
            },
            ip_address=creator.last_login_ip if creator else None
        )
        
        return new_course
    
    @staticmethod
    def create_module(course, data, created_by=None):
        """
        Create new module
        """
        from courses.models import Module
        
        # Validate required fields
        title = data.get('title')
        if not title:
            raise ValidationError("Module title is required")
        
        # Get next order
        last_order = Module.objects.filter(course=course).aggregate(
            models.Max('order')
        )['order__max'] or 0
        
        # Create module
        module = Module.objects.create(
            course=course,
            title=title,
            description=data.get('description', ''),
            order=data.get('order', last_order + 1),
            is_active=data.get('is_active', True),
            is_published=data.get('is_published', False)
        )
        
        # Log module creation
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=created_by,
            action='MODULE_CREATE',
            details={
                'module_id': str(module.id),
                'title': module.title,
                'course_id': str(course.id)
            },
            ip_address=created_by.last_login_ip if created_by else None
        )
        
        return module
    
    @staticmethod
    def create_lesson(module, data, created_by=None):
        """
        Create new lesson
        """
        from courses.models import Lesson
        
        # Validate required fields
        title = data.get('title')
        if not title:
            raise ValidationError("Lesson title is required")
        
        # Get next order
        last_order = Lesson.objects.filter(module=module).aggregate(
            models.Max('order')
        )['order__max'] or 0
        
        # Create lesson
        lesson = Lesson.objects.create(
            module=module,
            title=title,
            description=data.get('description', ''),
            lesson_type=data.get('lesson_type', 'TEXT'),
            content=data.get('content', ''),
            order=data.get('order', last_order + 1),
            duration_minutes=data.get('duration_minutes', 0),
            is_published=data.get('is_published', False),
            is_free=data.get('is_free', False),
            is_locked=data.get('is_locked', False),
            is_active=data.get('is_active', True)
        )
        
        # Log lesson creation
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=created_by,
            action='LESSON_CREATE',
            details={
                'lesson_id': str(lesson.id),
                'title': lesson.title,
                'module_id': str(module.id)
            },
            ip_address=created_by.last_login_ip if created_by else None
        )
        
        return lesson
    
    @staticmethod
    def reorder_modules(course, module_orders, reordered_by=None):
        """
        Reorder modules in course
        """
        from courses.models import Module
        
        with transaction.atomic():
            for module_id, new_order in module_orders.items():
                module = Module.objects.get(id=module_id, course=course)
                module.order = new_order
                module.save(update_fields=['order'])
        
        # Log module reordering
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=reordered_by,
            action='MODULE_REORDER',
            details={
                'course_id': str(course.id),
                'module_orders': module_orders
            },
            ip_address=reordered_by.last_login_ip if reordered_by else None
        )
    
    @staticmethod
    def get_course_statistics(course):
        """
        Get comprehensive course statistics
        """
        from enrollments.models import Enrollment
        from assignments.models import AssignmentSubmission
        from certificates.models import Certificate
        
        enrollments = Enrollment.objects.filter(course=course, is_active=True)
        submissions = AssignmentSubmission.objects.filter(assignment__course=course, is_active=True)
        certificates = Certificate.objects.filter(course=course)
        
        return {
            'total_enrollments': enrollments.count(),
            'active_enrollments': enrollments.filter(status='ACTIVE').count(),
            'completed_enrollments': enrollments.filter(status='COMPLETED').count(),
            'average_progress': enrollments.aggregate(
                avg_progress=Avg('progress_percentage')
            )['avg_progress'] or 0,
            'total_revenue': enrollments.aggregate(
                total=models.Sum('payment_amount')
            )['total'] or 0,
            'total_submissions': submissions.count(),
            'graded_submissions': submissions.filter(status='GRADED').count(),
            'average_score': submissions.filter(
                score__isnull=False
            ).aggregate(avg_score=Avg('score'))['avg_score'] or 0,
            'total_certificates': certificates.count(),
            'issued_certificates': certificates.filter(status='ISSUED').count(),
        }
    
    @staticmethod
    def get_lesson_statistics(lesson):
        """
        Get lesson statistics
        """
        from enrollments.models import LessonProgress
        
        progress_records = LessonProgress.objects.filter(lesson=lesson)
        
        return {
            'total_students': progress_records.count(),
            'completed_students': progress_records.filter(status='COMPLETED').count(),
            'in_progress_students': progress_records.filter(status='IN_PROGRESS').count(),
            'not_started_students': progress_records.filter(status='NOT_STARTED').count(),
            'average_progress': progress_records.aggregate(
                avg_progress=Avg('progress_percentage')
            )['avg_progress'] or 0,
            'average_time_spent': progress_records.aggregate(
                avg_time=Avg('time_spent')
            )['avg_time'] or timezone.timedelta(0),
        }
    
    @staticmethod
    def get_organization_courses(organization, status=None, category=None, instructor=None):
        """
        Get organization courses with filters
        """
        from courses.models import Course
        
        courses = Course.objects.filter(organization=organization, is_active=True)
        
        if status:
            courses = courses.filter(status=status)
        
        if category:
            courses = courses.filter(category=category)
        
        if instructor:
            courses = courses.filter(instructor=instructor)
        
        return courses
    
    @staticmethod
    def get_user_courses(user, role=None):
        """
        Get courses accessible to user based on role
        """
        from courses.models import Course
        
        if user.is_superadmin():
            return Course.objects.filter(is_active=True)
        
        elif user.is_admin():
            return Course.objects.filter(organization=user.organization, is_active=True)
        
        elif user.is_manager():
            return Course.objects.filter(
                instructor=user,
                is_active=True
            )
        
        elif user.is_student():
            # Get courses user is enrolled in
            from enrollments.models import Enrollment
            enrollment_ids = Enrollment.objects.filter(
                user=user,
                status='ACTIVE',
                is_active=True
            ).values_list('course_id', flat=True)
            return Course.objects.filter(id__in=enrollment_ids, is_active=True)
        
        return Course.objects.none()
    
    @staticmethod
    def search_courses(query, organization=None, user=None):
        """
        Search courses by title, description, or tags
        """
        from courses.models import Course
        
        courses = Course.objects.filter(is_active=True)
        
        if organization:
            courses = courses.filter(organization=organization)
        
        if user and not user.is_superadmin():
            courses = courses.filter(organization=user.organization)
        
        if query:
            courses = courses.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(tags__icontains=query)
            )
        
        return courses.distinct()
    
    @staticmethod
    def validate_course_access(user, course, action='view'):
        """
        Validate if user has access to course
        """
        if user.is_superadmin():
            return True
        
        if user.organization != course.organization:
            return False
        
        if action == 'view':
            return True
        
        if action in ['edit', 'delete', 'publish', 'archive']:
            return user.is_admin_or_above() or course.instructor == user
        
        if action == 'enroll':
            return course.is_accessible and course.status == 'PUBLISHED'
        
        return False
    
    @staticmethod
    def get_featured_courses(organization=None, limit=10):
        """
        Get featured courses
        """
        from courses.models import Course
        
        courses = Course.objects.filter(
            is_featured=True,
            is_active=True,
            status='PUBLISHED'
        )
        
        if organization:
            courses = courses.filter(organization=organization)
        
        return courses.order_by('-created_at')[:limit]
