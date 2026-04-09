from rest_framework import serializers
from django.utils import timezone
from .models import Assignment, AssignmentQuestion, AssignmentSubmission, AssignmentFile


class AssignmentSerializer(serializers.ModelSerializer):
    """
    Serializer for Assignment model
    """
    course_info = serializers.SerializerMethodField()
    lesson_info = serializers.SerializerMethodField()
    created_by_info = serializers.SerializerMethodField()
    assignment_type_display = serializers.CharField(source='get_assignment_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_available = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    total_submissions = serializers.ReadOnlyField()
    graded_submissions = serializers.ReadOnlyField()
    average_score = serializers.ReadOnlyField()
    
    class Meta:
        model = Assignment
        fields = [
            'id', 'title', 'description', 'instructions', 'assignment_type',
            'assignment_type_display', 'course', 'course_info', 'lesson',
            'lesson_info', 'max_score', 'passing_score', 'duration_minutes',
            'attempts_allowed', 'randomize_questions', 'allow_late_submission',
            'available_from', 'available_until', 'due_date', 'grace_period',
            'status', 'status_display', 'is_published', 'is_active',
            'created_by', 'created_by_info', 'created_at', 'updated_at',
            'is_available', 'is_overdue', 'total_submissions',
            'graded_submissions', 'average_score'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'is_available', 'is_overdue',
            'total_submissions', 'graded_submissions', 'average_score'
        ]
    
    def get_course_info(self, obj):
        """Get course information"""
        return {
            'id': str(obj.course.id),
            'title': obj.course.title,
            'slug': obj.course.slug,
        }
    
    def get_lesson_info(self, obj):
        """Get lesson information"""
        if obj.lesson:
            return {
                'id': str(obj.lesson.id),
                'title': obj.lesson.title,
                'slug': obj.lesson.slug,
            }
        return None
    
    def get_created_by_info(self, obj):
        """Get created by information"""
        if obj.created_by:
            return {
                'id': str(obj.created_by.id),
                'email': obj.created_by.email,
                'full_name': obj.created_by.full_name,
            }
        return None
    
    def validate_max_score(self, value):
        """Validate max score"""
        if value <= 0:
            raise serializers.ValidationError("Max score must be greater than 0")
        return value
    
    def validate_passing_score(self, value):
        """Validate passing score"""
        if value < 0:
            raise serializers.ValidationError("Passing score cannot be negative")
        return value
    
    def validate_attempts_allowed(self, value):
        """Validate attempts allowed"""
        if value <= 0:
            raise serializers.ValidationError("Attempts allowed must be greater than 0")
        return value
    
    def validate_duration_minutes(self, value):
        """Validate duration"""
        if value <= 0:
            raise serializers.ValidationError("Duration must be greater than 0")
        return value


class AssignmentQuestionSerializer(serializers.ModelSerializer):
    """
    Serializer for AssignmentQuestion model
    """
    question_type_display = serializers.CharField(source='get_question_type_display', read_only=True)
    
    class Meta:
        model = AssignmentQuestion
        fields = [
            'id', 'assignment', 'question_text', 'question_type',
            'question_type_display', 'question_data', 'points', 'order',
            'is_required', 'explanation', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_points(self, value):
        """Validate points"""
        if value <= 0:
            raise serializers.ValidationError("Points must be greater than 0")
        return value


class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    """
    Serializer for AssignmentSubmission model
    """
    assignment_info = serializers.SerializerMethodField()
    student_info = serializers.SerializerMethodField()
    graded_by_info = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_submitted = serializers.ReadOnlyField()
    is_graded = serializers.ReadOnlyField()
    is_passed = serializers.ReadOnlyField()
    percentage_score = serializers.ReadOnlyField()
    is_late = serializers.ReadOnlyField()
    
    class Meta:
        model = AssignmentSubmission
        fields = [
            'id', 'assignment', 'assignment_info', 'student', 'student_info',
            'answers', 'text_content', 'attached_files', 'score',
            'max_possible_score', 'feedback', 'graded_by', 'graded_by_info',
            'graded_at', 'status', 'status_display', 'submitted_at',
            'last_saved_at', 'time_spent', 'attempt_number', 'is_active',
            'created_at', 'updated_at', 'is_submitted', 'is_graded',
            'is_passed', 'percentage_score', 'is_late'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'graded_at', 'submitted_at',
            'is_submitted', 'is_graded', 'is_passed', 'percentage_score',
            'is_late'
        ]
    
    def get_assignment_info(self, obj):
        """Get assignment information"""
        return {
            'id': str(obj.assignment.id),
            'title': obj.assignment.title,
            'assignment_type': obj.assignment.assignment_type,
            'max_score': obj.assignment.max_score,
            'passing_score': obj.assignment.passing_score,
            'due_date': obj.assignment.due_date,
        }
    
    def get_student_info(self, obj):
        """Get student information"""
        return {
            'id': str(obj.student.id),
            'email': obj.student.email,
            'full_name': obj.student.full_name,
        }
    
    def get_graded_by_info(self, obj):
        """Get graded by information"""
        if obj.graded_by:
            return {
                'id': str(obj.graded_by.id),
                'email': obj.graded_by.email,
                'full_name': obj.graded_by.full_name,
            }
        return None
    
    def validate_score(self, value):
        """Validate score"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Score cannot be negative")
        return value


class AssignmentFileSerializer(serializers.ModelSerializer):
    """
    Serializer for AssignmentFile model
    """
    uploaded_by_info = serializers.SerializerMethodField()
    file_type_display = serializers.CharField(source='get_file_type_display', read_only=True)
    file_size_display = serializers.ReadOnlyField()
    
    class Meta:
        model = AssignmentFile
        fields = [
            'id', 'assignment', 'submission', 'file_type', 'file_type_display',
            'title', 'description', 'file', 'file_size', 'file_type_detected',
            'uploaded_by', 'uploaded_by_info', 'uploaded_at', 'is_active',
            'file_size_display'
        ]
        read_only_fields = ['uploaded_at', 'file_size', 'file_size_display']
    
    def get_uploaded_by_info(self, obj):
        """Get uploaded by information"""
        if obj.uploaded_by:
            return {
                'id': str(obj.uploaded_by.id),
                'email': obj.uploaded_by.email,
                'full_name': obj.uploaded_by.full_name,
            }
        return None


class AssignmentCreateSerializer(serializers.Serializer):
    """
    Serializer for creating assignments
    """
    title = serializers.CharField(max_length=300)
    description = serializers.CharField()
    instructions = serializers.CharField()
    assignment_type = serializers.ChoiceField(choices=Assignment.ASSIGNMENT_TYPES)
    course_id = serializers.UUIDField(write_only=True)
    lesson_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    max_score = serializers.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    passing_score = serializers.DecimalField(max_digits=5, decimal_places=2, default=60.00)
    duration_minutes = serializers.IntegerField(default=60)
    attempts_allowed = serializers.IntegerField(default=3)
    randomize_questions = serializers.BooleanField(default=False)
    allow_late_submission = serializers.BooleanField(default=False)
    available_from = serializers.DateTimeField()
    available_until = serializers.DateTimeField()
    due_date = serializers.DateTimeField()
    grace_period = serializers.DurationField(default=timezone.timedelta(0))


class AssignmentPublishSerializer(serializers.Serializer):
    """
    Serializer for publishing assignments
    """
    pass


class AssignmentCloseSerializer(serializers.Serializer):
    """
    Serializer for closing assignments
    """
    pass


class AssignmentQuestionCreateSerializer(serializers.Serializer):
    """
    Serializer for creating assignment questions
    """
    assignment_id = serializers.UUIDField(write_only=True)
    question_text = serializers.CharField()
    question_type = serializers.ChoiceField(choices=AssignmentQuestion.QUESTION_TYPES)
    question_data = serializers.JSONField(default=dict)
    points = serializers.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    order = serializers.IntegerField(default=0)
    is_required = serializers.BooleanField(default=True)
    explanation = serializers.CharField(required=False, allow_blank=True)


class AssignmentQuestionReorderSerializer(serializers.Serializer):
    """
    Serializer for reordering assignment questions
    """
    question_orders = serializers.JSONField()


class AssignmentSubmissionCreateSerializer(serializers.Serializer):
    """
    Serializer for creating assignment submissions
    """
    assignment_id = serializers.UUIDField(write_only=True)
    attempt_number = serializers.IntegerField(default=1)


class AssignmentSubmissionUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating assignment submissions
    """
    answers = serializers.JSONField(required=False)
    text_content = serializers.CharField(required=False, allow_blank=True)
    attached_files = serializers.JSONField(required=False)


class AssignmentSubmissionGradeSerializer(serializers.Serializer):
    """
    Serializer for grading assignment submissions
    """
    score = serializers.DecimalField(max_digits=5, decimal_places=2)
    feedback = serializers.CharField(required=False, allow_blank=True)


class AssignmentFileUploadSerializer(serializers.Serializer):
    """
    Serializer for uploading assignment files
    """
    assignment_id = serializers.UUIDField(write_only=True, required=False)
    submission_id = serializers.UUIDField(write_only=True, required=False)
    title = serializers.CharField(max_length=200)
    file = serializers.FileField()


class AssignmentStatisticsSerializer(serializers.Serializer):
    """
    Serializer for assignment statistics
    """
    total_submissions = serializers.IntegerField(read_only=True)
    submitted_submissions = serializers.IntegerField(read_only=True)
    graded_submissions = serializers.IntegerField(read_only=True)
    passed_submissions = serializers.IntegerField(read_only=True)
    failed_submissions = serializers.IntegerField(read_only=True)
    average_score = serializers.FloatField(read_only=True)
    pass_rate = serializers.FloatField(read_only=True)
    late_submissions = serializers.IntegerField(read_only=True)


class AssignmentQuestionStatisticsSerializer(serializers.Serializer):
    """
    Serializer for assignment question statistics
    """
    total_attempts = serializers.IntegerField(read_only=True)
    correct_answers = serializers.IntegerField(read_only=True)
    incorrect_answers = serializers.IntegerField(read_only=True)
    success_rate = serializers.FloatField(read_only=True)
