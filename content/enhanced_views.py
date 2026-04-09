from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files.storage import default_storage
from django.utils.text import slugify
from django.http import JsonResponse
from django.db import transaction
import uuid
import os

from courses.enhanced_models import EnhancedCourse, CourseFile
from accounts.models import User


@login_required
def enhanced_course_create_view(request):
    """
    Enhanced course creation with file upload and proper frontend integration
    """
    user = request.user
    
    # Check permissions - managers and admins can create courses
    if not user.is_manager_or_above():
        messages.error(request, 'You do not have permission to create courses.')
        return redirect('dashboard')
    
    context = {
        'user': user,
        'page_title': 'Create Course',
        'categories': EnhancedCourse._meta.get_field('category').choices,
        'difficulties': EnhancedCourse._meta.get_field('difficulty').choices,
    }
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Validate required fields
                title = request.POST.get('title', '').strip()
                description = request.POST.get('full_description', '').strip()
                duration = request.POST.get('duration', '0')
                max_students = request.POST.get('max_students', '50')
                difficulty = request.POST.get('difficulty', 'BEGINNER')
                category = request.POST.get('category', 'technical')
                
                if not title:
                    messages.error(request, 'Course title is required.')
                    return render(request, 'courses/enhanced_create.html', context)
                
                if not description:
                    messages.error(request, 'Course description is required.')
                    return render(request, 'courses/enhanced_create.html', context)
                
                # Validate numeric fields
                try:
                    duration = float(duration)
                    if duration <= 0:
                        messages.error(request, 'Duration must be greater than 0.')
                        return render(request, 'courses/enhanced_create.html', context)
                except ValueError:
                    messages.error(request, 'Invalid duration value.')
                    return render(request, 'courses/enhanced_create.html', context)
                
                try:
                    max_students = int(max_students)
                    if max_students <= 0:
                        messages.error(request, 'Max students must be greater than 0.')
                        return render(request, 'courses/enhanced_create.html', context)
                except ValueError:
                    messages.error(request, 'Invalid max students value.')
                    return render(request, 'courses/enhanced_create.html', context)
                
                # Generate unique slug
                base_slug = slugify(title)
                unique_slug = base_slug
                counter = 1
                
                while EnhancedCourse.objects.filter(
                    slug=unique_slug, 
                    organization=user.organization
                ).exists():
                    unique_slug = f"{base_slug}-{counter}"
                    counter += 1
                
                # Create course
                course = EnhancedCourse.objects.create(
                    title=title,
                    slug=unique_slug,
                    description=description,
                    short_description=request.POST.get('short_description', '').strip(),
                    category=category,
                    difficulty=difficulty,
                    duration_hours=duration,
                    max_students=max_students,
                    prerequisites=request.POST.get('prerequisites', '').strip(),
                    objectives=request.POST.get('objectives', '').strip(),
                    outcomes=request.POST.get('outcomes', '').strip(),
                    language=request.POST.get('language', 'en'),
                    certificate_enabled=request.POST.get('certificate_enabled') == 'on',
                    is_featured=request.POST.get('is_featured') == 'on',
                    organization=user.organization,
                    created_by=user,
                    status='PUBLISHED' if user.is_admin_or_above() else 'DRAFT'
                )
                
                # Handle file uploads
                uploaded_files = request.FILES.getlist('course_documents')
                file_count = 0
                
                for uploaded_file in uploaded_files:
                    if uploaded_file.name.lower().endswith('.pdf'):
                        # Determine file type
                        file_type = 'PDF'
                        if uploaded_file.name.lower().endswith('.mp4'):
                            file_type = 'VIDEO'
                        elif uploaded_file.name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                            file_type = 'IMAGE'
                        elif uploaded_file.name.lower().endswith(('.doc', '.docx')):
                            file_type = 'DOCUMENT'
                        
                        # Create unique filename
                        file_extension = os.path.splitext(uploaded_file.name)[1]
                        unique_filename = f"course_{course.id}_{uuid.uuid4().hex[:8]}{file_extension}"
                        
                        # Save file
                        file_path = default_storage.save(f'course_files/{unique_filename}', uploaded_file)
                        
                        # Create CourseFile record
                        CourseFile.objects.create(
                            course=course,
                            title=os.path.splitext(uploaded_file.name)[0],
                            description=f"Uploaded with course creation",
                            file=file_path,
                            file_type=file_type,
                            file_size=uploaded_file.size,
                            mime_type=uploaded_file.content_type or 'application/octet-stream',
                            uploaded_by=user,
                            organization=user.organization,
                            order=file_count
                        )
                        file_count += 1
                
                messages.success(
                    request, 
                    f'🎉 Course "{course.title}" created successfully! '
                    f'Your course has been set up with {file_count} file(s) and is now ready for students. '
                    f'You can view and manage your course from the course details page.'
                )
                return redirect('content:enhanced_course_detail', course_id=course.id)
                
        except Exception as e:
            messages.error(request, f'Error creating course: {str(e)}')
            return render(request, 'courses/enhanced_create.html', context)
    
    return render(request, 'courses/enhanced_create.html', context)


@login_required
def enhanced_course_detail_view(request, course_id):
    """
    Enhanced course detail view with proper file display
    """
    user = request.user
    
    try:
        course = EnhancedCourse.objects.get(id=course_id)
        
        # Check access permissions
        # Superadmins can access all courses
        if not user.is_superadmin() and user.organization and course.organization != user.organization:
            messages.error(request, 'You do not have access to this course.')
            return redirect('content:courses_browse')
        
        # Get course files - Allow access for enrolled students
        from enrollments.models import Enrollment
        
        # Check if user is enrolled in this course
        is_enrolled = Enrollment.objects.filter(user=user, course=course).exists()
        
        if user.is_manager_or_above() or user == course.created_by or is_enrolled:
            files = CourseFile.objects.filter(
                course=course,
                is_active=True
            ).order_by('order', 'created_at')
        
        # Check if user can edit
        can_edit = course.can_be_edited_by(user)
        can_delete = course.can_be_deleted_by(user)
        
        context = {
            'user': user,
            'course': course,
            'files': files,
            'can_edit': can_edit,
            'can_delete': can_delete,
            'total_files': len(files),
            'page_title': course.title,
        }
        
        return render(request, 'courses/enhanced_detail.html', context)
        
    except EnhancedCourse.DoesNotExist:
        messages.error(request, 'Course not found.')
        return redirect('content:courses_browse')
    except Exception as e:
        messages.error(request, f'Error loading course: {str(e)}')
        return redirect('content:courses_browse')


@login_required
def enhanced_course_edit_view(request, course_id):
    """
    Enhanced course edit view
    """
    user = request.user
    
    try:
        course = EnhancedCourse.objects.get(id=course_id)
        
        # Check edit permissions
        if not course.can_be_edited_by(user):
            messages.error(request, 'You do not have permission to edit this course.')
            return redirect('content:courses_browse')
        
        context = {
            'user': user,
            'course': course,
            'categories': EnhancedCourse._meta.get_field('category').choices,
            'difficulties': EnhancedCourse._meta.get_field('difficulty').choices,
            'page_title': f'Edit Course - {course.title}',
        }
        
        return render(request, 'courses/enhanced_edit.html', context)
        
    except EnhancedCourse.DoesNotExist:
        messages.error(request, 'Course not found.')
        return redirect('content:courses_browse')
    except Exception as e:
        messages.error(request, f'Error loading course: {str(e)}')
        return redirect('content:courses_browse')


@login_required
def enhanced_course_update_view(request, course_id):
    """
    Enhanced course update view
    """
    user = request.user
    
    try:
        with transaction.atomic():
            course = EnhancedCourse.objects.get(id=course_id)
            
            # Check edit permissions
            if not course.can_be_edited_by(user):
                messages.error(request, 'You do not have permission to update this course.')
                return redirect('content:courses_browse')
            
            if request.method == 'POST':
                # Validate required fields
                title = request.POST.get('title', '').strip()
                description = request.POST.get('full_description', '').strip()
                duration = request.POST.get('duration', '0')
                max_students = request.POST.get('max_students', '50')
                difficulty = request.POST.get('difficulty', 'BEGINNER')
                category = request.POST.get('category', 'technical')
                
                if not title:
                    messages.error(request, 'Course title is required.')
                    return redirect('content:enhanced_course_edit', course_id=course.id)
                
                if not description:
                    messages.error(request, 'Course description is required.')
                    return redirect('content:enhanced_course_edit', course_id=course.id)
                
                # Validate numeric fields
                try:
                    duration = float(duration)
                    if duration <= 0:
                        messages.error(request, 'Duration must be greater than 0.')
                        return redirect('content:enhanced_course_edit', course_id=course.id)
                except ValueError:
                    messages.error(request, 'Invalid duration value.')
                    return redirect('content:enhanced_course_edit', course_id=course.id)
                
                try:
                    max_students = int(max_students)
                    if max_students <= 0:
                        messages.error(request, 'Max students must be greater than 0.')
                        return redirect('content:enhanced_course_edit', course_id=course.id)
                except ValueError:
                    messages.error(request, 'Invalid max students value.')
                    return redirect('content:enhanced_course_edit', course_id=course.id)
                
                # Update slug if title changed
                if title != course.title:
                    base_slug = slugify(title)
                    unique_slug = base_slug
                    counter = 1
                    
                    while EnhancedCourse.objects.filter(
                        slug=unique_slug, 
                        organization=course.organization
                    ).exclude(id=course.id).exists():
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
                course.prerequisites = request.POST.get('prerequisites', '').strip()
                course.objectives = request.POST.get('objectives', '').strip()
                course.outcomes = request.POST.get('outcomes', '').strip()
                course.language = request.POST.get('language', 'en')
                course.certificate_enabled = request.POST.get('certificate_enabled') == 'on'
                course.is_featured = request.POST.get('is_featured') == 'on'
                course.status = request.POST.get('status', 'DRAFT')
                course.save()
                
                messages.success(request, f'🎉 Course "{course.title}" updated successfully!')
                return redirect('content:enhanced_course_detail', course_id=course.id)
            
            # If not POST, redirect to edit page
            return redirect('content:enhanced_course_edit', course_id=course.id)
            
    except EnhancedCourse.DoesNotExist:
        messages.error(request, 'Course not found.')
        return redirect('content:courses_browse')
    except Exception as e:
        messages.error(request, f'Error updating course: {str(e)}')
        return redirect('content:courses_browse')


@login_required
def enhanced_course_delete_view(request, course_id):
    """
    Enhanced course delete view
    """
    user = request.user
    
    try:
        course = EnhancedCourse.objects.get(id=course_id)
        
        # Check delete permissions
        if not course.can_be_deleted_by(user):
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
        
        return render(request, 'courses/enhanced_delete.html', context)
        
    except EnhancedCourse.DoesNotExist:
        messages.error(request, 'Course not found.')
        return redirect('content:courses_browse')
    except Exception as e:
        messages.error(request, f'Error deleting course: {str(e)}')
        return redirect('content:courses_browse')


@login_required
def enhanced_courses_list_view(request):
    """
    Enhanced courses list view with proper filtering
    """
    user = request.user
    
    # Check permissions
    if not user.is_manager_or_above():
        messages.error(request, 'You do not have permission to view courses.')
        return redirect('dashboard')
    
    try:
        # Get courses for this organization
        if user.is_superadmin():
            courses_queryset = EnhancedCourse.objects.all()
        else:
            courses_queryset = EnhancedCourse.objects.filter(organization=user.organization)
        
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
        
        # Statistics
        total_courses = courses_queryset.count()
        published_courses = courses_queryset.filter(status='PUBLISHED').count()
        draft_courses = courses_queryset.filter(status='DRAFT').count()
        
        context = {
            'user': user,
            'courses': courses_queryset,
            'total_courses': total_courses,
            'published_courses': published_courses,
            'draft_courses': draft_courses,
            'page_title': 'All Courses',
        }
        
        return render(request, 'courses/enhanced_list.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading courses: {str(e)}')
        return redirect('dashboard')


# API endpoints for frontend
@login_required
def api_upload_course_file(request, course_id):
    """
    API endpoint for uploading additional files to a course
    """
    user = request.user
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        course = EnhancedCourse.objects.get(id=course_id)
        
        # Check permissions
        if not course.can_be_edited_by(user):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No file provided'}, status=400)
        
        uploaded_file = request.FILES['file']
        
        # Validate file size (50MB limit)
        if uploaded_file.size > 50 * 1024 * 1024:
            return JsonResponse({'error': 'File size exceeds 50MB limit'}, status=400)
        
        # Determine file type
        file_type = 'DOCUMENT'
        if uploaded_file.name.lower().endswith('.pdf'):
            file_type = 'PDF'
        elif uploaded_file.name.lower().endswith(('.mp4', '.avi', '.mov')):
            file_type = 'VIDEO'
        elif uploaded_file.name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
            file_type = 'IMAGE'
        elif uploaded_file.name.lower().endswith(('.doc', '.docx')):
            file_type = 'DOCUMENT'
        
        # Create unique filename
        file_extension = os.path.splitext(uploaded_file.name)[1]
        unique_filename = f"course_{course.id}_{uuid.uuid4().hex[:8]}{file_extension}"
        
        # Save file
        file_path = default_storage.save(f'course_files/{unique_filename}', uploaded_file)
        
        # Create CourseFile record
        course_file = CourseFile.objects.create(
            course=course,
            title=request.POST.get('title', os.path.splitext(uploaded_file.name)[0]),
            description=request.POST.get('description', ''),
            file=file_path,
            file_type=file_type,
            file_size=uploaded_file.size,
            mime_type=uploaded_file.content_type or 'application/octet-stream',
            uploaded_by=user,
            organization=user.organization,
            order=request.POST.get('order', 0)
        )
        
        return JsonResponse({
            'success': True,
            'file': {
                'id': str(course_file.id),
                'title': course_file.title,
                'file_type': course_file.get_file_type_display(),
                'file_size': course_file.file_size_display,
                'created_at': course_file.created_at.isoformat(),
                'download_url': course_file.file.url if course_file.file else None
            }
        })
        
    except EnhancedCourse.DoesNotExist:
        return JsonResponse({'error': 'Course not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
