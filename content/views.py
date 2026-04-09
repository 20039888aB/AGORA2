from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q, Count, Sum
from datetime import timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework import permissions
from rest_framework.response import Response
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
import logging

logger = logging.getLogger(__name__)


@login_required
def content_upload(request):
    """
    Content upload page for managers and admins
    """
    user = request.user
    
    # Check permissions
    if not (user.is_manager_or_above() or user.is_admin_or_above()):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    context = {
        'user': user,
        'page_title': 'Upload Content',
    }
    
    return render(request, 'content/upload.html', context)


@login_required
def content_organize(request):
    """
    Content organization page for managers and admins
    """
    user = request.user
    
    # Check permissions
    if not (user.is_manager_or_above() or user.is_admin_or_above()):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    context = {
        'user': user,
        'page_title': 'Organize Content',
    }
    
    return render(request, 'content/organize.html', context)


@login_required
def content_approve(request):
    """
    Content approval page for admins
    """
    user = request.user
    
    # Check permissions - only admins can approve content
    if not user.is_admin_or_above():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    try:
        from courses.models import Course

        if request.method == 'POST':
            action = request.POST.get('action')
            course_id = request.POST.get('course_id')

            course = get_object_or_404(Course, id=course_id)

            if not user.is_superadmin() and user.organization and course.organization != user.organization:
                messages.error(request, 'You do not have permission to review this course.')
                return redirect('content:content_approve')

            uploader_role = getattr(getattr(course, 'instructor', None), 'role', None)
            if uploader_role != 'MANAGER':
                messages.error(request, 'Only manager-uploaded courses can be reviewed here.')
                return redirect('content:content_approve')

            if action == 'approve':
                course.status = 'PUBLISHED'
                course.save(update_fields=['status', 'updated_at'])
                messages.success(request, f'Course "{course.title}" approved successfully.')
            elif action == 'reject':
                course.status = 'ARCHIVED'
                course.save(update_fields=['status', 'updated_at'])
                messages.success(request, f'Course "{course.title}" rejected and archived.')
            else:
                messages.error(request, 'Invalid action.')

            return redirect('content:content_approve')

        pending_courses = Course.objects.select_related('organization', 'instructor').filter(
            is_active=True,
            status='DRAFT',
            instructor__role='MANAGER'
        )
        reviewed_courses = Course.objects.select_related('organization', 'instructor').filter(
            is_active=True,
            instructor__role='MANAGER',
            status__in=['PUBLISHED', 'ARCHIVED']
        ).order_by('-updated_at')

        if not user.is_superadmin() and user.organization:
            pending_courses = pending_courses.filter(organization=user.organization)
            reviewed_courses = reviewed_courses.filter(organization=user.organization)

        pending_count = pending_courses.count()
        approved_today = reviewed_courses.filter(
            status='PUBLISHED',
            updated_at__date=timezone.now().date()
        ).count()
        rejected_count = reviewed_courses.filter(status='ARCHIVED').count()

        context = {
            'user': user,
            'page_title': 'Approve Content',
            'pending_courses': pending_courses.order_by('-created_at'),
            'reviewed_courses': reviewed_courses[:25],
            'pending_count': pending_count,
            'approved_today': approved_today,
            'rejected_count': rejected_count,
        }
    except ImportError:
        context = {
            'user': user,
            'page_title': 'Approve Content',
            'pending_courses': [],
            'reviewed_courses': [],
            'pending_count': 0,
            'approved_today': 0,
            'rejected_count': 0,
        }

    return render(request, 'content/approve.html', context)


class ContentBrowseView(LoginRequiredMixin, TemplateView):
    """
    Browse available courses and content
    """
    template_name = 'content/browse.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['user'] = user
        context['page_title'] = 'Browse Courses'
        
        # Get real course data
        try:
            from courses.models import Course
            from enrollments.models import Enrollment as CourseEnrollment
            
            # Get courses based on user's organization
            if user.organization:
                courses = Course.objects.filter(organization=user.organization)
            else:
                courses = Course.objects.all()
            
            # Add enrollment status and progress for each course
            course_data = []
            for course in courses:
                # Check if user is enrolled
                enrollment = CourseEnrollment.objects.filter(user=user, course=course).first()
                is_enrolled = enrollment is not None
                is_completed = enrollment and enrollment.status == 'COMPLETED'
                
                progress_percentage = float(enrollment.progress_percentage) if enrollment else 0
                
                course_data.append({
                    'id': course.id,
                    'title': course.title,
                    'description': course.description or '',
                    'instructor': course.instructor,
                    'duration': course.duration,
                    'level': course.level,
                    'is_enrolled': is_enrolled,
                    'is_completed': is_completed,
                    'progress_percentage': int(progress_percentage),
                    'enrollment_date': enrollment.created_at if enrollment else None,
                })
            
            context['courses'] = course_data
            
        except ImportError:
            # Fallback if courses app is not available
            context['courses'] = []
        
        return context


@login_required
def course_create_view(request):
    """
    Course creation page for admins and managers
    """
    user = request.user
    
    # Check permissions
    if not user.is_manager_or_above():
        messages.error(request, 'You do not have permission to create courses.')
        return redirect('dashboard')
    
    context = {
        'user': user,
        'page_title': 'Create Course',
    }
    
    if request.method == 'POST':
        try:
            from courses.models import Course
            from django.core.files.storage import default_storage
            from django.utils.text import slugify
            import os
            
            # Validate required fields
            title = request.POST.get('title', '').strip()
            description = request.POST.get('full_description', '').strip()
            duration = request.POST.get('duration', '0')
            max_students = request.POST.get('max_students', '50')
            difficulty = request.POST.get('difficulty', 'beginner')
            
            if not title:
                messages.error(request, 'Course title is required.')
                return render(request, 'courses/create.html', context)
            
            if not description:
                messages.error(request, 'Course description is required.')
                return render(request, 'courses/create.html', context)
            
            # Validate numeric fields
            try:
                duration = float(duration)
                if duration <= 0:
                    messages.error(request, 'Duration must be greater than 0.')
                    return render(request, 'courses/create.html', context)
            except ValueError:
                messages.error(request, 'Invalid duration value.')
                return render(request, 'courses/create.html', context)
            
            try:
                max_students = int(max_students)
                if max_students <= 0:
                    messages.error(request, 'Max students must be greater than 0.')
                    return render(request, 'courses/create.html', context)
            except ValueError:
                messages.error(request, 'Invalid max students value.')
                return render(request, 'courses/create.html', context)
            
            # Handle category properly
            category_value = request.POST.get('category')
            category = None
            if category_value and category_value != '':
                try:
                    from courses.models import Category
                    category = Category.objects.filter(
                        slug=category_value,
                        organization=user.organization
                    ).first()
                    # If no category found with that slug, try to create one
                    if not category:
                        category = Category.objects.create(
                            name=category_value.title(),
                            slug=category_value,
                            organization=user.organization
                        )
                except ImportError:
                    # If Category model doesn't exist, set to None
                    category = None

            # Generate unique slug for the course
            base_slug = slugify(title)
            unique_slug = base_slug
            counter = 1

            # Ensure slug is unique within the organization
            while Course.objects.filter(slug=unique_slug, organization=user.organization).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1

            # Create course with organization-based access and PDF support
            course = Course.objects.create(
                title=title,
                slug=unique_slug,  # Use the unique slug
                description=description,
                short_description=request.POST.get('short_description', '').strip(),
                category=category,  # Now properly handled
                difficulty=difficulty,
                duration_hours=duration,
                max_students=max_students,
                status='PUBLISHED' if user.is_admin_or_above() else 'DRAFT',
                certificate_enabled=True,  # Default to enabled since field was removed
                price=0.00,  # Default to free since price field was removed
                organization=user.organization,  # Organization-based access control
                instructor=user,
                visibility='ORGANIZATION',  # Default to organization-wide visibility
                show_in_dashboard=True,  # Show in dashboards by default
                allow_organization_access=True,  # Allow organization access by default
            )
            
            # Handle main course PDF upload
            course_pdf = request.FILES.get('course_pdf')
            if course_pdf and course_pdf.name.endswith('.pdf'):
                course.course_pdf = course_pdf
                course.pdf_title = request.POST.get('pdf_title', f'{course.title} - Course Material')
                course.pdf_description = request.POST.get('pdf_description', 'Main course PDF document')
                course.save(update_fields=['course_pdf', 'pdf_title', 'pdf_description'])
            
            # Handle additional PDF document uploads
            uploaded_files = request.FILES.getlist('course_documents')
            for uploaded_file in uploaded_files:
                if uploaded_file.name.endswith('.pdf'):
                    # Create unique filename
                    filename = f"course_{course.id}_{uploaded_file.name}"
                    
                    # Save to course documents folder
                    file_path = default_storage.save(f'course_documents/{filename}', uploaded_file)
                    
                    # Create CourseDocument record
                    try:
                        from courses.models import CourseDocument
                        CourseDocument.objects.create(
                            course=course,
                            title=uploaded_file.name.replace('.pdf', ''),
                            file=file_path,
                            file_type='PDF',
                            category='READING',
                            is_required=True,
                            is_downloadable=True,
                            is_printable=True,
                            access_level='ENROLLED'
                        )
                    except ImportError:
                        pass
            
            messages.success(request, f'🎉 Course "{course.title}" created successfully! Your course has been set up with {len(uploaded_files) + (1 if course_pdf else 0)} PDF document(s) and is now ready for students. You can view and manage your course from the course details page.')
            return redirect('content:course_detail', course_id=course.id)
            
        except Exception as e:
            messages.error(request, f'Error creating course: {str(e)}')
    
    context = {
        'user': user,
        'page_title': 'Create Course',
    }
    
    return render(request, 'courses/create.html', context)


@login_required
def course_edit_view(request, course_id):
    """
    Course edit page for admins and managers
    """
    user = request.user
    
    try:
        from courses.models import Course
        
        # Get course
        course = Course.objects.get(id=course_id)
        
        # Check permissions - managers can edit courses from their organization
        if not user.is_manager_or_above():
            messages.error(request, 'You do not have permission to edit courses.')
            return redirect('dashboard')
        
        # Check organization access
        if not user.is_superadmin() and course.organization != user.organization:
            messages.error(request, 'You do not have permission to edit this course.')
            return redirect('content:courses_browse')
        
        context = {
            'user': user,
            'course': course,
            'page_title': f'Edit Course - {course.title}',
        }
        
        return render(request, 'courses/edit.html', context)
        
    except Course.DoesNotExist:
        messages.error(request, 'Course not found.')
        return redirect('content:courses_browse')
    except Exception as e:
        messages.error(request, f'Error loading course: {str(e)}')
        return redirect('content:courses_browse')


@login_required
def course_update_view(request, course_id):
    """
    Handle course update for admins and managers
    """
    user = request.user
    
    try:
        from courses.models import Course
        from django.utils.text import slugify
        
        # Get course
        course = Course.objects.get(id=course_id)
        
        # Check permissions - managers can update courses from their organization
        if not user.is_manager_or_above():
            messages.error(request, 'You do not have permission to update courses.')
            return redirect('dashboard')
        
        # Check organization access
        if not user.is_superadmin() and course.organization != user.organization:
            messages.error(request, 'You do not have permission to update this course.')
            return redirect('content:courses_browse')
        
        if request.method == 'POST':
            # Validate required fields
            title = request.POST.get('title', '').strip()
            description = request.POST.get('full_description', '').strip()
            duration = request.POST.get('duration', '0')
            max_students = request.POST.get('max_students', '50')
            difficulty = request.POST.get('difficulty', 'beginner')
            status = request.POST.get('status', 'DRAFT')
            
            if not title:
                messages.error(request, 'Course title is required.')
                return redirect('content:course_edit', course_id=course.id)
            
            if not description:
                messages.error(request, 'Course description is required.')
                return redirect('content:course_edit', course_id=course.id)
            
            # Validate numeric fields
            try:
                duration = float(duration)
                if duration <= 0:
                    messages.error(request, 'Duration must be greater than 0.')
                    return redirect('content:course_edit', course_id=course.id)
            except ValueError:
                messages.error(request, 'Invalid duration value.')
                return redirect('content:course_edit', course_id=course.id)
            
            try:
                max_students = int(max_students)
                if max_students <= 0:
                    messages.error(request, 'Max students must be greater than 0.')
                    return redirect('content:course_edit', course_id=course.id)
            except ValueError:
                messages.error(request, 'Invalid max students value.')
                return redirect('content:course_edit', course_id=course.id)
            
            # Handle category
            category_value = request.POST.get('category')
            category = None
            if category_value and category_value != '':
                try:
                    from courses.models import Category
                    category = Category.objects.filter(
                        slug=category_value,
                        organization=user.organization
                    ).first()
                    if not category:
                        category = Category.objects.create(
                            name=category_value.title(),
                            slug=category_value,
                            organization=user.organization
                        )
                except ImportError:
                    category = None
            
            # Update slug if title changed
            if title != course.title:
                base_slug = slugify(title)
                unique_slug = base_slug
                counter = 1
                
                # Ensure slug is unique within the organization
                org_courses = Course.objects.filter(organization=course.organization)
                while org_courses.filter(slug=unique_slug).exclude(id=course.id).exists():
                    unique_slug = f"{base_slug}-{counter}"
                    counter += 1
                course.slug = unique_slug
            
            # Update course
            course.title = title
            course.description = description
            course.short_description = request.POST.get('short_description', '').strip()
            course.category = category
            course.difficulty = difficulty
            course.duration_hours = duration
            course.max_students = max_students
            if user.is_admin_or_above():
                course.status = status
            else:
                course.status = 'DRAFT'
            course.prerequisites = request.POST.get('prerequisites', '').strip()
            course.objectives = request.POST.get('objectives', '').strip()
            course.outcomes = request.POST.get('outcomes', '').strip()
            course.language = request.POST.get('language', 'en')
            course.certificate_enabled = request.POST.get('certificate_enabled') == 'on'
            course.is_featured = request.POST.get('is_featured') == 'on'
            course.save()
            
            messages.success(request, f'🎉 Course "{course.title}" updated successfully!')
            return redirect('content:course_detail', course_id=course.id)
        
        # If not POST, redirect to edit page
        return redirect('content:course_edit', course_id=course.id)
        
    except Course.DoesNotExist:
        messages.error(request, 'Course not found.')
        return redirect('content:courses_browse')
    except Exception as e:
        messages.error(request, f'Error updating course: {str(e)}')
        return redirect('content:courses_browse')


@login_required
def course_delete_view(request, course_id):
    """
    Handle course deletion for admins and managers
    """
    user = request.user
    
    try:
        from courses.models import Course
        
        # Get course
        course = Course.objects.get(id=course_id)
        
        # Check permissions - only admins and superadmins can delete courses
        if not user.is_admin_or_above():
            messages.error(request, 'You do not have permission to delete courses.')
            return redirect('dashboard')
        
        # Check organization access
        if not user.is_superadmin() and course.organization != user.organization:
            messages.error(request, 'You do not have permission to delete this course.')
            return redirect('content:courses_browse')
        
        if request.method == 'POST':
            course_title = course.title
            course.delete()
            messages.success(request, f'🗑️ Course "{course_title}" has been deleted successfully.')
            return redirect('content:courses_browse')
        
        context = {
            'user': user,
            'course': course,
            'page_title': f'Delete Course - {course.title}',
        }
        
        return render(request, 'courses/delete.html', context)
        
    except Course.DoesNotExist:
        messages.error(request, 'Course not found.')
        return redirect('content:courses_browse')
    except Exception as e:
        messages.error(request, f'Error deleting course: {str(e)}')
        return redirect('content:courses_browse')


@login_required
def course_detail_view(request, course_id):
    """
    Course detail page with documents and progress tracking
    """
    user = request.user
    
    try:
        from courses.models import Course
        from enrollments.models import Enrollment as CourseEnrollment
        
        # Get course with documents prefetched
        course = Course.objects.prefetch_related('documents').get(id=course_id)
        
        # Check enrollment status
        enrollment = CourseEnrollment.objects.filter(user=user, course=course).first()

        # Access rules:
        # - Students must be enrolled and enrollment must be active
        # - Managers/admins/instructors follow course visibility/management checks
        if user.is_student():
            if not enrollment or not enrollment.is_active or enrollment.status in ['SUSPENDED', 'DROPPED', 'EXPIRED']:
                messages.error(request, 'You do not have access to this course.')
                return redirect('dashboard')
        elif not course.can_user_access(user):
            messages.error(request, 'You do not have access to this course.')
            return redirect('dashboard')
        
        # Check if user can manage this course (for template context)
        can_manage_course = user.can_manage_course(course)
        
        is_enrolled = enrollment is not None
        is_completed = enrollment and enrollment.status == 'COMPLETED'
        
        # Get course documents from database - using proper relationship
        documents = []
        course_pdf = None
        
        # Add course PDF if available
        if course.has_pdf_document:
            course_pdf = {
                'id': 'main_pdf',
                'title': course.pdf_title or course.title,
                'description': course.pdf_description or 'Main course document',
                'file_path': course.course_pdf.url,
                'file_size': course.pdf_size_display,
                'upload_date': course.updated_at,
                'type': 'PDF',
                'is_completed': False,  # Main PDF doesn't have individual completion tracking
                'completed_at': None,
                'order': 0,
                'is_main_pdf': True
            }
        
        # Get additional documents using proper relationship
        if course.allow_organization_access or user.is_admin_or_above():
            try:
                from enrollments.models import DocumentProgress
                
                # Use the prefetched documents
                course_documents = course.documents.filter(
                    is_latest_version=True
                ).order_by('order', 'created_at')
                
                for doc in course_documents:
                    # Check if user has completed this document
                    progress = DocumentProgress.objects.filter(
                        user=user,
                        course=course,
                        document=doc
                    ).first()
                    
                    # Check document accessibility
                    is_accessible = doc.is_accessible(user) if hasattr(doc, 'is_accessible') else True
                    
                    if is_accessible:
                        documents.append({
                            'id': str(doc.id),
                            'title': doc.title,
                            'description': doc.description,
                            'file_path': doc.file.url if doc.file else '#',
                            'file_size': doc.file_size_display,
                            'upload_date': doc.created_at,
                            'type': doc.file_type,
                            'is_completed': progress.is_completed if progress else False,
                            'completed_at': progress.completed_at if progress else None,
                            'order': doc.order,
                            'is_main_pdf': False
                        })
                
            except Exception as e:
                pass
        
        # Calculate progress
        total_documents = len(documents)
        # Calculate progress based on enrollment status
        if enrollment and enrollment.status == 'COMPLETED':
            # If course is completed, progress is 100%
            progress_percentage = 100
            completed_documents = total_documents
        else:
            # Calculate progress from document completion
            completed_documents = len([d for d in documents if d.get('is_completed', False)])
            progress_percentage = (completed_documents / total_documents) * 100 if total_documents > 0 else 0
        
        # Calculate progress circle stroke-dashoffset for SVG
        # Circle circumference = 2 * π * r = 2 * 3.14 * 50 = 314
        # Progress offset = circumference - (progress_percentage/100 * circumference)
        # Simplified: 314 - (progress_percentage * 3.14)
        progress_offset = 314 - (progress_percentage * 3.14)
        
        # Get enrolled count
        enrolled_count = CourseEnrollment.objects.filter(course=course).count()
        
        context = {
            'user': user,
            'course': course,
            'documents': documents,
            'course_pdf': course_pdf,  # Add course PDF to context
            'is_enrolled': is_enrolled,
            'is_completed': is_completed,
            'progress_percentage': int(progress_percentage),
            'progress_offset': int(progress_offset),  # For SVG stroke-dashoffset
            'total_documents': total_documents,
            'completed_documents': completed_documents,
            'enrolled_count': enrolled_count,
            'can_manage_course': can_manage_course,  # Clean permission check
            'page_title': course.title,
            'organization_courses': course.get_organization_courses(),  # Add organization courses
        }
        
        return render(request, 'courses/detail.html', context)
        
    except Course.DoesNotExist:
        messages.error(request, 'Course not found.')
        return redirect('dashboard')
    except ImportError:
        messages.error(request, 'Course system not available.')
        return redirect('dashboard')


@login_required
def learning_continue(request):
    """
    Continue learning page for students - redirects to current course
    """
    user = request.user
    
    # Only students can access this
    if not user.is_student():
        messages.error(request, 'This page is for students only.')
        return redirect('dashboard')
    
    try:
        from courses.models import Course
        from enrollments.models import Enrollment
        from courses.models import CourseDocument
        from enrollments.models import DocumentProgress
        
        # Get student's active enrollments
        active_enrollments = Enrollment.objects.filter(
            user=user,
            is_active=True
        ).exclude(status='COMPLETED').order_by('-last_accessed_at')
        
        if active_enrollments.exists():
            # Get the most recently accessed course
            enrollment = active_enrollments.first()
            course = enrollment.course
            
            # Check if there are incomplete documents
            incomplete_documents = []
            course_documents = CourseDocument.objects.filter(course=course).order_by('order', 'created_at')
            
            for doc in course_documents:
                progress = DocumentProgress.objects.filter(
                    user=user,
                    course=course,
                    document=doc,
                    is_completed=True
                ).first()
                
                if not progress:
                    incomplete_documents.append(doc)
            
            # Redirect to course detail page
            messages.info(request, f'Continuing your course: {course.title}')
            return redirect('content:course_detail', course_id=course.id)
        else:
            # No active courses, redirect to course browse
            messages.info(request, 'No active courses found. Browse available courses to get started.')
            return redirect('student_course_browse')
            
    except ImportError:
        messages.error(request, 'Learning system not available.')
        return redirect('dashboard')
    except Exception as e:
        messages.error(request, f'Error accessing learning content: {str(e)}')
        return redirect('dashboard')


@login_required
def achievements_view(request):
    """
    Achievements and badges page for students
    """
    user = request.user

    completed_courses = 0
    certificates_earned = 0
    learning_hours = 0
    achievements = []

    try:
        from enrollments.models import Enrollment
        from certificates.models import Certificate

        completed_courses = Enrollment.objects.filter(user=user, status='COMPLETED').count()
        certificates_earned = Certificate.objects.filter(user=user).count()
        learning_hours = Enrollment.objects.filter(user=user, status='COMPLETED').aggregate(
            total=Sum('course__duration_hours')
        )['total'] or 0

        achievement_rules = [
            {
                'icon': '🎯',
                'name': 'First Course',
                'description': 'Complete your first course',
                'current': completed_courses,
                'target': 1,
            },
            {
                'icon': '📚',
                'name': 'Consistent Learner',
                'description': 'Complete 5 courses',
                'current': completed_courses,
                'target': 5,
            },
            {
                'icon': '🌟',
                'name': 'Knowledge Master',
                'description': 'Complete 10 courses',
                'current': completed_courses,
                'target': 10,
            },
            {
                'icon': '🏅',
                'name': 'Certified',
                'description': 'Earn your first certificate',
                'current': certificates_earned,
                'target': 1,
            },
            {
                'icon': '🏆',
                'name': 'Certificate Collector',
                'description': 'Earn 5 certificates',
                'current': certificates_earned,
                'target': 5,
            },
            {
                'icon': '⏱️',
                'name': 'Focused Learner',
                'description': 'Complete 50 learning hours',
                'current': learning_hours,
                'target': 50,
            },
        ]

        for rule in achievement_rules:
            progress = 100 if rule['target'] <= 0 else min(100, round((rule['current'] / rule['target']) * 100))
            achievements.append({
                **rule,
                'is_unlocked': rule['current'] >= rule['target'],
                'progress': progress,
            })
    except ImportError:
        pass

    unlocked_badges = len([achievement for achievement in achievements if achievement['is_unlocked']])
    
    context = {
        'user': user,
        'page_title': 'My Achievements',
        'achievements': achievements,
        'achievements_total': len(achievements),
        'unlocked_badges': unlocked_badges,
        'completed_courses': completed_courses,
        'learning_hours': learning_hours,
    }
    
    return render(request, 'achievements/list.html', context)


@login_required
def profile_view(request):
    """
    User profile page
    """
    user = request.user

    courses_enrolled = 0
    certificates_earned = 0
    achievements_unlocked = 0
    learning_hours = 0

    try:
        from enrollments.models import Enrollment
        from certificates.models import Certificate

        courses_enrolled = Enrollment.objects.filter(user=user).count()
        completed_courses = Enrollment.objects.filter(user=user, status='COMPLETED').count()
        certificates_earned = Certificate.objects.filter(user=user).count()
        learning_hours = Enrollment.objects.filter(user=user, status='COMPLETED').aggregate(
            total=Sum('course__duration_hours')
        )['total'] or 0

        achievements_unlocked = sum([
            completed_courses >= 1,
            completed_courses >= 5,
            completed_courses >= 10,
            certificates_earned >= 1,
            certificates_earned >= 5,
            learning_hours >= 50,
        ])
    except ImportError:
        pass
    
    context = {
        'user': user,
        'page_title': 'My Profile',
        'profile_stats': {
            'courses_enrolled': courses_enrolled,
            'certificates_earned': certificates_earned,
            'achievements_unlocked': achievements_unlocked,
            'learning_hours': learning_hours,
        }
    }
    
    return render(request, 'profile/detail.html', context)


@login_required
def profile_edit(request):
    """
    Edit user profile page
    """
    user = request.user
    
    if request.method == 'POST':
        # Update basic info
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        user.bio = request.POST.get('bio', '').strip()
        
        # Handle profile picture upload
        if 'avatar' in request.FILES:
            user.avatar = request.FILES['avatar']
        
        # Handle email change (if different)
        new_email = request.POST.get('email', '').strip().lower()
        if new_email != user.email:
            # Check if email is already taken
            from accounts.models import User
            if User.objects.filter(email=new_email).exclude(id=user.id).exists():
                messages.error(request, 'This email address is already in use.')
                return render(request, 'profile/edit.html', {
                    'user': user,
                    'page_title': 'Edit Profile',
                    'error': 'Email already in use'
                })
            user.email = new_email
        
        try:
            user.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('content:profile_detail')
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
    
    context = {
        'user': user,
        'page_title': 'Edit Profile',
    }
    
    return render(request, 'profile/edit.html', context)


@login_required
def settings_view(request):
    """
    User settings page
    """
    user = request.user
    
    context = {
        'user': user,
        'page_title': 'Settings',
    }
    
    return render(request, 'settings/edit.html', context)


@login_required
def courses_manage_view(request):
    """
    Courses management page for admins
    """
    user = request.user
    
    # Check permissions
    if not user.is_manager_or_above():
        messages.error(request, 'You do not have permission to manage courses.')
        return redirect('dashboard')
    
    try:
        from courses.models import Course
        from django.core.paginator import Paginator
        
        # Get courses for the organization
        if user.organization:
            courses_queryset = Course.objects.filter(organization=user.organization)
        else:
            courses_queryset = Course.objects.all()
        
        # Search functionality
        search_query = request.GET.get('search', '')
        if search_query:
            courses_queryset = courses_queryset.filter(
                title__icontains=search_query
            )
        
        # Filter by status
        status_filter = request.GET.get('status', '')
        if status_filter:
            courses_queryset = courses_queryset.filter(status=status_filter)
        
        # Pagination
        paginator = Paginator(courses_queryset, 12)
        page_number = request.GET.get('page')
        courses = paginator.get_page(page_number)
        
        context = {
            'user': user,
            'courses': courses,
            'search_query': search_query,
            'status_filter': status_filter,
            'page_title': 'Manage Courses',
        }
        
        return render(request, 'courses/manage.html', context)
        
    except ImportError:
        messages.error(request, 'Course system not available.')
        return redirect('dashboard')


@login_required
def enrollments_manage_view(request):
    """
    Enrollments management page for admins
    """
    user = request.user
    
    # Check permissions
    if not user.is_manager_or_above():
        messages.error(request, 'You do not have permission to manage enrollments.')
        return redirect('dashboard')
    
    try:
        from enrollments.models import Enrollment
        from django.core.paginator import Paginator
        
        # Get enrollments for the organization
        if user.organization:
            enrollments_queryset = Enrollment.objects.filter(
                course__organization=user.organization
            )
        else:
            enrollments_queryset = Enrollment.objects.all()
        
        # Search functionality
        search_query = request.GET.get('search', '')
        if search_query:
            enrollments_queryset = enrollments_queryset.filter(
                user__email__icontains=search_query
            )
        
        # Filter by status
        status_filter = request.GET.get('status', '')
        if status_filter:
            enrollments_queryset = enrollments_queryset.filter(status=status_filter)
        
        # Pagination
        paginator = Paginator(enrollments_queryset, 20)
        page_number = request.GET.get('page')
        enrollments = paginator.get_page(page_number)
        
        context = {
            'user': user,
            'enrollments': enrollments,
            'search_query': search_query,
            'status_filter': status_filter,
            'page_title': 'Manage Enrollments',
        }
        
        return render(request, 'enrollments/manage.html', context)
        
    except ImportError:
        messages.error(request, 'Enrollment system not available.')
        return redirect('dashboard')


@login_required
def assignments_manage_view(request):
    """
    Assignments management page for admins
    """
    user = request.user
    
    # Check permissions
    if not user.is_manager_or_above():
        messages.error(request, 'You do not have permission to manage assignments.')
        return redirect('dashboard')
    
    try:
        from assignments.models import Assignment
        from django.core.paginator import Paginator
        
        # Get assignments for the organization
        if user.organization:
            assignments_queryset = Assignment.objects.filter(
                course__organization=user.organization
            )
        else:
            assignments_queryset = Assignment.objects.all()
        
        # Search functionality
        search_query = request.GET.get('search', '')
        if search_query:
            assignments_queryset = assignments_queryset.filter(
                title__icontains=search_query
            )
        
        # Filter by type
        type_filter = request.GET.get('type', '')
        if type_filter:
            assignments_queryset = assignments_queryset.filter(assignment_type=type_filter)
        
        # Pagination
        paginator = Paginator(assignments_queryset, 20)
        page_number = request.GET.get('page')
        assignments = paginator.get_page(page_number)
        
        context = {
            'user': user,
            'assignments': assignments,
            'search_query': search_query,
            'type_filter': type_filter,
            'page_title': 'Manage Assignments',
        }
        
        return render(request, 'assignments/manage.html', context)
        
    except ImportError:
        messages.error(request, 'Assignment system not available.')
        return redirect('dashboard')


@login_required
def certificates_manage_view(request):
    """
    Certificates management page for admins
    """
    user = request.user
    
    # Check permissions
    if not user.is_manager_or_above():
        messages.error(request, 'You do not have permission to manage certificates.')
        return redirect('dashboard')
    
    try:
        from certificates.models import Certificate
        from django.core.paginator import Paginator
        
        # Get certificates for the organization
        if user.organization:
            certificates_queryset = Certificate.objects.filter(
                course__organization=user.organization
            )
        else:
            certificates_queryset = Certificate.objects.all()
        
        # Search functionality
        search_query = request.GET.get('search', '')
        if search_query:
            certificates_queryset = certificates_queryset.filter(
                user__email__icontains=search_query
            )
        
        # Filter by status
        status_filter = request.GET.get('status', '')
        if status_filter:
            certificates_queryset = certificates_queryset.filter(status=status_filter)
        
        # Pagination
        paginator = Paginator(certificates_queryset, 20)
        page_number = request.GET.get('page')
        certificates = paginator.get_page(page_number)
        
        context = {
            'user': user,
            'certificates': certificates,
            'search_query': search_query,
            'status_filter': status_filter,
            'page_title': 'Manage Certificates',
        }
        
        return render(request, 'certificates/manage.html', context)
        
    except ImportError:
        messages.error(request, 'Certificate system not available.')
        return redirect('dashboard')


@login_required
def student_assignments_view(request):
    """
    Student assignments view
    """
    user = request.user
    
    # Only students can access this
    if not user.is_student():
        messages.error(request, 'This page is for students only.')
        return redirect('dashboard')
    
    try:
        from assignments.models import Assignment, AssignmentSubmission
        from django.core.paginator import Paginator
        
        # Get assignments from enrolled courses
        from enrollments.models import Enrollment as CourseEnrollment
        enrolled_courses = CourseEnrollment.objects.filter(user=user, is_active=True).values_list('course', flat=True)
        
        assignments_queryset = Assignment.objects.filter(course__in=enrolled_courses)
        
        # Get submission status for each assignment
        assignments_with_status = []
        for assignment in assignments_queryset:
            submission = AssignmentSubmission.objects.filter(
                assignment=assignment, 
                student=user
            ).first()

            if not submission:
                assignment_status = 'NOT_STARTED'
            elif submission.status == 'GRADED':
                assignment_status = 'COMPLETED'
            elif submission.status in ['DRAFT', 'RETURNED']:
                assignment_status = 'IN_PROGRESS'
            else:
                assignment_status = submission.status
            
            assignments_with_status.append({
                'assignment': assignment,
                'submission': submission,
                'status': assignment_status,
                'score': submission.score if submission else None,
                'submitted_at': submission.submitted_at if submission else None
            })

        total_assignments = len(assignments_with_status)
        completed_assignments = len([item for item in assignments_with_status if item['status'] == 'COMPLETED'])
        in_progress_assignments = len([item for item in assignments_with_status if item['status'] == 'IN_PROGRESS'])
        not_started_assignments = len([item for item in assignments_with_status if item['status'] == 'NOT_STARTED'])
        
        # Pagination
        paginator = Paginator(assignments_with_status, 20)
        page_number = request.GET.get('page')
        assignments_page = paginator.get_page(page_number)
        
        context = {
            'user': user,
            'assignments': assignments_page,
            'total_assignments': total_assignments,
            'completed_assignments': completed_assignments,
            'in_progress_assignments': in_progress_assignments,
            'not_started_assignments': not_started_assignments,
            'page_title': 'My Assignments',
        }
        
        return render(request, 'assignments/student.html', context)
        
    except ImportError:
        messages.error(request, 'Assignment system not available.')
        return redirect('dashboard')


@login_required
def student_certificates_view(request):
    """
    Student certificates view
    """
    user = request.user
    
    # Only students can access this
    if not user.is_student():
        messages.error(request, 'This page is for students only.')
        return redirect('dashboard')
    
    try:
        from certificates.models import Certificate
        from django.core.paginator import Paginator
        
        # Get student's certificates
        certificates_queryset = Certificate.objects.filter(user=user).order_by('-created_at')

        issued_certificates = certificates_queryset.filter(status='ISSUED').count()
        pending_certificates = certificates_queryset.filter(status='PENDING').count()
        revoked_certificates = certificates_queryset.filter(status='REVOKED').count()
        
        # Pagination
        paginator = Paginator(certificates_queryset, 20)
        page_number = request.GET.get('page')
        certificates = paginator.get_page(page_number)
        
        context = {
            'user': user,
            'certificates': certificates,
            'total_certificates': certificates_queryset.count(),
            'issued_certificates': issued_certificates,
            'pending_certificates': pending_certificates,
            'revoked_certificates': revoked_certificates,
            'page_title': 'My Certificates',
        }
        
        return render(request, 'certificates/student.html', context)
        
    except ImportError:
        messages.error(request, 'Certificate system not available.')
        return redirect('dashboard')


@login_required
def courses_browse(request):
    """
    Browse courses page
    """
    user = request.user
    
    try:
        from courses.models import Course
        from enrollments.models import Enrollment
        
        # Start with all active courses
        available_courses = Course.objects.filter(is_active=True)

        # Scope by organization for non-superadmins
        if not user.is_superadmin() and user.organization:
            available_courses = available_courses.filter(organization=user.organization)
        elif not user.is_superadmin() and not user.organization:
            # If user has no organization, they can't see any courses
            available_courses = Course.objects.none()

        # Students should only see published, organization-accessible dashboard courses
        if user.is_student():
            available_courses = available_courses.filter(
                status='PUBLISHED',
                show_in_dashboard=True,
                allow_organization_access=True
            )
        # Non-students (managers, admins) see all active courses in their org
        # but can also see courses that might not be dashboard-visible

        available_courses = available_courses.order_by('-created_at')
        
        # Separate enrolled and available courses
        enrolled_courses = []
        available_for_enrollment = []
        
        for course in available_courses:
            enrollment = Enrollment.objects.filter(user=user, course=course).first()
            if enrollment:
                enrolled_courses.append({
                    'course': course,
                    'enrollment': enrollment,
                    'progress': enrollment.progress_percentage,
                    'status': enrollment.status
                })
            else:
                available_for_enrollment.append(course)
        
        context = {
            'user': user,
            'enrolled_courses': enrolled_courses,
            'available_courses': available_for_enrollment,
            'total_courses': len(enrolled_courses) + len(available_for_enrollment),
            'page_title': 'Browse Courses',
        }
        
        return render(request, 'courses/student_browse.html', context)
        
    except ImportError:
        messages.error(request, 'Course system not available.')
        return redirect('dashboard')


@login_required
def organizations_manage(request):
    """
    Organization management for superadmins
    """
    user = request.user
    
    # Only superadmins can manage organizations
    if not user.is_superadmin():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    # Fetch real data from database
    from organizations.models import Organization
    from accounts.models import User
    try:
        from enrollments.models import Enrollment
    except ImportError:
        Enrollment = None
    
    organizations = Organization.objects.all()
    
    # Add statistics to each organization
    org_data = []
    for org in organizations:
        user_count = User.objects.filter(organization=org, is_active=True).count()
        total_users = User.objects.filter(organization=org).count()
        
        # Get course count (if courses model exists)
        course_count = 0
        try:
            from courses.models import Course
            course_count = Course.objects.filter(organization=org).count()
        except ImportError:
            pass
        
        completion_rate = 0
        if Enrollment is not None:
            total_org_enrollments = Enrollment.objects.filter(user__organization=org).count()
            completed_org_enrollments = Enrollment.objects.filter(
                user__organization=org,
                status='COMPLETED'
            ).count()
            completion_rate = round((completed_org_enrollments / max(total_org_enrollments, 1)) * 100, 1) if total_org_enrollments > 0 else 0
        
        org_data.append({
            'id': org.id,
            'name': org.name,
            'description': org.description or '',
            'is_active': org.is_active,
            'created_at': org.created_at,
            'user_count': user_count,
            'total_users': total_users,
            'course_count': course_count,
            'completion_rate': completion_rate,
            'tier': 'Enterprise' if user_count > 100 else 'Professional' if user_count > 50 else 'Basic',
        })
    
    # Calculate overall statistics
    total_orgs = organizations.count()
    active_orgs = organizations.filter(is_active=True).count()
    total_users = User.objects.filter(organization__isnull=False).count()
    pending_orgs = organizations.filter(is_active=False).count()
    
    context = {
        'user': user,
        'page_title': 'Manage Organizations',
        'organizations': org_data,
        'stats': {
            'total_orgs': total_orgs,
            'active_orgs': active_orgs,
            'total_users': total_users,
            'pending_orgs': pending_orgs,
        }
    }
    
    return render(request, 'organizations/manage.html', context)


@login_required
def organizations_create(request):
    """
    Create new organization for superadmins
    """
    user = request.user
    
    # Only superadmins can create organizations
    if not user.is_superadmin():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        from organizations.models import Organization
        
        try:
            org = Organization.objects.create(
                name=request.POST.get('name'),
                email=request.POST.get('email'),
                phone=request.POST.get('phone', ''),
                description=request.POST.get('description', ''),
                website=request.POST.get('website', ''),
                address=request.POST.get('address', ''),
                subscription_tier=request.POST.get('subscription_tier', 'BASIC'),
                max_users=int(request.POST.get('max_users', 100)),
                is_active=True
            )
            
            messages.success(request, f'Organization "{org.name}" has been created successfully!')
            return redirect('organizations_manage')
            
        except Exception as e:
            messages.error(request, f'Error creating organization: {str(e)}')
    
    return render(request, 'organizations/create.html', {
        'user': user,
        'page_title': 'Create Organization',
    })


@login_required
def users_manage(request):
    """
    User management for admins and superadmins
    """
    user = request.user
    
    # Check permissions
    if not (user.is_admin_or_above()):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    # Get real user data
    try:
        from accounts.models import User
        from organizations.models import Organization
        from django.core.paginator import Paginator
        from django.utils import timezone
        from datetime import timedelta
        
        # Get users with pagination
        if user.is_superadmin():
            users_queryset = User.objects.all().order_by('-date_joined')
        else:
            users_queryset = User.objects.filter(organization=user.organization).order_by('-date_joined')
        
        # Pagination
        paginator = Paginator(users_queryset, 20)
        page_number = request.GET.get('page')
        users = paginator.get_page(page_number)
        
        # Statistics
        total_users = users_queryset.count()
        active_users = users_queryset.filter(is_active=True).count()
        
        # New users this month
        this_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        new_users = users_queryset.filter(date_joined__gte=this_month).count()
        
        # Organization count
        if user.is_superadmin():
            org_count = Organization.objects.count()
        else:
            org_count = 1
        
        stats = {
            'total_users': total_users,
            'active_users': active_users,
            'new_users': new_users,
            'org_count': org_count,
        }
        
    except ImportError:
        users = []
        stats = {
            'total_users': 0,
            'active_users': 0,
            'new_users': 0,
            'org_count': 0,
        }
    
    context = {
        'user': user,
        'page_title': 'Manage Users',
        'users': users,
        'stats': stats,
    }
    
    return render(request, 'users/manage.html', context)


@login_required
def users_invite(request):
    """
    Invite users page for admins and managers
    """
    user = request.user
    
    # Check permissions
    if not (user.is_manager_or_above()):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    from accounts.models import User

    allowed_roles = ['STUDENT', 'MANAGER'] if user.is_manager() else ['STUDENT', 'MANAGER', 'ADMIN']
    role_choices = [(code, label) for code, label in User.ROLE_CHOICES if code in allowed_roles]

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        selected_role = request.POST.get('role', 'STUDENT').strip().upper()
        password = request.POST.get('password', '').strip()

        if not email:
            messages.error(request, 'Email is required.')
        elif selected_role not in allowed_roles:
            messages.error(request, 'You do not have permission to assign that role.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'A user with this email already exists.')
        elif len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
        else:
            invite_org = user.organization if not user.is_superadmin() else user.organization
            new_user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=selected_role,
                organization=invite_org,
                is_active=True,
            )
            if user.is_manager():
                new_user.managed_by = user
                new_user.save(update_fields=['managed_by'])
            messages.success(request, f'User {email} was created successfully.')
            return redirect('users_invite')

    context = {
        'user': user,
        'page_title': 'Invite Users',
        'role_choices': role_choices,
    }

    return render(request, 'users/invite.html', context)


@login_required
def departments_manage(request):
    """
    Department management for admins
    """
    user = request.user
    
    # Check permissions
    if not user.is_admin_or_above():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    try:
        from organizations.models import Department

        departments = Department.objects.select_related('organization', 'parent', 'head').filter(
            organization=user.organization
        ).order_by('name') if user.organization else Department.objects.none()

        context = {
            'user': user,
            'page_title': 'Manage Departments',
            'departments': departments,
            'total_departments': departments.count(),
            'active_departments': departments.filter(is_active=True).count(),
        }
    except ImportError:
        context = {
            'user': user,
            'page_title': 'Manage Departments',
            'departments': [],
            'total_departments': 0,
            'active_departments': 0,
        }

    return render(request, 'departments/manage.html', context)


@login_required
def departments_create(request):
    """
    Create department page for admins
    """
    user = request.user
    
    # Check permissions
    if not user.is_admin_or_above():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    try:
        from organizations.models import Department
        from django.utils.text import slugify

        if not user.organization:
            messages.error(request, 'You must belong to an organization to create departments.')
            return redirect('departments_manage')

        if request.method == 'POST':
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            is_active = request.POST.get('is_active') == 'on'

            if not name:
                messages.error(request, 'Department name is required.')
            else:
                base_slug = slugify(name)
                slug = base_slug
                counter = 1
                while Department.objects.filter(organization=user.organization, slug=slug).exists():
                    slug = f'{base_slug}-{counter}'
                    counter += 1

                Department.objects.create(
                    organization=user.organization,
                    name=name,
                    slug=slug,
                    description=description,
                    is_active=is_active,
                )
                messages.success(request, f'Department "{name}" created successfully.')
                return redirect('departments_manage')

        context = {
            'user': user,
            'page_title': 'Create Department',
        }
    except ImportError:
        messages.error(request, 'Department module is not available.')
        return redirect('dashboard')

    return render(request, 'departments/create.html', context)


@login_required
def team_add(request):
    """
    Add team member page for managers
    """
    user = request.user
    
    # Check permissions
    if not user.is_manager_or_above():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    context = {
        'user': user,
        'page_title': 'Add Team Member',
    }
    
    return render(request, 'team/add.html', context)


@login_required
def team_assign(request):
    """
    Assign training to team page for managers
    """
    user = request.user
    
    # Check permissions
    if not user.is_manager_or_above():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    context = {
        'user': user,
        'page_title': 'Assign Training',
    }
    
    return render(request, 'team/assign.html', context)


@login_required
def team_performance(request):
    """
    Team performance review page for managers
    """
    user = request.user
    
    # Check permissions
    if not user.is_manager_or_above():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    context = {
        'user': user,
        'page_title': 'Team Performance',
    }
    
    return render(request, 'team/performance.html', context)


@login_required
def team_schedule(request):
    """
    Training calendar page for managers
    """
    user = request.user
    
    # Check permissions
    if not user.is_manager_or_above():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    context = {
        'user': user,
        'page_title': 'Training Calendar',
    }
    
    return render(request, 'team/schedule.html', context)


@login_required
def team_communication(request):
    """
    Team communication page for managers
    """
    user = request.user
    
    # Check permissions
    if not user.is_manager_or_above():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    context = {
        'user': user,
        'page_title': 'Team Communication',
    }
    
    return render(request, 'team/communication.html', context)


@login_required
def courses_manage(request):
    """
    Course management page for admins
    """
    user = request.user
    
    # Check permissions
    if not user.is_admin_or_above():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    context = {
        'user': user,
        'page_title': 'Manage Courses',
    }
    
    return render(request, 'courses/manage.html', context)


@login_required
def courses_approval(request):
    """
    Course approval page for admins
    """
    user = request.user
    
    # Check permissions
    if not user.is_admin_or_above():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    context = {
        'user': user,
        'page_title': 'Course Approval',
    }
    
    return render(request, 'courses/approval.html', context)


@login_required
def certificates_manage(request):
    """
    Certificate management page for admins
    """
    user = request.user
    
    # Check permissions
    if not user.is_admin_or_above():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    # Get real certificate data
    try:
        from certificates.models import Certificate
        from courses.models import Course
        from django.core.paginator import Paginator
        from django.utils import timezone
        from datetime import timedelta
        
        # Get certificates with pagination
        if user.is_superadmin():
            certificates_queryset = Certificate.objects.all().order_by('-issued_date')
        else:
            certificates_queryset = Certificate.objects.filter(
                course__organization=user.organization
            ).order_by('-issued_date')
        
        # Pagination
        paginator = Paginator(certificates_queryset, 20)
        page_number = request.GET.get('page')
        certificates = paginator.get_page(page_number)
        
        # Statistics
        total_certificates = certificates_queryset.count()
        issued_this_month = certificates_queryset.filter(
            issued_date__gte=timezone.now() - timedelta(days=30)
        ).count()
        pending_review = certificates_queryset.filter(status='pending').count()
        revoked_certificates = certificates_queryset.filter(status='revoked').count()
        
        stats = {
            'total_certificates': total_certificates,
            'issued_this_month': issued_this_month,
            'pending_review': pending_review,
            'revoked_certificates': revoked_certificates,
        }
        
    except ImportError:
        certificates = []
        stats = {
            'total_certificates': 0,
            'issued_this_month': 0,
            'pending_review': 0,
            'revoked_certificates': 0,
        }
    
    context = {
        'user': user,
        'page_title': 'Manage Certificates',
        'certificates': certificates,
        'stats': stats,
    }
    
    return render(request, 'certificates/manage.html', context)


@login_required
def learning_paths_view(request):
    """
    Learning paths page
    """
    user = request.user
    
    context = {
        'user': user,
        'page_title': 'Learning Paths',
    }
    
    return render(request, 'learning/paths.html', context)


@login_required
def analytics_platform(request):
    """
    Platform analytics page for superadmins
    """
    user = request.user
    
    # Only superadmins can access platform analytics
    if not user.is_superadmin():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    # Get real platform data
    try:
        from accounts.models import User
        from organizations.models import Organization
        from courses.models import Course
        from certificates.models import Certificate
        
        # Platform statistics
        total_users = User.objects.count()
        total_organizations = Organization.objects.count()
        total_courses = Course.objects.count()
        total_certificates = Certificate.objects.count()
        
        recent_activities = []

        recent_users = User.objects.order_by('-date_joined')[:5]
        for recent_user in recent_users:
            recent_activities.append({
                'text': f'New user joined: {recent_user.get_full_name() or recent_user.email}',
                'time': recent_user.date_joined,
                'badge': 'Users',
                'type': 'success',
            })

        recent_orgs = Organization.objects.order_by('-created_at')[:3]
        for recent_org in recent_orgs:
            recent_activities.append({
                'text': f'Organization created: {recent_org.name}',
                'time': recent_org.created_at,
                'badge': 'Orgs',
                'type': 'info',
            })

        recent_courses = Course.objects.order_by('-created_at')[:3]
        for recent_course in recent_courses:
            recent_activities.append({
                'text': f'Course created: {recent_course.title}',
                'time': recent_course.created_at,
                'badge': 'Courses',
                'type': 'warning',
            })

        recent_activities = sorted(recent_activities, key=lambda item: item['time'], reverse=True)[:10]
        for activity in recent_activities:
            activity['time'] = activity['time'].strftime('%b %d, %Y %H:%M')
        
    except ImportError:
        # Fallback data
        total_users = 0
        total_organizations = 0
        total_courses = 0
        total_certificates = 0
        recent_activities = []
    
    context = {
        'user': user,
        'page_title': 'Platform Analytics',
        'total_users': total_users,
        'total_organizations': total_organizations,
        'total_courses': total_courses,
        'total_certificates': total_certificates,
        'recent_activities': recent_activities,
    }
    
    return render(request, 'analytics/platform.html', context)


@login_required
def analytics_organization(request):
    """
    Organization analytics page for admins
    """
    user = request.user
    
    # Check permissions
    if not user.is_admin_or_above():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    # Get real organization data
    try:
        from accounts.models import User
        from organizations.models import Organization
        from courses.models import Course
        from certificates.models import Certificate
        
        # Get organizations
        if user.is_superadmin():
            organizations = Organization.objects.all()
        else:
            organizations = Organization.objects.filter(id=user.organization.id)
        
        # Get selected organization
        org_id = request.GET.get('org_id')
        selected_org = None
        org_stats = None
        top_performers = []
        
        if org_id:
            selected_org = Organization.objects.get(id=org_id)
            
            # Organization statistics
            total_users = User.objects.filter(organization=selected_org).count()
            active_courses = Course.objects.filter(organization=selected_org, status='PUBLISHED').count()
            certificates_issued = Certificate.objects.filter(user__organization=selected_org).count()

            thirty_days_ago = timezone.now() - timedelta(days=30)
            new_org_users = User.objects.filter(organization=selected_org, date_joined__gte=thirty_days_ago).count()
            new_org_courses = Course.objects.filter(organization=selected_org, created_at__gte=thirty_days_ago).count()
            new_org_certificates = Certificate.objects.filter(user__organization=selected_org, created_at__gte=thirty_days_ago).count()

            completions_total = Enrollment.objects.filter(user__organization=selected_org, status='COMPLETED').count()
            completions_recent = Enrollment.objects.filter(
                user__organization=selected_org,
                status='COMPLETED',
                updated_at__gte=thirty_days_ago
            ).count()
            completion_rate = round((completions_total / max(total_users, 1)) * 100, 1) if total_users > 0 else 0
            completion_trend = round((completions_recent / max(completions_total, 1)) * 100, 1) if completions_total > 0 else 0
            
            org_stats = {
                'total_users': total_users,
                'active_courses': active_courses,
                'certificates_issued': certificates_issued,
                'user_growth': round((new_org_users / max(total_users, 1)) * 100, 1) if total_users > 0 else 0,
                'course_growth': round((new_org_courses / max(active_courses, 1)) * 100, 1) if active_courses > 0 else 0,
                'certificate_growth': round((new_org_certificates / max(certificates_issued, 1)) * 100, 1) if certificates_issued > 0 else 0,
                'completion_rate': completion_rate,
                'completion_trend': completion_trend,
            }
            
            top_users = User.objects.filter(organization=selected_org).annotate(
                courses_completed=Count('enrollments', filter=Q(enrollments__status='COMPLETED')),
                certificates=Count('certificates')
            ).order_by('-courses_completed', '-certificates', 'first_name')[:5]

            top_performers = [
                {
                    'name': performer.get_full_name() or performer.email,
                    'role': performer.role.title(),
                    'courses_completed': performer.courses_completed,
                    'certificates': performer.certificates,
                    'hours_completed': 0,
                }
                for performer in top_users
            ]
        
    except ImportError:
        organizations = []
        selected_org = None
        org_stats = None
        top_performers = []
    
    context = {
        'user': user,
        'page_title': 'Organization Analytics',
        'organizations': organizations,
        'selected_org': selected_org,
        'org_stats': org_stats,
        'top_performers': top_performers,
    }
    
    return render(request, 'analytics/organization.html', context)


@login_required
def analytics_team(request):
    """
    Team analytics page for managers
    """
    user = request.user
    
    # Check permissions
    if not user.is_manager_or_above():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    # Get real team data
    try:
        from accounts.models import User
        from organizations.models import Team, TeamMembership
        from enrollments.models import Enrollment
        from certificates.models import Certificate

        teams_qs = Team.objects.filter(organization=user.organization) if user.organization else Team.objects.none()
        teams = [{'id': str(team.id), 'name': team.name} for team in teams_qs]
        
        # Get selected team
        team_id = request.GET.get('team_id')
        selected_team = None
        team_stats = None
        team_members = []
        
        if team_id:
            selected_team_obj = teams_qs.filter(id=team_id).first()
            if selected_team_obj:
                selected_team = {'id': str(selected_team_obj.id), 'name': selected_team_obj.name}

                member_ids = list(
                    TeamMembership.objects.filter(team=selected_team_obj).values_list('user_id', flat=True)
                )
                members_qs = User.objects.filter(id__in=member_ids)

                total_members = members_qs.count()
                total_enrollments = Enrollment.objects.filter(user_id__in=member_ids).count()
                completed_enrollments = Enrollment.objects.filter(user_id__in=member_ids, status='COMPLETED').count()
                total_certificates = Certificate.objects.filter(user_id__in=member_ids).count()
                total_hours = Enrollment.objects.filter(user_id__in=member_ids).aggregate(
                    total=Sum('course__duration_hours')
                )['total'] or 0
                avg_performance = round((completed_enrollments / max(total_enrollments, 1)) * 100, 1) if total_enrollments > 0 else 0

                team_stats = {
                    'total_members': total_members,
                    'avg_performance': avg_performance,
                    'courses_completed': completed_enrollments,
                    'total_hours': total_hours,
                    'member_growth': 0,
                    'performance_growth': 0,
                    'completion_growth': 0,
                    'hours_growth': 0,
                }

                team_members = []
                for member in members_qs:
                    member_completed = Enrollment.objects.filter(user=member, status='COMPLETED').count()
                    member_total = Enrollment.objects.filter(user=member).count()
                    member_certs = Certificate.objects.filter(user=member).count()
                    member_hours = Enrollment.objects.filter(user=member).aggregate(
                        total=Sum('course__duration_hours')
                    )['total'] or 0
                    member_progress = round((member_completed / max(member_total, 1)) * 100, 1) if member_total > 0 else 0
                    team_members.append({
                        'name': member.get_full_name() or member.email,
                        'role': member.role.title(),
                        'status': 'Active' if member.is_active else 'Inactive',
                        'courses_completed': member_completed,
                        'certificates': member_certs,
                        'hours': member_hours,
                        'progress': member_progress,
                    })
        
    except ImportError:
        teams = []
        selected_team = None
        team_stats = None
        team_members = []
    
    context = {
        'user': user,
        'page_title': 'Team Analytics',
        'teams': teams,
        'selected_team': selected_team,
        'team_stats': team_stats,
        'team_members': team_members,
    }
    
    return render(request, 'analytics/team.html', context)


@login_required
def analytics_reports(request):
    """
    Reports page for admins and managers
    """
    user = request.user
    
    # Check permissions
    if not user.is_manager_or_above():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    # Get real reports data
    try:
        from organizations.models import Organization
        
        # Organizations for filtering
        if user.is_superadmin():
            organizations = Organization.objects.all()
        else:
            organizations = Organization.objects.filter(id=user.organization.id)
        
        reports = []
        scheduled_reports = []
        
    except ImportError:
        organizations = []
        reports = []
        scheduled_reports = []
    
    context = {
        'user': user,
        'page_title': 'Analytics Reports',
        'organizations': organizations,
        'reports': reports,
        'scheduled_reports': scheduled_reports,
    }
    
    return render(request, 'analytics/reports.html', context)


@login_required
def admin_dashboard_view(request):
    """
    Admin dashboard with organization-specific statistics
    """
    user = request.user
    
    # Check permissions
    if not user.is_admin_or_above():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    # Get organization-specific statistics
    try:
        from courses.models import Course
        from enrollments.models import Enrollment as CourseEnrollment
        from certificates.models import Certificate
        from accounts.models import User
        from django.utils import timezone
        from datetime import timedelta
        
        # Course statistics for this organization
        total_courses = Course.objects.filter(organization=user.organization).count()
        published_courses = Course.objects.filter(
            organization=user.organization,
            status='PUBLISHED'
        ).count()
        
        # Enrollment statistics
        total_enrollments = CourseEnrollment.objects.filter(
            course__organization=user.organization
        ).count()
        
        # Certificate statistics
        total_certificates = Certificate.objects.filter(
            course__organization=user.organization
        ).count()
        
        # Completed courses statistics
        completed_enrollments = CourseEnrollment.objects.filter(
            course__organization=user.organization,
            status='COMPLETED'
        ).count()
        
        # User statistics for this organization
        org_users = User.objects.filter(organization=user.organization).count()
        active_users = User.objects.filter(
            organization=user.organization,
            is_active=True
        ).count()
        
        # Calculate real growth percentages
        from datetime import datetime, timedelta
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # New users in last 30 days
        new_users = User.objects.filter(
            organization=user.organization,
            date_joined__gte=thirty_days_ago
        ).count()
        user_growth = round((new_users / max(org_users, 1)) * 100, 1) if org_users > 0 else 0
        
        # New courses in last 30 days
        new_courses = Course.objects.filter(
            organization=user.organization,
            created_at__gte=thirty_days_ago
        ).count()
        course_growth = round((new_courses / max(total_courses, 1)) * 100, 1) if total_courses > 0 else 0
        
        # New enrollments in last 30 days
        new_enrollments = CourseEnrollment.objects.filter(
            course__organization=user.organization,
            created_at__gte=thirty_days_ago
        ).count()
        enrollment_growth = round((new_enrollments / max(total_enrollments, 1)) * 100, 1) if total_enrollments > 0 else 0
        
        # New certificates in last 30 days
        new_certificates = Certificate.objects.filter(
            course__organization=user.organization,
            created_at__gte=thirty_days_ago
        ).count()
        certificate_growth = round((new_certificates / max(total_certificates, 1)) * 100, 1) if total_certificates > 0 else 0
        
        # Growth for completed courses
        completed_thirty_days_ago = CourseEnrollment.objects.filter(
            course__organization=user.organization,
            status='COMPLETED',
            updated_at__gte=thirty_days_ago
        ).count()
        completion_growth = round((completed_thirty_days_ago / max(completed_enrollments, 1)) * 100, 1) if completed_enrollments > 0 else 0
        
        # Recent courses
        recent_courses = Course.objects.filter(
            organization=user.organization
        ).order_by('-created_at')[:5]
        
        stats = {
            'total_courses': total_courses,
            'published_courses': published_courses,
            'total_enrollments': total_enrollments,
            'total_certificates': total_certificates,
            'completed_courses': completed_enrollments,
            'certificates_issued': total_certificates,
            'org_users': org_users,
            'total_users': org_users,  # Alias for template compatibility
            'active_users': active_users,
            'user_growth': user_growth,
            'course_growth': course_growth,
            'enrollment_growth': enrollment_growth,
            'certificate_growth': certificate_growth,
            'completion_growth': completion_growth,
            'recent_courses': recent_courses,
        }
        
    except ImportError:
        # Fallback data
        stats = {
            'total_courses': 0,
            'published_courses': 0,
            'total_enrollments': 0,
            'total_certificates': 0,
            'completed_courses': 0,
            'certificates_issued': 0,
            'org_users': 0,
            'total_users': 0,
            'active_users': 0,
            'user_growth': 0,
            'course_growth': 0,
            'enrollment_growth': 0,
            'certificate_growth': 0,
            'completion_growth': 0,
            'recent_courses': [],
        }
    
    context = {
        'user': user,
        'page_title': 'Admin Dashboard',
        'stats': stats,
    }
    
    return render(request, 'dashboard.html', context)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def view_document(request, document_id):
    """
    API endpoint to view a PDF document
    """
    user = request.user
    
    try:
        from django.core.files.storage import default_storage
        import os
        
        # Get document path from storage
        course_docs_dir = 'course_documents/'
        if not default_storage.exists(course_docs_dir):
            return Response({'success': False, 'message': 'Document not found'}, status=404)
        
        all_files = default_storage.listdir(course_docs_dir)[0]
        document_file = None
        
        for filename in all_files:
            if filename == document_id and filename.endswith('.pdf'):
                document_file = os.path.join(course_docs_dir, filename)
                break
        
        if not document_file or not default_storage.exists(document_file):
            return Response({'success': False, 'message': 'Document not found'}, status=404)
        
        # Get file info
        file_size = default_storage.size(document_file)
        modified_time = default_storage.get_modified_time(document_file)
        
        # Extract title from filename
        if '_' in document_id:
            parts = document_id.split('_')
            if len(parts) >= 3:
                title = '_'.join(parts[2:]).replace('.pdf', '')
            else:
                title = document_id.replace('.pdf', '')
        else:
            title = document_id.replace('.pdf', '')
        
        # Create file URL
        file_url = default_storage.url(document_file)
        
        return Response({
            'success': True,
            'title': title,
            'file_url': file_url,
            'file_size': file_size,
            'upload_date': modified_time.isoformat(),
            'type': 'PDF'
        })
        
    except Exception as e:
        return Response({'success': False, 'message': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_document_complete(request, document_id):
    """
    API endpoint to mark a document as complete
    """
    user = request.user
    
    try:
        from courses.models import CourseDocument
        from django.utils import timezone
        
        # Get the document
        document = get_object_or_404(CourseDocument, id=document_id)
        course = document.course
        
        # Check if user has access to this course
        if user.organization and course.organization != user.organization:
            return Response({
                'success': False,
                'message': 'You do not have access to this course.'
            }, status=403)
        
        # Check if user is enrolled in the course
        from enrollments.models import Enrollment
        enrollment = Enrollment.objects.filter(user=user, course=course).first()
        if not enrollment:
            # Auto-enroll the user if they're trying to complete a document
            enrollment = Enrollment.objects.create(
                user=user,
                course=course,
                status='ACTIVE'
            )
        
        # Track document completion
        from content.models import DocumentProgress
        progress, created = DocumentProgress.objects.get_or_create(
            user=user,
            course=course,
            document=document,
            defaults={
                'is_completed': True,
                'completed_at': timezone.now()
            }
        )
        
        if not created and not progress.is_completed:
            progress.is_completed = True
            progress.completed_at = timezone.now()
            progress.save()
        
        # Update course progress
        total_documents = CourseDocument.objects.filter(course=course).count()
        completed_documents = DocumentProgress.objects.filter(
            user=user,
            course=course,
            is_completed=True
        ).count()
        
        progress_percentage = (completed_documents / total_documents) * 100 if total_documents > 0 else 0
        
        # Update enrollment progress
        enrollment.progress_percentage = progress_percentage
        enrollment.last_accessed_at = timezone.now()
        enrollment.save()
        
        return Response({
            'success': True,
            'message': 'Document marked as complete',
            'progress_percentage': int(progress_percentage),
            'completed_documents': completed_documents,
            'total_documents': total_documents
        })
        
    except Exception as e:
        return Response({'success': False, 'message': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def enroll_in_course(request, course_id):
    """
    API endpoint for students to enroll in courses
    """
    user = request.user
    
    try:
        from courses.models import Course
        from enrollments.models import Enrollment as CourseEnrollment
        
        # Get course
        course = Course.objects.get(id=course_id)
        
        # Check if user has access to this course
        if user.organization and course.organization != user.organization:
            return Response({
                'success': False,
                'message': 'You do not have access to this course.'
            }, status=403)
        
        # Check if already enrolled
        existing_enrollment = CourseEnrollment.objects.filter(user=user, course=course).first()
        if existing_enrollment:
            return Response({
                'success': False,
                'message': 'You are already enrolled in this course.'
            }, status=400)
        
        # Create enrollment
        enrollment = CourseEnrollment.objects.create(
            user=user,
            course=course,
            status='ACTIVE',
            enrolled_at=timezone.now(),
            is_active=True
        )
        
        return Response({
            'success': True,
            'message': f'Successfully enrolled in {course.title}!',
            'enrollment_id': enrollment.id
        })
        
    except Course.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Course not found.'
        }, status=404)
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
def courses_list_view(request):
    """
    Display all courses for the organization
    """
    user = request.user
    
    # Check permissions
    if not user.is_manager_or_above():
        messages.error(request, 'You do not have permission to view courses.')
        return redirect('dashboard')
    
    try:
        from courses.models import Course
        from django.core.paginator import Paginator
        
        # Get courses for this organization
        if user.is_superadmin():
            courses_queryset = Course.objects.all()
        else:
            courses_queryset = Course.objects.filter(organization=user.organization)
        
        # Filter by status if provided
        status_filter = request.GET.get('status')
        if status_filter:
            courses_queryset = courses_queryset.filter(status=status_filter.upper())
        
        # Search functionality
        search_query = request.GET.get('search')
        if search_query:
            courses_queryset = courses_queryset.filter(
                title__icontains=search_query
            )
        
        # Order by creation date (newest first)
        courses_queryset = courses_queryset.order_by('-created_at')
        
        # Pagination
        paginator = Paginator(courses_queryset, 12)  # 12 courses per page
        page_number = request.GET.get('page')
        courses = paginator.get_page(page_number)
        
        # Statistics
        total_courses = courses_queryset.count()
        published_courses = courses_queryset.filter(status='PUBLISHED').count()
        draft_courses = courses_queryset.filter(status='DRAFT').count()
        
        context = {
            'user': user,
            'page_title': 'All Courses',
            'courses': courses,
            'total_courses': total_courses,
            'published_courses': published_courses,
            'draft_courses': draft_courses,
            'current_status': status_filter,
            'search_query': search_query or '',
        }
        
        return render(request, 'courses/list.html', context)
        
    except ImportError:
        messages.error(request, 'Course system not available.')
        return redirect('dashboard')


@login_required
def student_course_browse(request):
    """
    Student course browsing page with enrollment functionality
    """
    user = request.user
    
    if not user.is_student():
        messages.error(request, 'This page is for students only.')
        return redirect('dashboard')
    
    try:
        from courses.models import Course
        from enrollments.models import Enrollment
        
        # Get student's enrolled course IDs
        enrolled_course_ids = Enrollment.objects.filter(user=user).values_list('course_id', flat=True)
        
        # Get all organization courses for this student
        if user.organization:
            available_courses = Course.objects.filter(
                organization=user.organization
            ).order_by('-created_at')
            logger.debug(
                "student_course_browse: user=%s organization_id=%s org_courses=%s",
                user.id,
                user.organization_id,
                available_courses.count(),
            )
        else:
            available_courses = Course.objects.none()
            logger.debug(
                "student_course_browse: user=%s has no organization, org_courses=0",
                user.id,
            )
        
        # Separate enrolled and available courses
        enrolled_courses = []
        available_for_enrollment = []
        
        for course in available_courses:
            enrollment = Enrollment.objects.filter(user=user, course=course).first()
            if enrollment:
                enrolled_courses.append({
                    'course': course,
                    'enrollment': enrollment,
                    'progress': enrollment.progress_percentage,
                    'status': enrollment.status
                })
            else:
                available_for_enrollment.append(course)
        
        context = {
            'user': user,
            'enrolled_courses': enrolled_courses,
            'available_courses': available_for_enrollment,
            'total_courses': len(enrolled_courses) + len(available_for_enrollment),
            'page_title': 'Course Catalog',
        }
        
        return render(request, 'courses/student_browse.html', context)
        
    except ImportError:
        messages.error(request, 'Course system not available.')
        return redirect('dashboard')


@login_required
def enroll_student(request, course_id):
    """
    Enroll a student in a course
    """
    user = request.user
    
    if not user.is_student():
        messages.error(request, 'Only students can enroll in courses.')
        return redirect('dashboard')
    
    try:
        from courses.models import Course
        from enrollments.models import Enrollment
        
        course = get_object_or_404(Course, id=course_id)

        # Students can only enroll in courses from their own organization
        if not user.organization or course.organization_id != user.organization_id:
            messages.error(request, 'You can only enroll in courses from your organization.')
            return redirect('content:student_course_browse')
        
        # Check if already enrolled
        if Enrollment.objects.filter(user=user, course=course).exists():
            messages.info(request, 'You are already enrolled in this course.')
            return redirect('content:course_detail', course_id=course.id)
        
        # Create enrollment
        enrollment = Enrollment.objects.create(
            user=user,
            course=course,
            status='ACTIVE',
            is_active=True,
            progress_percentage=0,
            enrollment_date=timezone.now(),
            start_date=timezone.now()
        )
        
        messages.success(request, f'Successfully enrolled in {course.title}!')
        return redirect('content:course_detail', course_id=course.id)
        
    except ImportError:
        messages.error(request, 'Enrollment system not available.')
        return redirect('dashboard')


@login_required
def finish_course(request, course_id):
    """
    Mark course as completed and generate certificate
    """
    from django.http import JsonResponse
    user = request.user
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)

    # Allow any authenticated user to complete courses, not just students
    # Remove the role restriction to enable course completion for all user types
    
    try:
        from courses.models import Course
        from enrollments.models import Enrollment
        from certificates.models import Certificate
        from django.utils import timezone
        
        course = get_object_or_404(Course, id=course_id)
        enrollment = Enrollment.objects.filter(user=user, course=course).first()

        if not enrollment:
            enrollment = Enrollment.objects.create(
                user=user,
                course=course,
                status='ACTIVE'
            )
        
        if enrollment.status == 'COMPLETED':
            return JsonResponse({
                'success': True,
                'message': 'Course is already completed.',
                'progress': 100,
                'certificate_url': f'/content/course/{course_id}/certificate/'
            })
        
        # Mark enrollment as completed
        enrollment.status = 'COMPLETED'
        enrollment.progress_percentage = 100
        enrollment.completion_date = timezone.now()
        enrollment.last_accessed_at = timezone.now()
        enrollment.save()
        
        # Generate certificate
        from certificates.models import CertificateTemplate
        
        # Get or create a default template
        template_org = getattr(user, 'organization', None) or getattr(course, 'organization', None)
        template, created = CertificateTemplate.objects.get_or_create(
            name='Default Certificate',
            organization=template_org,
            defaults={
                'description': 'Default certificate template',
                'is_default': True,
                'is_active': True
            }
        )

        certificate = Certificate.objects.filter(
            user=user,
            course=course,
            enrollment=enrollment
        ).order_by('-created_at').first()

        if not certificate:
            certificate = Certificate.objects.create(
                template=template,
                user=user,
                course=course,
                enrollment=enrollment,
                certificate_number=f'CERT-{timezone.now().strftime("%Y%m%d")}-{user.id}-{course.id}',
                verification_code=f'{user.id}-{course.id}-{timezone.now().strftime("%Y%m%d")}',
                completion_date=enrollment.completion_date,
                issued_date=timezone.now(),
                recipient_name=user.get_full_name() or user.email,
                course_name=course.title,
                completion_text='Successfully completed the course',
                status='ISSUED',
                download_url=f'/content/course/{course_id}/certificate/'
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Congratulations! Course completed successfully.',
            'progress': 100,
            'certificate_url': f'/content/course/{course_id}/certificate/',
            'certificate_id': certificate.certificate_number,
            'completion_date': enrollment.completion_date.strftime('%B %d, %Y')
        })
        
    except ImportError:
        return JsonResponse({'success': False, 'message': 'Certificate system not available'}, status=500)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'An error occurred: {str(e)}'}, status=500)


@login_required
def download_certificate(request, course_id):
    """
    Download course certificate as PDF
    """
    user = request.user
    
    try:
        from courses.models import Course
        from enrollments.models import Enrollment
        from certificates.models import Certificate, CertificateTemplate
        from django.http import JsonResponse, FileResponse, Http404
        from django.conf import settings
        import os
        
        course = get_object_or_404(Course, id=course_id)
        
        # Check if user has completed the course
        enrollment = get_object_or_404(Enrollment, user=user, course=course)
        
        if enrollment.status != 'COMPLETED':
            # Don't add message, just return error response
            return JsonResponse({'error': 'You must complete the course before downloading the certificate.'}, status=400)
        
        # Get or create certificate
        try:
            certificate = Certificate.objects.get(user=user, course=course, enrollment=enrollment)
        except Certificate.DoesNotExist:
            # Create new certificate
            template, created = CertificateTemplate.objects.get_or_create(
                name='Default Certificate',
                organization=user.organization,
                defaults={
                    'description': 'Default certificate template',
                    'is_default': True,
                    'is_active': True
                }
            )
            
            certificate = Certificate.objects.create(
                template=template,
                user=user,
                course=course,
                enrollment=enrollment,
                certificate_number=f'CERT-{enrollment.completion_date.strftime("%Y%m%d")}-{user.id}-{course.id}',
                verification_code=f'{user.id}-{course.id}-{enrollment.completion_date.strftime("%Y%m%d")}',
                completion_date=enrollment.completion_date,
                issued_date=enrollment.completion_date,
                recipient_name=user.get_full_name() or user.email,
                course_name=course.title,
                completion_text='Successfully completed the course',
                status='ISSUED',
                download_url=f'/content/course/{course_id}/certificate/'
            )
        
        # Generate PDF certificate
        try:
            from django.template.loader import render_to_string
            from django.http import HttpResponse
            import io
            from reportlab.lib.pagesizes import letter, A4, landscape
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import inch
            from reportlab.lib.colors import black, blue, gold, darkblue
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            
            # Create a PDF in memory
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=landscape(A4))
            width, height = landscape(A4)
            
            # Set up fonts
            # Use default fonts to avoid font registration issues
            title_font = 'Helvetica-Bold'
            text_font = 'Helvetica'
            
            # Draw certificate border
            p.setStrokeColor(black)
            p.setLineWidth(2)
            p.rect(50, 50, width-100, height-100)
            
            # Draw inner border
            p.setStrokeColor(gold if hasattr(gold, 'pattern') else black)
            p.setLineWidth(1)
            p.rect(60, 60, width-120, height-120)
            
            # Title
            p.setFont(title_font, 36)
            p.setFillColor(darkblue)
            p.drawCentredString(width/2, height-120, "Certificate of Completion")
            
            # Subtitle
            p.setFont(text_font, 18)
            p.setFillColor(black)
            p.drawCentredString(width/2, height-160, "This is to certify that")
            
            # Student name
            p.setFont(title_font, 28)
            p.setFillColor(blue)
            student_name = user.get_full_name() or user.email
            p.drawCentredString(width/2, height-210, student_name)
            
            # Underline for name
            p.setStrokeColor(blue)
            p.setLineWidth(1)
            p.line(width/2-150, height-220, width/2+150, height-220)
            
            # Course completion text
            p.setFont(text_font, 16)
            p.setFillColor(black)
            p.drawCentredString(width/2, height-260, "has successfully completed the course")
            
            # Course name
            p.setFont(title_font, 20)
            p.setFillColor(darkblue)
            p.drawCentredString(width/2, height-300, course.title)
            
            # Completion date
            p.setFont(text_font, 14)
            p.setFillColor(black)
            completion_date = enrollment.completion_date.strftime("%B %d, %Y")
            p.drawCentredString(width/2, height-340, f"Completed on {completion_date}")
            
            # Certificate ID
            p.setFont(text_font, 10)
            p.setFillColor(black)
            p.drawCentredString(width/2, height-380, f"Certificate ID: {certificate.certificate_number}")
            
            # Signature lines
            p.setStrokeColor(black)
            p.setLineWidth(1)
            
            # Left signature
            p.line(width/2-200, 120, width/2-50, 120)
            p.setFont(text_font, 12)
            p.drawCentredString(width/2-125, 100, "Course Instructor")
            
            # Right signature
            p.line(width/2+50, 120, width/2+200, 120)
            p.drawCentredString(width/2+125, 100, "Director, AgoraProf LMS")
            
            # Date at bottom
            p.setFont(text_font, 10)
            p.drawCentredString(width/2, 30, f"Issued on {timezone.now().strftime('%B %d, %Y')}")
            
            # Save the PDF
            p.save()
            
            # Get PDF value
            pdf_value = buffer.getvalue()
            buffer.close()
            
            # Create response
            response = HttpResponse(pdf_value, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="certificate_{course.title}_{student_name}.pdf"'
            response['Content-Length'] = len(pdf_value)
            
            return response
            
        except ImportError:
            # If reportlab is not available, create a simple text-based PDF
            from django.template.loader import render_to_string
            from django.http import HttpResponse
            import io
            
            # Create a simple PDF using basic canvas
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=landscape(A4))
            width, height = landscape(A4)
            
            # Simple certificate design
            p.setFont("Helvetica-Bold", 36)
            p.drawCentredString(width/2, height-100, "Certificate of Completion")
            
            p.setFont("Helvetica", 18)
            p.drawCentredString(width/2, height-150, "This is to certify that")
            
            p.setFont("Helvetica-Bold", 24)
            student_name = user.get_full_name() or user.email
            p.drawCentredString(width/2, height-200, student_name)
            
            p.setFont("Helvetica", 16)
            p.drawCentredString(width/2, height-250, "has successfully completed the course")
            
            p.setFont("Helvetica-Bold", 20)
            p.drawCentredString(width/2, height-300, course.title)
            
            p.setFont("Helvetica", 12)
            completion_date = enrollment.completion_date.strftime("%B %d, %Y")
            p.drawCentredString(width/2, height-350, f"Completed on {completion_date}")
            
            p.save()
            
            pdf_value = buffer.getvalue()
            buffer.close()
            
            response = HttpResponse(pdf_value, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="certificate_{course.title}_{student_name}.pdf"'
            return response
            
    except Enrollment.DoesNotExist:
        return JsonResponse({'error': 'You are not enrolled in this course.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Error generating certificate: {str(e)}'}, status=500)


@login_required
def enrollments_list(request):
    """
    Display user's enrollments with real-time data
    """
    user = request.user
    
    try:
        from enrollments.models import Enrollment
        from courses.models import Course
        from certificates.models import Certificate
        from django.utils import timezone
        from datetime import timedelta
        
        # Get user's enrollments
        enrollments = Enrollment.objects.filter(user=user).select_related('course').order_by('-created_at')
        
        # Calculate statistics
        active_count = enrollments.filter(status='ACTIVE').count()
        completed_count = enrollments.filter(status='COMPLETED').count()
        in_progress_count = enrollments.filter(status='IN_PROGRESS').count()
        
        # Calculate average progress and hours learned
        total_progress = sum(enrollment.progress_percentage for enrollment in enrollments)
        avg_progress = total_progress / len(enrollments) if enrollments else 0
        hours_learned = sum(enrollment.progress_percentage * 0.1 for enrollment in enrollments)  # Estimate
        
        context = {
            'enrollments': enrollments,
            'active_count': active_count,
            'completed_count': completed_count,
            'in_progress_count': in_progress_count,
            'total_count': len(enrollments),
            'hours_learned': round(hours_learned, 1),
            'avg_progress': round(avg_progress, 1),
            'user': user,
        }
        
        return render(request, 'enrollments/list.html', context)
        
    except ImportError:
        # If enrollment models are not available, show empty state
        context = {
            'enrollments': [],
            'active_count': 0,
            'completed_count': 0,
            'in_progress_count': 0,
            'total_count': 0,
            'hours_learned': 0,
            'avg_progress': 0,
            'user': user,
        }
        
        return render(request, 'enrollments/list.html', context)


@login_required
def update_progress(request, course_id):
    """
    Update course progress for a student
    """
    from django.http import JsonResponse
    user = request.user
    
    if not user.is_student():
        return JsonResponse({'error': 'Only students can update progress'}, status=403)
    
    try:
        from django.http import JsonResponse
        from courses.models import Course, CourseDocument
        from enrollments.models import Enrollment, DocumentProgress
        from django.utils import timezone
        
        course = get_object_or_404(Course, id=course_id)
        enrollment = get_object_or_404(Enrollment, user=user, course=course)
        
        if enrollment.status == 'COMPLETED':
            return JsonResponse({'error': 'Course is already completed'}, status=400)
        
        # Get action from request
        action = request.POST.get('action', 'complete_document')
        
        if action == 'complete_document':
            document_id = request.POST.get('document_id')
            
            if not document_id:
                return JsonResponse({'error': 'Document ID is required'}, status=400)
            
            try:
                document = CourseDocument.objects.get(id=document_id, course=course)
                
                # Create or update document progress
                progress, created = DocumentProgress.objects.update_or_create(
                    user=user,
                    course=course,
                    document=document,
                    defaults={
                        'is_completed': True,
                        'completed_at': timezone.now()
                    }
                )
                
                if created:
                    # Recalculate course progress
                    total_documents = CourseDocument.objects.filter(course=course).count()
                    completed_documents = DocumentProgress.objects.filter(
                        user=user,
                        course=course,
                        is_completed=True
                    ).count()
                    
                    new_progress = (completed_documents / total_documents) * 100
                    enrollment.progress_percentage = new_progress
                    enrollment.last_accessed_at = timezone.now()
                    
                    # Check if course is completed
                    if new_progress >= 100:
                        enrollment.status = 'COMPLETED'
                        enrollment.completion_date = timezone.now()
                        
                        # Generate certificate
                        try:
                            from certificates.models import Certificate
                            certificate, created = Certificate.objects.get_or_create(
                                user=user,
                                course=course,
                                defaults={
                                    'issued_date': enrollment.completion_date,
                                    'certificate_url': f'/content/course/{course_id}/certificate/',
                                    'certificate_id': f'CERT-{timezone.now().strftime("%Y%m%d")}-{user.id}-{course.id}',
                                    'verification_code': f'{user.id}-{course.id}-{timezone.now().strftime("%Y%m%d")}'
                                }
                            )
                        except ImportError:
                            pass  # Certificate system not available
                    else:
                        enrollment.status = 'ACTIVE'
                    
                    enrollment.save()
                    
                    return JsonResponse({
                        'success': True,
                        'message': f'Document "{document.title}" marked as complete',
                        'progress': new_progress,
                        'total_documents': total_documents,
                        'completed_documents': completed_documents,
                        'document_completed': True,
                        'course_completed': new_progress >= 100,
                        'certificate_url': f'/content/course/{course_id}/certificate/' if new_progress >= 100 else None
                    })
                else:
                    return JsonResponse({
                        'success': True,
                        'message': f'Document "{document.title}" was already completed',
                        'progress': enrollment.progress_percentage
                    })
                    
            except CourseDocument.DoesNotExist:
                return JsonResponse({'error': 'Document not found'}, status=404)
            except Exception as e:
                return JsonResponse({'error': f'Error updating progress: {str(e)}'}, status=500)
        
        return JsonResponse({'error': 'Invalid action'}, status=400)
        
    except ImportError:
        return JsonResponse({'error': 'Progress tracking system not available'}, status=500)
