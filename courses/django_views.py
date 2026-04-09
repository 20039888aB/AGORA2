from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db.models import Q
from django.utils.decorators import method_decorator

from .models import Course, CourseDocument
from .forms import CourseDocumentForm, CourseDocumentBulkForm


@login_required
def course_documents(request, course_id):
    """
    Enhanced view and manage course documents with admin features
    """
    course = get_object_or_404(Course, id=course_id)
    
    user_org_id = getattr(request.user, 'organization_id', None)
    course_org_id = getattr(course, 'organization_id', None)

    is_admin = request.user.is_admin_or_above()
    is_instructor = (request.user == course.instructor) or (
        user_org_id == course_org_id and request.user.is_instructor()
    )
    is_manager = user_org_id == course_org_id and request.user.is_manager()
    is_org_member = user_org_id == course_org_id

    can_view_documents = is_admin or is_instructor or is_manager or is_org_member
    can_manage_documents = is_admin or is_instructor or is_manager

    if not can_view_documents:
        messages.error(request, 'You do not have permission to view documents for this course.')
        return redirect('dashboard')
    
    documents = CourseDocument.objects.filter(course=course).order_by('order', 'created_at')
    
    # Enhanced context with admin statistics
    context = {
        'course': course,
        'documents': documents,
        'page_title': f'Documents - {course.title}',
        'is_admin': is_admin,
        'is_instructor': is_instructor,
        'is_manager': is_manager,
        'is_org_member': is_org_member,
        'can_manage_documents': can_manage_documents,
        'can_add_document': can_manage_documents,
        'total_documents': documents.count(),
        'total_size': sum(doc.file_size or 0 for doc in documents if doc.file_size),
        'required_documents': documents.filter(is_required=True).count(),
        'pdf_documents': documents.filter(file_type='PDF').count(),
        'other_documents': documents.exclude(file_type='PDF').count(),
        'can_bulk_upload': is_admin,  # Only admins can bulk upload
        'can_reorder': can_manage_documents,
    }
    
    return render(request, 'courses/documents/list.html', context)


@login_required
def add_course_document(request, course_id):
    """
    Add a new document to a course
    """
    course = get_object_or_404(Course, id=course_id)
    
    # Check permissions
    if not (request.user.is_admin_or_above() or 
            (request.user == course.instructor) or 
            (request.user.organization == course.organization and request.user.is_instructor())):
        messages.error(request, 'You do not have permission to add documents to this course.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CourseDocumentForm(request.POST, request.FILES, course=course)
        if form.is_valid():
            document = form.save()
            messages.success(request, f'Document "{document.title}" has been added successfully.')
            return redirect('course_documents', course_id=course.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CourseDocumentForm(course=course)
    
    context = {
        'course': course,
        'form': form,
        'page_title': f'Add Document - {course.title}',
        'action': 'Add'
    }
    
    return render(request, 'courses/documents/form.html', context)


@login_required
def edit_course_document(request, course_id, document_id):
    """
    Edit an existing course document
    """
    course = get_object_or_404(Course, id=course_id)
    document = get_object_or_404(CourseDocument, id=document_id, course=course)
    
    # Check permissions
    if not (request.user.is_admin_or_above() or 
            (request.user == course.instructor) or 
            (request.user.organization == course.organization and request.user.is_instructor())):
        messages.error(request, 'You do not have permission to edit documents for this course.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CourseDocumentForm(request.POST, request.FILES, instance=document, course=course)
        if form.is_valid():
            document = form.save()
            messages.success(request, f'Document "{document.title}" has been updated successfully.')
            return redirect('course_documents', course_id=course.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CourseDocumentForm(instance=document, course=course)
    
    context = {
        'course': course,
        'document': document,
        'form': form,
        'page_title': f'Edit Document - {course.title}',
        'action': 'Edit'
    }
    
    return render(request, 'courses/documents/form.html', context)


@login_required
def delete_course_document(request, course_id, document_id):
    """
    Delete a course document
    """
    course = get_object_or_404(Course, id=course_id)
    document = get_object_or_404(CourseDocument, id=document_id, course=course)
    
    # Check permissions
    if not (request.user.is_admin_or_above() or 
            (request.user == course.instructor) or 
            (request.user.organization == course.organization and request.user.is_instructor())):
        messages.error(request, 'You do not have permission to delete documents for this course.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        title = document.title
        document.delete()
        messages.success(request, f'Document "{title}" has been deleted successfully.')
        return redirect('course_documents', course_id=course.id)
    
    context = {
        'course': course,
        'document': document,
        'page_title': f'Delete Document - {course.title}',
    }
    
    return render(request, 'courses/documents/delete.html', context)


@login_required
def bulk_upload_documents(request, course_id):
    """
    Bulk upload documents to a course
    """
    course = get_object_or_404(Course, id=course_id)
    
    # Check permissions
    if not (request.user.is_admin_or_above() or 
            (request.user == course.instructor) or 
            (request.user.organization == course.organization and request.user.is_instructor())):
        messages.error(request, 'You do not have permission to upload documents to this course.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CourseDocumentBulkForm(request.POST, request.FILES)
        files = request.FILES.getlist('files')
        
        if files:
            uploaded_count = 0
            for file in files:
                # Create document for each file
                document = CourseDocument(
                    course=course,
                    title=file.name.replace('_', ' ').replace('-', ' ').split('.')[0],
                    file=file,
                    file_size=file.size,
                    file_type='PDF' if file.name.lower().endswith('.pdf') else 'OTHER',
                    order=CourseDocument.objects.filter(course=course).count() + uploaded_count + 1
                )
                document.save()
                uploaded_count += 1
            
            messages.success(request, f'Successfully uploaded {uploaded_count} documents.')
            return redirect('course_documents', course_id=course.id)
        else:
            messages.error(request, 'Please select at least one file to upload.')
    else:
        form = CourseDocumentBulkForm()
    
    context = {
        'course': course,
        'form': form,
        'page_title': f'Bulk Upload Documents - {course.title}',
    }
    
    return render(request, 'courses/documents/bulk_upload.html', context)


@login_required
def reorder_documents(request, course_id):
    """
    Reorder course documents
    """
    course = get_object_or_404(Course, id=course_id)
    
    # Check permissions
    if not (request.user.is_admin_or_above() or 
            (request.user == course.instructor) or 
            (request.user.organization == course.organization and request.user.is_instructor())):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if request.method == 'POST':
        document_orders = request.POST.get('document_orders', '')
        
        if document_orders:
            try:
                # Parse the document orders (format: "doc_id1:order1,doc_id2:order2")
                orders = {}
                for item in document_orders.split(','):
                    if ':' in item:
                        doc_id, order = item.split(':')
                        orders[doc_id.strip()] = int(order.strip())
                
                # Update document orders
                for doc_id, order in orders.items():
                    CourseDocument.objects.filter(id=doc_id, course=course).update(order=order)
                
                return JsonResponse({'success': True, 'message': 'Documents reordered successfully'})
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=400)
        else:
            return JsonResponse({'error': 'No document orders provided'}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def student_course_documents(request, course_id):
    """
    Student view for course documents - read-only access
    """
    course = get_object_or_404(Course, id=course_id)
    
    # Check if student is enrolled or has access
    from enrollments.models import Enrollment
    is_enrolled = Enrollment.objects.filter(
        user=request.user, 
        course=course, 
        is_active=True
    ).exists()
    
    # Allow access if enrolled or admin/instructor
    if not (is_enrolled or request.user.is_admin_or_above() or 
            request.user == course.instructor or
            (request.user.organization == course.organization and request.user.is_instructor())):
        messages.error(request, 'You do not have access to view documents for this course.')
        return redirect('dashboard')
    
    # Get accessible documents (only published/active ones for students)
    if request.user.is_admin_or_above() or request.user == course.instructor:
        documents = CourseDocument.objects.filter(course=course).order_by('order', 'created_at')
    else:
        # Students only see published documents
        documents = CourseDocument.objects.filter(
            course=course, 
            is_active=True
        ).order_by('order', 'created_at')
    
    context = {
        'course': course,
        'documents': documents,
        'page_title': f'Course Materials - {course.title}',
        'is_student': not (request.user.is_admin_or_above() or request.user == course.instructor),
        'is_enrolled': is_enrolled,
        'total_documents': documents.count(),
        'required_documents': documents.filter(is_required=True).count(),
    }
    
    return render(request, 'courses/documents/student_list.html', context)
