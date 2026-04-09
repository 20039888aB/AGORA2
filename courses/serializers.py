from rest_framework import serializers
from .models import Course, Module, Lesson, Resource, Category, CourseReview


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for Category model
    """
    full_path = serializers.ReadOnlyField()
    level = serializers.ReadOnlyField()
    total_courses = serializers.ReadOnlyField()
    total_subcategories = serializers.ReadOnlyField()
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'icon', 'parent',
            'organization', 'is_active', 'created_at', 'updated_at',
            'full_path', 'level', 'total_courses', 'total_subcategories'
        ]
        read_only_fields = ['created_at', 'updated_at', 'full_path', 'level', 'total_courses', 'total_subcategories']


class CategoryCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating Category model
    """
    class Meta:
        model = Category
        fields = [
            'name', 'description', 'icon', 'parent', 'organization', 'is_active'
        ]
    
    def validate_parent(self, value):
        """Validate that parent category is in the same organization"""
        if value and hasattr(self, 'context') and 'request' in self.context:
            organization = self.context['request'].user.organization
            if value.organization != organization:
                raise serializers.ValidationError("Parent category must be in the same organization")
        return value


class CourseSerializer(serializers.ModelSerializer):
    """
    Serializer for Course model
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    instructor_info = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    difficulty_display = serializers.CharField(source='get_difficulty_display', read_only=True)
    total_modules = serializers.ReadOnlyField()
    total_lessons = serializers.ReadOnlyField()
    total_enrollments = serializers.ReadOnlyField()
    is_accessible = serializers.ReadOnlyField()
    is_published = serializers.ReadOnlyField()
    
    class Meta:
        model = Course
        fields = [
            'id', 'title', 'slug', 'description', 'short_description',
            'category', 'category_name', 'instructor', 'instructor_info',
            'thumbnail', 'status', 'status_display', 'difficulty',
            'difficulty_display', 'duration_hours', 'price', 'prerequisites',
            'objectives', 'outcomes', 'tags', 'language',
            'max_students', 'certificate_enabled', 'is_featured',
            'organization', 'is_active', 'created_at', 'updated_at',
            'total_modules', 'total_lessons', 'total_enrollments',
            'is_accessible', 'is_published'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'total_modules', 'total_lessons',
            'total_enrollments', 'is_accessible', 'is_published'
        ]
    
    def get_instructor_info(self, obj):
        """Get instructor information"""
        if obj.instructor:
            return {
                'id': str(obj.instructor.id),
                'email': obj.instructor.email,
                'full_name': obj.instructor.full_name,
            }
        return None
    
    def validate_status(self, value):
        """Validate course status"""
        if value == 'PUBLISHED' and not self.instance.is_accessible:
            raise serializers.ValidationError("Course must be accessible before publishing")
        return value


class ModuleSerializer(serializers.ModelSerializer):
    """
    Serializer for Module model
    """
    course_title = serializers.CharField(source='course.title', read_only=True)
    full_name = serializers.ReadOnlyField()
    total_lessons = serializers.ReadOnlyField()
    
    class Meta:
        model = Module
        fields = [
            'id', 'course', 'course_title', 'title', 'slug', 'description',
            'order', 'is_active', 'is_published', 'created_at', 'updated_at',
            'full_name', 'total_lessons'
        ]
        read_only_fields = ['created_at', 'updated_at', 'full_name', 'total_lessons']


class LessonSerializer(serializers.ModelSerializer):
    """
    Serializer for Lesson model
    """
    module_title = serializers.CharField(source='module.title', read_only=True)
    course_title = serializers.CharField(source='module.course.title', read_only=True)
    full_name = serializers.ReadOnlyField()
    lesson_type_display = serializers.CharField(source='get_lesson_type_display', read_only=True)
    file_size = serializers.SerializerMethodField()
    total_resources = serializers.ReadOnlyField()
    
    class Meta:
        model = Lesson
        fields = [
            'id', 'module', 'module_title', 'course_title', 'title', 'slug',
            'description', 'lesson_type', 'lesson_type_display', 'content',
            'video_url', 'pdf_file', 'external_url', 'duration_minutes',
            'order', 'is_published', 'is_free', 'is_locked',
            'unlock_conditions', 'created_at', 'updated_at', 'full_name',
            'total_resources', 'file_size'
        ]
        read_only_fields = ['created_at', 'updated_at', 'full_name', 'total_resources', 'file_size']
    
    def get_file_size(self, obj):
        """Get file size in human readable format"""
        return obj.file_size


class ResourceSerializer(serializers.ModelSerializer):
    """
    Serializer for Resource model
    """
    lesson_title = serializers.CharField(source='lesson.title', read_only=True)
    resource_type_display = serializers.CharField(source='get_resource_type_display', read_only=True)
    file_size = serializers.SerializerMethodField()
    
    class Meta:
        model = Resource
        fields = [
            'id', 'lesson', 'lesson_title', 'title', 'description',
            'resource_type', 'resource_type_display', 'file', 'url',
            'download_url', 'order', 'is_required', 'created_at',
            'updated_at', 'file_size'
        ]
        read_only_fields = ['created_at', 'updated_at', 'file_size']
    
    def get_file_size(self, obj):
        """Get file size in human readable format"""
        return obj.file_size


class CourseReviewSerializer(serializers.ModelSerializer):
    """
    Serializer for CourseReview model
    """
    user_info = serializers.SerializerMethodField()
    rating_display = serializers.CharField(source='get_rating_display', read_only=True)
    
    class Meta:
        model = CourseReview
        fields = [
            'id', 'course', 'user', 'user_info', 'rating',
            'rating_display', 'review', 'is_verified', 'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_user_info(self, obj):
        """Get user information"""
        return {
            'id': str(obj.user.id),
            'email': obj.user.email,
            'full_name': obj.user.full_name,
        }


class CourseCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating courses
    """
    class Meta:
        model = Course
        fields = [
            'title', 'slug', 'description', 'short_description', 'category',
            'instructor', 'difficulty', 'duration_hours', 'price',
            'prerequisites', 'objectives', 'outcomes', 'tags',
            'language', 'max_students', 'certificate_enabled'
        ]


class ModuleCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating modules
    """
    class Meta:
        model = Module
        fields = [
            'course', 'title', 'slug', 'description', 'order'
        ]


class LessonCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating lessons
    """
    class Meta:
        model = Lesson
        fields = [
            'module', 'title', 'slug', 'description', 'lesson_type',
            'content', 'video_url', 'external_url', 'duration_minutes',
            'order', 'is_free', 'is_locked', 'unlock_conditions'
        ]


class ResourceCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating resources
    """
    class Meta:
        model = Resource
        fields = [
            'lesson', 'title', 'description', 'resource_type',
            'file', 'url', 'download_url', 'order', 'is_required'
        ]


class CoursePublishSerializer(serializers.Serializer):
    """
    Serializer for publishing courses
    """
    pass


class CourseArchiveSerializer(serializers.Serializer):
    """
    Serializer for archiving courses
    """
    pass


class ModuleReorderSerializer(serializers.Serializer):
    """
    Serializer for reordering modules
    """
    module_orders = serializers.JSONField()
    
    def validate_module_orders(self, value):
        """Validate module orders"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Module orders must be a dictionary")
        
        for module_id, order in value.items():
            if not isinstance(order, int) or order < 0:
                raise serializers.ValidationError(f"Invalid order for module {module_id}")
        
        return value
