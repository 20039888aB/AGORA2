from django.db import models, transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Course, Module, Lesson, Resource, Category, CourseReview


class CourseService:
    """
    Service layer for Course business logic
    """
    
    @staticmethod
    def create_course(data, creator=None):
        """Create new course with validation"""
        # Validate permissions
        if creator and not creator.is_admin_or_above():
            raise ValidationError("Only admins can create courses")
        
        # Validate organization
        if not data.get('organization'):
            raise ValidationError("Organization is required")
        
        # Validate category belongs to same organization
        category = Category.objects.get(id=data.get('category'))
        if category.organization != data.get('organization'):
            raise ValidationError("Category must belong to same organization")
        
        # Validate instructor belongs to same organization
        instructor = data.get('instructor')
        if instructor and instructor.organization != data.get('organization'):
            raise ValidationError("Instructor must belong to same organization")
        
        course = Course.objects.create(**data)
        
        # Auto-assign creator as instructor if not specified
        if not instructor and not creator.is_superadmin():
            course.instructor = creator
            course.save(update_fields=['instructor'])
        
        return course
    
    @staticmethod
    def publish_course(course, published_by):
        """Publish course"""
        if course.status != 'DRAFT':
            raise ValidationError("Only draft courses can be published")
        
        course.status = 'PUBLISHED'
        course.save(update_fields=['status'])
        
        # Log course publication
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=published_by,
            action='COURSE_PUBLISH',
            details={
                'course': str(course.id),
                'title': course.title,
            },
            ip_address=published_by.last_login_ip
        )
    
    @staticmethod
    def archive_course(course, archived_by):
        """Archive course"""
        if course.status == 'ARCHIVED':
            raise ValidationError("Course is already archived")
        
        course.status = 'ARCHIVED'
        course.save(update_fields=['status'])
        
        # Log course archival
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=archived_by,
            action='COURSE_ARCHIVE',
            details={
                'course': str(course.id),
                'title': course.title,
            },
            ip_address=archived_by.last_login_ip
        )
    
    @staticmethod
    def get_course_statistics(course):
        """Get comprehensive course statistics"""
        from enrollments.models import Enrollment
        
        enrollments = Enrollment.objects.filter(course=course, is_active=True)
        
        return {
            'total_enrollments': enrollments.count(),
            'active_enrollments': enrollments.filter(status='ACTIVE').count(),
            'completed_enrollments': enrollments.filter(status='COMPLETED').count(),
            'average_progress': enrollments.aggregate(
                avg_progress=models.Avg('progress_percentage')
            )['avg_progress'] or 0,
            'total_reviews': course.coursereview_set.count(),
            'average_rating': course.coursereview_set.aggregate(
                avg_rating=models.Avg('rating')
            )['avg_rating'] or 0,
            'total_modules': course.total_modules,
            'total_lessons': course.total_lessons,
        }
    
    @staticmethod
    def duplicate_course(course, creator, modules=None, lessons=None):
        """Duplicate course with modules and lessons"""
        with transaction.atomic():
            # Create new course
            new_course = Course.objects.create(
                title=f"{course.title} (Copy)",
                slug=f"{course.slug}-copy",
                description=course.description,
                category=course.category,
                instructor=creator,
                organization=course.organization,
                difficulty=course.difficulty,
                duration_hours=course.duration_hours,
                price=course.price,
                prerequisites=course.prerequisites,
                objectives=course.objectives,
                outcomes=course.outcomes,
                tags=course.tags,
                language=course.language,
                max_students=course.max_students,
                certificate_enabled=course.certificate_enabled,
                is_featured=False,
                status='DRAFT'
            )
            
            # Duplicate modules
            if modules:
                for module in course.modules.filter(is_active=True):
                    Module.objects.create(
                        course=new_course,
                        title=module.title,
                        slug=f"{module.slug}-copy",
                        description=module.description,
                        order=module.order,
                        is_published=False
                    )
            
            # Duplicate lessons
            if lessons:
                for lesson in course.lessons.filter(is_active=True):
                    Lesson.objects.create(
                        course=new_course,
                        module=Module.objects.get(
                            course=new_course,
                            slug=f"{lesson.module.slug}-copy"
                        ),
                        title=lesson.title,
                        slug=f"{lesson.slug}-copy",
                        description=lesson.description,
                        lesson_type=lesson.lesson_type,
                        content=lesson.content,
                        video_url=lesson.video_url,
                        external_url=lesson.external_url,
                        duration_minutes=lesson.duration_minutes,
                        order=lesson.order,
                        is_published=False,
                        is_free=lesson.is_free,
                        is_locked=lesson.is_locked,
                        unlock_conditions=lesson.unlock_conditions
                    )
        
        return new_course


class ModuleService:
    """
    Service layer for Module business logic
    """
    
    @staticmethod
    def create_module(data, creator=None):
        """Create new module with validation"""
        # Validate permissions
        if creator and not creator.is_admin_or_above():
            raise ValidationError("Only admins can create modules")
        
        # Validate course belongs to same organization
        course = data.get('course')
        if course and course.organization != creator.organization:
            raise ValidationError("Course must belong to same organization")
        
        module = Module.objects.create(**data)
        return module
    
    @staticmethod
    def reorder_modules(course, module_orders, reordered_by):
        """Reorder modules in course"""
        with transaction.atomic():
            for module_id, new_order in module_orders.items():
                module = Module.objects.get(id=module_id, course=course)
                module.order = new_order
                module.save(update_fields=['order'])
        
        # Log reordering
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=reordered_by,
            action='MODULE_REORDER',
            details={
                'course': str(course.id),
                'module_orders': module_orders,
            },
            ip_address=reordered_by.last_login_ip
        )


class LessonService:
    """
    Service layer for Lesson business logic
    """
    
    @staticmethod
    def create_lesson(data, creator=None):
        """Create new lesson with validation"""
        # Validate permissions
        if creator and not creator.is_admin_or_above():
            raise ValidationError("Only admins can create lessons")
        
        # Validate module belongs to same course and organization
        module = data.get('module')
        if module:
            if module.course.organization != creator.organization:
                raise ValidationError("Module must belong to same organization")
        
        lesson = Lesson.objects.create(**data)
        return lesson
    
    @staticmethod
    def publish_lesson(lesson, published_by):
        """Publish lesson"""
        if lesson.is_published:
            raise ValidationError("Lesson is already published")
        
        lesson.is_published = True
        lesson.save(update_fields=['is_published'])
        
        # Log lesson publication
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=published_by,
            action='LESSON_PUBLISH',
            details={
                'lesson': str(lesson.id),
                'title': lesson.title,
            },
            ip_address=published_by.last_login_ip
        )
    
    @staticmethod
    def get_lesson_statistics(lesson):
        """Get lesson statistics"""
        from enrollments.models import LessonProgress
        
        progress_records = LessonProgress.objects.filter(lesson=lesson)
        
        return {
            'total_students': progress_records.count(),
            'completed_students': progress_records.filter(completed_at__isnull=False).count(),
            'average_progress': progress_records.aggregate(
                avg_progress=models.Avg('progress_percentage')
            )['avg_progress'] or 0,
            'total_resources': lesson.resources.count(),
        }


class ResourceService:
    """
    Service layer for Resource business logic
    """
    
    @staticmethod
    def create_resource(data, creator=None):
        """Create new resource with validation"""
        # Validate permissions
        if creator and not creator.is_admin_or_above():
            raise ValidationError("Only admins can create resources")
        
        # Validate lesson belongs to same course
        lesson = data.get('lesson')
        if lesson and lesson.module.course.organization != creator.organization:
            raise ValidationError("Lesson must belong to same organization")
        
        resource = Resource.objects.create(**data)
        return resource
    
    @staticmethod
    def track_download(resource, user):
        """Track resource download"""
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=user,
            action='RESOURCE_DOWNLOAD',
            details={
                'resource': str(resource.id),
                'title': resource.title,
                'lesson': str(resource.lesson.id),
            },
            ip_address=user.last_login_ip
        )


class CategoryService:
    """
    Service layer for Category business logic
    """
    
    @staticmethod
    def create_category(data, creator=None):
        """Create new category with validation"""
        # Validate permissions
        if creator and not creator.is_admin_or_above():
            raise ValidationError("Only admins can create categories")
        
        # Validate organization
        if not data.get('organization'):
            raise ValidationError("Organization is required")
        
        category = Category.objects.create(**data)
        return category
    
    @staticmethod
    def move_category(category, new_parent, moved_by):
        """Move category in hierarchy"""
        # Validate no cycles
        current = new_parent
        max_depth = 10  # Prevent infinite loops
        
        for _ in range(max_depth):
            if not current:
                break
            if current.id == category.id:
                raise ValidationError("Cannot create circular hierarchy")
            current = current.parent
        
        category.parent = new_parent
        category.save(update_fields=['parent'])
        
        # Log category move
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=moved_by,
            action='CATEGORY_MOVE',
            details={
                'category': str(category.id),
                'old_parent': str(category.parent_id) if category.parent_id else None,
                'new_parent': str(new_parent.id) if new_parent else None,
            },
            ip_address=moved_by.last_login_ip
        )
