from django.db import models, transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Assignment, AssignmentQuestion, AssignmentSubmission, AssignmentFile


class AssignmentService:
    """
    Service layer for Assignment business logic
    """
    
    @staticmethod
    def create_assignment(data, creator=None):
        """Create new assignment with validation"""
        # Validate permissions
        if creator and not creator.is_admin_or_above():
            raise ValidationError("Only admins can create assignments")
        
        # Validate course belongs to same organization
        course = data.get('course')
        if course and course.organization != creator.organization:
            raise ValidationError("Course must belong to same organization")
        
        # Validate lesson belongs to same course
        lesson = data.get('lesson')
        if lesson and lesson.module.course != course:
            raise ValidationError("Lesson must belong to same course")
        
        assignment = Assignment.objects.create(**data)
        
        # Log assignment creation
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=creator,
            action='ASSIGNMENT_CREATE',
            details={
                'assignment': str(assignment.id),
                'course': str(course.id),
                'title': assignment.title,
                'assignment_type': assignment.assignment_type,
            },
            ip_address=creator.last_login_ip
        )
        
        return assignment
    
    @staticmethod
    def publish_assignment(assignment, published_by=None):
        """Publish assignment"""
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
                'assignment': str(assignment.id),
                'title': assignment.title,
            },
            ip_address=published_by.last_login_ip
        )
    
    @staticmethod
    def close_assignment(assignment, closed_by=None):
        """Close assignment"""
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
                'assignment': str(assignment.id),
                'title': assignment.title,
            },
            ip_address=closed_by.last_login_ip
        )
    
    @staticmethod
    def get_assignment_statistics(assignment):
        """Get comprehensive assignment statistics"""
        submissions = assignment.submissions.filter(is_active=True)
        
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
    def duplicate_assignment(assignment, creator=None):
        """Duplicate assignment with questions"""
        with transaction.atomic():
            # Create new assignment
            new_assignment = Assignment.objects.create(
                title=f"{assignment.title} (Copy)",
                description=assignment.description,
                instructions=assignment.instructions,
                assignment_type=assignment.assignment_type,
                course=assignment.course,
                lesson=assignment.lesson,
                max_score=assignment.max_score,
                passing_score=assignment.passing_score,
                duration_minutes=assignment.duration_minutes,
                attempts_allowed=assignment.attempts_allowed,
                randomize_questions=assignment.randomize_questions,
                allow_late_submission=assignment.allow_late_submission,
                available_from=timezone.now(),
                available_until=timezone.now() + timezone.timedelta(days=30),
                due_date=timezone.now() + timezone.timedelta(days=7),
                grace_period=assignment.grace_period,
                status='DRAFT',
                is_published=False,
                created_by=creator
            )
            
            # Duplicate questions
            for question in assignment.questions.all():
                AssignmentQuestion.objects.create(
                    assignment=new_assignment,
                    question_text=question.question_text,
                    question_type=question.question_type,
                    question_data=question.question_data,
                    points=question.points,
                    order=question.order,
                    is_required=question.is_required,
                    explanation=question.explanation
                )
        
        return new_assignment


class AssignmentQuestionService:
    """
    Service layer for Assignment Question business logic
    """
    
    @staticmethod
    def create_question(data, creator=None):
        """Create new assignment question"""
        # Validate permissions
        if creator and not creator.is_admin_or_above():
            raise ValidationError("Only admins can create assignment questions")
        
        # Validate assignment belongs to same organization
        assignment = data.get('assignment')
        if assignment and assignment.course.organization != creator.organization:
            raise ValidationError("Assignment must belong to same organization")
        
        question = AssignmentQuestion.objects.create(**data)
        return question
    
    @staticmethod
    def reorder_questions(assignment, question_orders, reordered_by=None):
        """Reorder questions in assignment"""
        with transaction.atomic():
            for question_id, new_order in question_orders.items():
                question = AssignmentQuestion.objects.get(id=question_id, assignment=assignment)
                question.order = new_order
                question.save(update_fields=['order'])
        
        # Log reordering
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=reordered_by,
            action='ASSIGNMENT_QUESTION_REORDER',
            details={
                'assignment': str(assignment.id),
                'question_orders': question_orders,
            },
            ip_address=reordered_by.last_login_ip
        )
    
    @staticmethod
    def get_question_statistics(question):
        """Get question statistics"""
        submissions = AssignmentSubmission.objects.filter(
            assignment=question.assignment,
            is_active=True
        )
        
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


class AssignmentSubmissionService:
    """
    Service layer for Assignment Submission business logic
    """
    
    @staticmethod
    def create_submission(student, assignment, attempt_number=1):
        """Create new assignment submission"""
        # Validate student can submit
        if not assignment.is_available:
            raise ValidationError("Assignment is not available for submission")
        
        # Check attempts limit
        existing_submissions = AssignmentSubmission.objects.filter(
            assignment=assignment,
            student=student,
            is_active=True
        ).count()
        
        if existing_submissions >= assignment.attempts_allowed:
            raise ValidationError("Maximum attempts reached")
        
        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=student,
            attempt_number=attempt_number,
            max_possible_score=assignment.max_score
        )
        
        # Log submission creation
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=student,
            action='ASSIGNMENT_SUBMISSION_CREATE',
            details={
                'submission': str(submission.id),
                'assignment': str(assignment.id),
                'attempt': attempt_number,
            },
            ip_address=student.last_login_ip
        )
        
        return submission
    
    @staticmethod
    def update_submission(submission, answers=None, text_content=None, attached_files=None, updated_by=None):
        """Update assignment submission"""
        if submission.status == 'SUBMITTED':
            raise ValidationError("Cannot update submitted assignment")
        
        if answers is not None:
            submission.answers = answers
        
        if text_content is not None:
            submission.text_content = text_content
        
        if attached_files is not None:
            submission.attached_files = attached_files
        
        submission.last_saved_at = timezone.now()
        submission.save(update_fields=['answers', 'text_content', 'attached_files', 'last_saved_at'])
        
        # Log update
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=updated_by or submission.student,
            action='ASSIGNMENT_SUBMISSION_UPDATE',
            details={
                'submission': str(submission.id),
                'assignment': str(submission.assignment.id),
            },
            ip_address=(updated_by or submission.student).last_login_ip
        )
        
        return submission
    
    @staticmethod
    def submit_assignment(submission, submitted_by=None):
        """Submit assignment"""
        submission.submit(submitted_by)
        return submission
    
    @staticmethod
    def grade_submission(submission, score, feedback=None, graded_by=None):
        """Grade assignment submission"""
        submission.grade(score, feedback, graded_by)
        return submission
    
    @staticmethod
    def auto_grade_submission(submission):
        """Auto-grade submission based on correct answers"""
        assignment = submission.assignment
        total_score = 0
        max_score = 0
        
        for question in assignment.questions.all():
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
    def get_submission_statistics(submission):
        """Get submission statistics"""
        return {
            'score': float(submission.score) if submission.score else 0,
            'max_possible_score': float(submission.max_possible_score),
            'percentage_score': submission.percentage_score,
            'is_passed': submission.is_passed,
            'is_late': submission.is_late,
            'time_spent': submission.time_spent,
            'attempt_number': submission.attempt_number,
        }


class AssignmentFileService:
    """
    Service layer for Assignment File business logic
    """
    
    @staticmethod
    def upload_file(assignment=None, submission=None, file=None, title=None, uploaded_by=None):
        """Upload file to assignment or submission"""
        if not assignment and not submission:
            raise ValidationError("Either assignment or submission must be provided")
        
        if assignment and submission:
            raise ValidationError("Cannot attach file to both assignment and submission")
        
        # Determine file type
        file_type = 'ASSIGNMENT' if assignment else 'SUBMISSION'
        
        # Create file record
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
                'file': str(assignment_file.id),
                'title': assignment_file.title,
                'file_type': file_type,
                'assignment': str(assignment.id) if assignment else None,
                'submission': str(submission.id) if submission else None,
            },
            ip_address=uploaded_by.last_login_ip
        )
        
        return assignment_file
    
    @staticmethod
    def delete_file(assignment_file, deleted_by=None):
        """Delete assignment file"""
        if assignment_file.file:
            assignment_file.file.delete()
        
        assignment_file.delete()
        
        # Log file deletion
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=deleted_by,
            action='ASSIGNMENT_FILE_DELETE',
            details={
                'file': str(assignment_file.id),
                'title': assignment_file.title,
            },
            ip_address=deleted_by.last_login_ip
        )
