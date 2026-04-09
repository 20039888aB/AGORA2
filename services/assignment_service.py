"""
Assignment Service - Centralized Assignment Business Logic

This service contains all assignment-related business logic that should be used
instead of putting logic directly in models or views.
"""

from django.db import models, transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db.models import Q, Avg, Count, Sum
import uuid

User = get_user_model()


class AssignmentService:
    """
    Service layer for Assignment business logic
    """
    
    @staticmethod
    def create_assignment(data, creator=None):
        """
        Create new assignment with validation and business logic
        """
        # Extract and validate required fields
        title = data.get('title')
        course = data.get('course')
        
        if not title:
            raise ValidationError("Assignment title is required")
        if not course:
            raise ValidationError("Course is required")
        
        # Validate permissions
        if creator and not creator.is_admin_or_above():
            raise ValidationError("Only admins can create assignments")
        
        # Validate course belongs to same organization
        if course.organization != creator.organization:
            raise ValidationError("Course must belong to same organization")
        
        # Validate lesson belongs to same course
        lesson = data.get('lesson')
        if lesson and lesson.module.course != course:
            raise ValidationError("Lesson must belong to same course")
        
        # Check if assignment already exists in course
        from assignments.models import Assignment
        if Assignment.objects.filter(course=course, title=title).exists():
            raise ValidationError("Assignment with this title already exists in this course")
        
        # Create assignment
        assignment = Assignment.objects.create(
            title=title,
            description=data.get('description', ''),
            instructions=data.get('instructions', ''),
            assignment_type=data.get('assignment_type', 'ESSAY'),
            course=course,
            lesson=lesson,
            max_score=data.get('max_score', 100.00),
            passing_score=data.get('passing_score', 60.00),
            duration_minutes=data.get('duration_minutes', 60),
            attempts_allowed=data.get('attempts_allowed', 3),
            randomize_questions=data.get('randomize_questions', False),
            allow_late_submission=data.get('allow_late_submission', False),
            available_from=data.get('available_from'),
            available_until=data.get('available_until'),
            due_date=data.get('due_date'),
            grace_period=data.get('grace_period', timezone.timedelta(0)),
            created_by=creator
        )
        
        # Log assignment creation
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=creator,
            action='ASSIGNMENT_CREATE',
            details={
                'assignment_id': str(assignment.id),
                'title': assignment.title,
                'course_id': str(course.id),
                'assignment_type': assignment.assignment_type
            },
            ip_address=creator.last_login_ip if creator else None
        )
        
        return assignment
    
    @staticmethod
    def publish_assignment(assignment, published_by=None):
        """
        Publish assignment
        """
        if assignment.status != 'DRAFT':
            raise ValidationError("Only draft assignments can be published")
        
        assignment.status = 'PUBLISHED'
        assignment.is_published = True
        assignment.save(update_fields=['status', 'is_published'])
        
        # Log assignment publication
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=published_by,
            action='ASSIGNMENT_PUBLISH',
            details={
                'assignment_id': str(assignment.id),
                'title': assignment.title
            },
            ip_address=published_by.last_login_ip if published_by else None
        )
        
        return assignment
    
    @staticmethod
    def close_assignment(assignment, closed_by=None):
        """
        Close assignment
        """
        if assignment.status == 'CLOSED':
            raise ValidationError("Assignment is already closed")
        
        assignment.status = 'CLOSED'
        assignment.save(update_fields=['status'])
        
        # Log assignment closure
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=closed_by,
            action='ASSIGNMENT_CLOSE',
            details={
                'assignment_id': str(assignment.id),
                'title': assignment.title
            },
            ip_address=closed_by.last_login_ip if closed_by else None
        )
        
        return assignment
    
    @staticmethod
    def create_question(assignment, data, creator=None):
        """
        Create new assignment question
        """
        # Validate permissions
        if creator and not creator.is_admin_or_above():
            raise ValidationError("Only admins can create assignment questions")
        
        # Validate assignment belongs to same organization
        if assignment.course.organization != creator.organization:
            raise ValidationError("Assignment must belong to same organization")
        
        # Create question
        from assignments.models import AssignmentQuestion
        question = AssignmentQuestion.objects.create(
            assignment=assignment,
            question_text=data.get('question_text', ''),
            question_type=data.get('question_type', 'MULTIPLE_CHOICE'),
            question_data=data.get('question_data', {}),
            points=data.get('points', 10.00),
            order=data.get('order', 0),
            is_required=data.get('is_required', True),
            explanation=data.get('explanation', '')
        )
        
        # Log question creation
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=creator,
            action='ASSIGNMENT_QUESTION_CREATE',
            details={
                'question_id': str(question.id),
                'assignment_id': str(assignment.id),
                'question_type': question.question_type
            },
            ip_address=creator.last_login_ip if creator else None
        )
        
        return question
    
    @staticmethod
    def create_submission(student, assignment, attempt_number=1, created_by=None):
        """
        Create new assignment submission
        """
        # Validate student can submit
        if not assignment.is_available:
            raise ValidationError("Assignment is not available for submission")
        
        # Check attempts limit
        from assignments.models import AssignmentSubmission
        existing_submissions = AssignmentSubmission.objects.filter(
            assignment=assignment,
            student=student,
            is_active=True
        ).count()
        
        if existing_submissions >= assignment.attempts_allowed:
            raise ValidationError("Maximum attempts reached")
        
        # Create submission
        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=student,
            attempt_number=attempt_number,
            max_possible_score=assignment.max_score
        )
        
        # Log submission creation
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=created_by or student,
            action='ASSIGNMENT_SUBMISSION_CREATE',
            details={
                'submission_id': str(submission.id),
                'assignment_id': str(assignment.id),
                'attempt': attempt_number
            },
            ip_address=(created_by or student).last_login_ip
        )
        
        return submission
    
    @staticmethod
    def submit_assignment(submission, submitted_by=None):
        """
        Submit assignment
        """
        if submission.status == 'SUBMITTED':
            raise ValidationError("Assignment is already submitted")
        
        if not submission.assignment.is_available:
            raise ValidationError("Assignment is not available for submission")
        
        submission.status = 'SUBMITTED'
        submission.submitted_at = timezone.now()
        submission.save(update_fields=['status', 'submitted_at'])
        
        # Log submission
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=submitted_by or submission.student,
            action='ASSIGNMENT_SUBMIT',
            details={
                'submission_id': str(submission.id),
                'assignment_id': str(submission.assignment.id),
                'attempt': submission.attempt_number
            },
            ip_address=(submitted_by or submission.student).last_login_ip
        )
        
        return submission
    
    @staticmethod
    def grade_submission(submission, score, feedback=None, graded_by=None):
        """
        Grade assignment submission
        """
        if score < 0 or score > submission.max_possible_score:
            raise ValidationError("Score must be between 0 and max possible score")
        
        submission.score = score
        submission.feedback = feedback or ''
        submission.graded_by = graded_by
        submission.graded_at = timezone.now()
        submission.status = 'GRADED'
        submission.save(update_fields=['score', 'feedback', 'graded_by', 'graded_at', 'status'])
        
        # Log grading
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=graded_by,
            action='ASSIGNMENT_GRADE',
            details={
                'submission_id': str(submission.id),
                'assignment_id': str(submission.assignment.id),
                'score': float(score),
                'feedback': feedback
            },
            ip_address=graded_by.last_login_ip if graded_by else None
        )
        
        return submission
    
    @staticmethod
    def auto_grade_submission(submission):
        """
        Auto-grade submission based on correct answers
        """
        assignment = submission.assignment
        total_score = 0
        max_score = 0
        
        from assignments.models import AssignmentQuestion
        for question in AssignmentQuestion.objects.filter(assignment=assignment):
            if str(question.id) in submission.answers:
                answer = submission.answers[str(question.id)]
                correct_answer = question.question_data.get('correct_answer')
                
                if answer == correct_answer:
                    total_score += question.points
                
                max_score += question.points
        
        submission.score = total_score
        submission.max_possible_score = max_score
        submission.status = 'GRADED'
        submission.graded_at = timezone.now()
        submission.save(update_fields=['score', 'max_possible_score', 'status', 'graded_at'])
        
        return submission
    
    @staticmethod
    def upload_file(assignment=None, submission=None, file=None, title=None, uploaded_by=None):
        """
        Upload file to assignment or submission
        """
        if not assignment and not submission:
            raise ValidationError("Either assignment or submission must be provided")
        
        if assignment and submission:
            raise ValidationError("Cannot attach file to both assignment and submission")
        
        # Determine file type
        file_type = 'ASSIGNMENT' if assignment else 'SUBMISSION'
        
        # Create file record
        from assignments.models import AssignmentFile
        assignment_file = AssignmentFile.objects.create(
            assignment=assignment,
            submission=submission,
            file_type=file_type,
            title=title or file.name,
            file=file,
            uploaded_by=uploaded_by
        )
        
        # Log file upload
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=uploaded_by,
            action='ASSIGNMENT_FILE_UPLOAD',
            details={
                'file_id': str(assignment_file.id),
                'title': assignment_file.title,
                'file_type': file_type,
                'assignment_id': str(assignment.id) if assignment else None,
                'submission_id': str(submission.id) if submission else None
            },
            ip_address=uploaded_by.last_login_ip if uploaded_by else None
        )
        
        return assignment_file
    
    @staticmethod
    def get_assignment_statistics(assignment):
        """
        Get comprehensive assignment statistics
        """
        from assignments.models import AssignmentSubmission
        submissions = AssignmentSubmission.objects.filter(assignment=assignment, is_active=True)
        
        return {
            'total_submissions': submissions.count(),
            'submitted_submissions': submissions.filter(status='SUBMITTED').count(),
            'graded_submissions': submissions.filter(status='GRADED').count(),
            'passed_submissions': submissions.filter(
                status='GRADED',
                score__gte=assignment.passing_score
            ).count(),
            'failed_submissions': submissions.filter(
                status='GRADED',
                score__lt=assignment.passing_score
            ).count(),
            'average_score': assignment.average_score,
            'pass_rate': (submissions.filter(
                status='GRADED',
                score__gte=assignment.passing_score
            ).count() / submissions.filter(status='GRADED').count() * 100) if submissions.filter(status='GRADED').exists() else 0,
            'late_submissions': submissions.filter(
                submitted_at__gt=assignment.due_date + assignment.grace_period
            ).count(),
        }
    
    @staticmethod
    def get_question_statistics(question):
        """
        Get question statistics
        """
        from assignments.models import AssignmentSubmission
        submissions = AssignmentSubmission.objects.filter(assignment=question.assignment, is_active=True)
        
        correct_answers = 0
        total_answers = 0
        
        for submission in submissions:
            if submission.answers and str(question.id) in submission.answers:
                answer = submission.answers[str(question.id)]
                if question.question_data.get('correct_answer') == answer:
                    correct_answers += 1
                total_answers += 1
        
        return {
            'total_attempts': total_answers,
            'correct_answers': correct_answers,
            'incorrect_answers': total_answers - correct_answers,
            'success_rate': (correct_answers / total_answers * 100) if total_answers > 0 else 0,
        }
    
    @staticmethod
    def get_course_assignments(course, status=None, assignment_type=None):
        """
        Get course assignments with filters
        """
        from assignments.models import Assignment
        assignments = Assignment.objects.filter(course=course, is_active=True)
        
        if status:
            assignments = assignments.filter(status=status)
        
        if assignment_type:
            assignments = assignments.filter(assignment_type=assignment_type)
        
        return assignments
    
    @staticmethod
    def get_user_assignments(user, status=None):
        """
        Get user assignments based on role
        """
        from assignments.models import Assignment
        assignments = Assignment.objects.filter(is_active=True)
        
        if user.is_superadmin():
            return assignments
        
        elif user.is_admin():
            return assignments.filter(course__organization=user.organization)
        
        elif user.is_manager():
            return assignments.filter(course__instructor=user)
        
        elif user.is_student():
            # Get assignments from courses user is enrolled in
            from enrollments.models import Enrollment
            course_ids = Enrollment.objects.filter(
                user=user,
                status='ACTIVE',
                is_active=True
            ).values_list('course_id', flat=True)
            return assignments.filter(course_id__in=course_ids)
        
        return Assignment.objects.none()
    
    @staticmethod
    def get_user_submissions(user, status=None):
        """
        Get user's assignment submissions
        """
        from assignments.models import AssignmentSubmission
        submissions = AssignmentSubmission.objects.filter(student=user, is_active=True)
        
        if status:
            submissions = submissions.filter(status=status)
        
        return submissions
    
    @staticmethod
    def validate_assignment_access(user, assignment, action='view'):
        """
        Validate if user has access to assignment
        """
        if user.is_superadmin():
            return True
        
        if assignment.course.organization != user.organization:
            return False
        
        if action == 'view':
            return True
        
        if action in ['edit', 'delete', 'publish', 'close']:
            return user.is_admin_or_above() or assignment.course.instructor == user
        
        if action == 'submit':
            return user.is_student() and assignment.is_available
        
        if action == 'grade':
            return user.is_admin_or_above() or assignment.course.instructor == user
        
        return False
    
    @staticmethod
    def get_pending_grading(organization=None, limit=50):
        """
        Get assignments pending grading
        """
        from assignments.models import AssignmentSubmission
        submissions = AssignmentSubmission.objects.filter(
            status='SUBMITTED',
            is_active=True
        )
        
        if organization:
            submissions = submissions.filter(
                assignment__course__organization=organization
            )
        
        return submissions.order_by('submitted_at')[:limit]
    
    @staticmethod
    def search_assignments(query, organization=None, user=None):
        """
        Search assignments by title, description, or instructions
        """
        from assignments.models import Assignment
        assignments = Assignment.objects.filter(is_active=True)
        
        if organization:
            assignments = assignments.filter(course__organization=organization)
        
        if user and not user.is_superadmin():
            assignments = assignments.filter(course__organization=user.organization)
        
        if query:
            assignments = assignments.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(instructions__icontains=query)
            )
        
        return assignments.distinct()
