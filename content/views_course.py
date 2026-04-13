from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)


@login_required
def course_create(request):
    """
    Course creation form for managers with automatic approval workflow
    """
    user = request.user
    
    # Check permissions - only managers and admins can create courses
    if not user.is_manager_or_above():
        messages.error(request, 'You do not have permission to create courses.')
        return redirect('dashboard')

    try:
        from courses.models import Course, Category
        from content.models import CourseApproval
        from organizations.models import Organization
        
        if request.method == 'POST':
            action = request.POST.get('action')
            
            if action == 'create_course':
                # Extract course data
                title = request.POST.get('title')
                description = request.POST.get('description')
                short_description = request.POST.get('short_description', '')
                category_id = request.POST.get('category')
                difficulty_level = request.POST.get('difficulty_level', 'BEGINNER')
                duration_hours = request.POST.get('duration_hours', 0)
                price = request.POST.get('price', 0)
                language = request.POST.get('language', 'en')
                is_free = request.POST.get('is_free') == 'on'
                is_public = request.POST.get('is_public') == 'on'
                allow_reviews = request.POST.get('allow_reviews') == 'on'
                certificate_enabled = request.POST.get('certificate_enabled') == 'on'
                auto_enroll = request.POST.get('auto_enroll') == 'on'
                
                # Approval settings
                requires_approval = request.POST.get('requires_approval', 'on') == 'on'
                priority = request.POST.get('priority', 'NORMAL')
                approval_notes = request.POST.get('approval_notes', '')
                
                # Learning objectives
                learning_objectives = request.POST.getlist('learning_objectives')
                learning_objectives = [obj.strip() for obj in learning_objectives if obj.strip()]
                
                # Prerequisites
                prerequisites = request.POST.getlist('prerequisites')
                prerequisites = [req.strip() for req in prerequisites if req.strip()]
                
                if title and description:
                    # Get category
                    category = None
                    if category_id:
                        try:
                            category = Category.objects.get(id=category_id, organization=user.organization)
                        except Category.DoesNotExist:
                            category = None
                    
                    # Create course
                    course = Course.objects.create(
                        title=title,
                        description=description,
                        short_description=short_description,
                        category=category,
                        instructor=user,
                        organization=user.organization,
                        difficulty_level=difficulty_level,
                        duration_hours=int(duration_hours) if duration_hours else 0,
                        price=float(price) if price else 0.0,
                        language=language,
                        is_free=is_free,
                        is_public=is_public,
                        allow_reviews=allow_reviews,
                        certificate_enabled=certificate_enabled,
                        auto_enroll=auto_enroll,
                        status='DRAFT',  # Manager courses start as DRAFT
                        learning_objectives=learning_objectives,
                        prerequisites=prerequisites,
                        is_active=True,
                        created_at=timezone.now(),
                        updated_at=timezone.now()
                    )
                    
                    # Create approval request if required
                    if requires_approval and user.is_manager():
                        approval = CourseApproval.objects.create(
                            course=course,
                            submitted_by=user,
                            priority=priority,
                            review_notes=approval_notes,
                            submitted_at=timezone.now()
                        )
                        
                        # Run automated checks
                        approval.run_automated_checks()
                        
                        messages.success(request, f'Course "{title}" created and submitted for approval.')
                    else:
                        # Admins can publish directly
                        if user.is_admin_or_above():
                            course.status = 'PUBLISHED'
                            course.save(update_fields=['status'])
                            messages.success(request, f'Course "{title}" created and published.')
                        else:
                            messages.success(request, f'Course "{title}" created as draft.')
                    
                    return redirect('content:course_manage')
                else:
                    messages.error(request, 'Please provide both title and description.')
            
            elif action == 'save_draft':
                # Save as draft without approval
                title = request.POST.get('title')
                description = request.POST.get('description')
                
                if title and description:
                    course = Course.objects.create(
                        title=title,
                        description=description,
                        instructor=user,
                        organization=user.organization,
                        status='DRAFT',
                        is_active=True,
                        created_at=timezone.now(),
                        updated_at=timezone.now()
                    )
                    
                    messages.success(request, f'Course draft "{title}" saved.')
                    return redirect('content:course_manage')
                else:
                    messages.error(request, 'Please provide both title and description.')
        
        # Get categories for the organization
        categories = Category.objects.filter(
            organization=user.organization,
            is_active=True
        ).order_by('name')
        
        # Get existing courses for prerequisites
        existing_courses = Course.objects.filter(
            organization=user.organization,
            is_active=True,
            status='PUBLISHED'
        ).exclude(instructor=user).order_by('title')
        
        context = {
            'user': user,
            'page_title': 'Create Course',
            'categories': categories,
            'existing_courses': existing_courses,
            'difficulty_choices': Course.DIFFICULTY_LEVELS,
            'language_choices': Course.LANGUAGE_CHOICES,
            'priority_choices': CourseApproval.PRIORITY_LEVELS,
            'is_manager': user.is_manager(),
            'is_admin': user.is_admin_or_above(),
        }
        
    except ImportError as e:
        messages.error(request, 'Course creation features are not available. Please contact administrator.')
        context = {
            'user': user,
            'page_title': 'Create Course',
            'categories': [],
            'existing_courses': [],
            'difficulty_choices': [],
            'language_choices': [],
            'priority_choices': [],
            'is_manager': user.is_manager(),
            'is_admin': user.is_admin_or_above(),
        }

    return render(request, 'content/course_create.html', context)


@login_required
def course_edit(request, course_id):
    """
    Edit existing course with approval workflow for managers
    """
    user = request.user
    
    try:
        from courses.models import Course
        from content.models import CourseApproval
        
        course = get_object_or_404(Course, id=course_id)
        
        # Check permissions
        if not user.can_manage_course(course):
            messages.error(request, 'You do not have permission to edit this course.')
            return redirect('dashboard')
        
        # Check if course has approval request
        approval = getattr(course, 'approval_request', None)
        
        if request.method == 'POST':
            action = request.POST.get('action')
            
            if action == 'update_course':
                # Get form data
                title = request.POST.get('title')
                description = request.POST.get('description')
                short_description = request.POST.get('short_description', '')
                category_id = request.POST.get('category')
                difficulty_level = request.POST.get('difficulty_level', 'BEGINNER')
                duration_hours = request.POST.get('duration_hours', 0)
                price = request.POST.get('price', 0)
                language = request.POST.get('language', 'en')
                is_free = request.POST.get('is_free') == 'on'
                is_public = request.POST.get('is_public') == 'on'
                allow_reviews = request.POST.get('allow_reviews') == 'on'
                certificate_enabled = request.POST.get('certificate_enabled') == 'on'
                auto_enroll = request.POST.get('auto_enroll') == 'on'
                
                # Learning objectives
                learning_objectives = request.POST.getlist('learning_objectives')
                learning_objectives = [obj.strip() for obj in learning_objectives if obj.strip()]
                
                # Prerequisites
                prerequisites = request.POST.getlist('prerequisites')
                prerequisites = [req.strip() for req in prerequisites if req.strip()]
                
                if title and description:
                    # Update course
                    course.title = title
                    course.description = description
                    course.short_description = short_description
                    course.difficulty_level = difficulty_level
                    course.duration_hours = int(duration_hours) if duration_hours else 0
                    course.price = float(price) if price else 0.0
                    course.language = language
                    course.is_free = is_free
                    course.is_public = is_public
                    course.allow_reviews = allow_reviews
                    course.certificate_enabled = certificate_enabled
                    course.auto_enroll = auto_enroll
                    course.learning_objectives = learning_objectives
                    course.prerequisites = prerequisites
                    course.updated_at = timezone.now()
                    
                    # Update category
                    if category_id:
                        try:
                            category = Category.objects.get(id=category_id, organization=user.organization)
                            course.category = category
                        except Category.DoesNotExist:
                            course.category = None
                    
                    # Handle approval workflow for managers
                    if user.is_manager() and course.status == 'PUBLISHED':
                        # If manager edits published course, it needs re-approval
                        course.status = 'DRAFT'
                        
                        # Create or update approval request
                        if approval:
                            approval.status = 'PENDING'
                            approval.reviewed_by = None
                            approval.reviewed_at = None
                            approval.approved_by = None
                            approval.approved_at = None
                            approval.submitted_at = timezone.now()
                            approval.save()
                        else:
                            approval = CourseApproval.objects.create(
                                course=course,
                                submitted_by=user,
                                priority='NORMAL',
                                submitted_at=timezone.now()
                            )
                            approval.run_automated_checks()
                        
                        messages.success(request, f'Course "{title}" updated and resubmitted for approval.')
                    else:
                        course.save()
                        messages.success(request, f'Course "{title}" updated successfully.')
                    
                    return redirect('content:course_manage')
                else:
                    messages.error(request, 'Please provide both title and description.')
            
            elif action == 'resubmit_for_approval':
                if approval and approval.status == 'RETURNED':
                    if approval.resubmit():
                        messages.success(request, f'Course "{course.title}" resubmitted for approval.')
                    else:
                        messages.error(request, 'Unable to resubmit course for approval.')
                else:
                    messages.error(request, 'Course cannot be resubmitted.')
                
                return redirect('content:course_edit', course_id=course_id)
        
        # Get categories and existing courses
        categories = Category.objects.filter(
            organization=user.organization,
            is_active=True
        ).order_by('name')
        
        existing_courses = Course.objects.filter(
            organization=user.organization,
            is_active=True,
            status='PUBLISHED'
        ).exclude(id=course.id).order_by('title')
        
        context = {
            'user': user,
            'page_title': f'Edit Course: {course.title}',
            'course': course,
            'approval': approval,
            'categories': categories,
            'existing_courses': existing_courses,
            'difficulty_choices': Course.DIFFICULTY_LEVELS,
            'language_choices': Course.LANGUAGE_CHOICES,
            'is_manager': user.is_manager(),
            'is_admin': user.is_admin_or_above(),
        }
        
    except ImportError as e:
        messages.error(request, 'Course editing features are not available. Please contact administrator.')
        return redirect('dashboard')

    return render(request, 'content/course_edit.html', context)


@login_required
def course_manage(request):
    """
    Course management page for managers and admins
    """
    user = request.user
    
    # Check permissions
    if not user.is_manager_or_above():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')

    try:
        from courses.models import Course
        from content.models import CourseApproval
        from django.core.paginator import Paginator
        
        # Get courses based on user role
        if user.is_superadmin():
            courses = Course.objects.select_related('instructor', 'organization', 'category').all()
        elif user.is_admin_or_above():
            courses = Course.objects.select_related('instructor', 'organization', 'category').filter(
                organization=user.organization
            )
        else:  # Manager
            courses = Course.objects.select_related('instructor', 'organization', 'category').filter(
                instructor=user
            )
        
        # Filter by status
        status_filter = request.GET.get('status')
        if status_filter:
            courses = courses.filter(status=status_filter)
        
        # Search
        search_query = request.GET.get('search')
        if search_query:
            courses = courses.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # Pagination
        paginator = Paginator(courses, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Get approval statistics for managers
        approval_stats = {}
        if user.is_manager():
            my_approvals = CourseApproval.objects.filter(
                submitted_by=user
            ).select_related('course')
            
            approval_stats = {
                'pending': my_approvals.filter(status='PENDING').count(),
                'under_review': my_approvals.filter(status='UNDER_REVIEW').count(),
                'approved': my_approvals.filter(status='APPROVED').count(),
                'rejected': my_approvals.filter(status='REJECTED').count(),
                'returned': my_approvals.filter(status='RETURNED').count(),
            }
        
        context = {
            'user': user,
            'page_title': 'Manage Courses',
            'courses': page_obj,
            'approval_stats': approval_stats,
            'status_choices': Course.STATUS_CHOICES,
        }
        
    except ImportError as e:
        messages.error(request, 'Course management features are not available. Please contact administrator.')
        context = {
            'user': user,
            'page_title': 'Manage Courses',
            'courses': [],
            'approval_stats': {},
            'status_choices': [],
        }

    return render(request, 'content/course_manage.html', context)
