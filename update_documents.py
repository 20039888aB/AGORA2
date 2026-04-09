#!/usr/bin/env python
import os
import sys
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agoraprof.settings')
django.setup()

from courses.models import CourseDocument
from django.core.files.base import ContentFile

# Get all documents
documents = CourseDocument.objects.all()
print(f'Found {documents.count()} documents')

for doc in documents:
    # Create sample PDF content
    content = f"{doc.title}\n\n{doc.description or 'Course material'}\n\nThis is course content for {doc.course.title}.\n\nModule {doc.order} Content:\n- Key concepts and theories\n- Practical examples and case studies\n- Exercises and activities\n- Assessment criteria\n\nGenerated on: {doc.created_at.strftime('%Y-%m-%d')}\nCourse: {doc.course.title}"
    
    # Create filename
    filename = f'{doc.course.slug}_{doc.order}_{doc.title.replace(" ", "_")}.pdf'
    
    # Save the content as a file
    doc.file.save(filename, ContentFile(content.encode('utf-8')))
    doc.file_size = len(content.encode('utf-8'))
    doc.save()
    
    print(f'Updated: {doc.title} -> {filename}')

print('All documents updated with PDF content')
