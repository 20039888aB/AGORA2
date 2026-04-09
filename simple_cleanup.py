#!/usr/bin/env python
"""
Simple Database Cleanup - Remove Fake Data
This script removes obvious fake/test data while preserving real user accounts.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agoraprof.settings')
django.setup()

from django.db import transaction
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

def simple_cleanup():
    """
    Simple cleanup of fake data
    """
    print("🧹 Starting Simple Database Cleanup...")
    print("=" * 50)
    
    with transaction.atomic():
        # 1. Remove fake/test users (keep real ones)
        fake_users = User.objects.filter(
            Q(email__icontains='test') |
            Q(email__icontains='fake') |
            Q(email__icontains='demo') |
            Q(email__icontains='example') |
            Q(email__endswith='test.com')
        )
        
        print(f"🗑️  Deleting {fake_users.count()} fake/test users")
        fake_users.delete()
        
        # 2. Remove courses created by fake users
        from courses.models import Course
        fake_courses = Course.objects.filter(
            Q(title__icontains='test') |
            Q(title__icontains='fake') |
            Q(title__icontains='demo') |
            Q(title__icontains='example') |
            Q(instructor__in=fake_users)
        )
        
        print(f"🗑️  Deleting {fake_courses.count()} fake courses")
        fake_courses.delete()
        
        # 3. Remove enhanced courses created by fake users
        try:
            from courses.enhanced_models import EnhancedCourse
            fake_enhanced_courses = EnhancedCourse.objects.filter(
                Q(title__icontains='test') |
                Q(title__icontains='fake') |
                Q(title__icontains='demo') |
                Q(title__icontains='example') |
                Q(created_by__in=fake_users)
            )
            
            print(f"🗑️  Deleting {fake_enhanced_courses.count()} fake enhanced courses")
            fake_enhanced_courses.delete()
        except ImportError:
            print("ℹ️  Enhanced courses module not found, skipping")
        
        # 4. Clean up orphaned data
        from courses.models import CourseDocument, Module, Lesson
        from courses.enhanced_models import CourseFile
        
        # Delete orphaned documents
        orphaned_docs = CourseDocument.objects.filter(course__isnull=True)
        print(f"🧹  Deleting {orphaned_docs.count()} orphaned documents")
        orphaned_docs.delete()
        
        # Delete orphaned modules
        orphaned_modules = Module.objects.filter(course__isnull=True)
        print(f"🧹  Deleting {orphaned_modules.count()} orphaned modules")
        orphaned_modules.delete()
        
        # Delete orphaned lessons
        orphaned_lessons = Lesson.objects.filter(course__isnull=True)
        print(f"🧹  Deleting {orphaned_lessons.count()} orphaned lessons")
        orphaned_lessons.delete()
        
        # Delete orphaned course files
        orphaned_files = CourseFile.objects.filter(course__isnull=True)
        print(f"🧹  Deleting {orphaned_files.count()} orphaned course files")
        orphaned_files.delete()
        
        # 5. Clean up enrollments for deleted courses
        try:
            from enrollments.models import Enrollment
            remaining_courses = Course.objects.all()
            orphaned_enrollments = Enrollment.objects.filter(
                Q(course__isnull=True) | Q(user__isnull=True)
            )
            print(f"🧹  Deleting {orphaned_enrollments.count()} orphaned enrollments")
            orphaned_enrollments.delete()
        except ImportError:
            print("ℹ️  Enrollments module not found, skipping")
    
    print("\n✅ Simple Database Cleanup Complete!")
    print("=" * 50)
    
    # Summary report
    print("\n📊 SUMMARY REPORT:")
    print(f"   Remaining Users: {User.objects.count()}")
    print(f"   Remaining Courses: {Course.objects.count()}")
    
    try:
        from courses.enhanced_models import EnhancedCourse
        print(f"   Remaining Enhanced Courses: {EnhancedCourse.objects.count()}")
    except ImportError:
        print("   Remaining Enhanced Courses: N/A (module not found)")
    
    print(f"   Remaining Course Documents: {CourseDocument.objects.count()}")
    print(f"   Remaining Course Files: {CourseFile.objects.count()}")
    print(f"   Remaining Modules: {Module.objects.count()}")
    print(f"   Remaining Lessons: {Lesson.objects.count()}")
    
    print("\n🎯 Database is now clean!")
    print("🚀 Ready for production use!")
    
    return True

def show_stats():
    """Show current database statistics"""
    print("📊 Current Database Statistics:")
    print("=" * 40)
    
    print(f"Users: {User.objects.count()}")
    print(f"Courses: {Course.objects.count()}")
    
    try:
        from courses.enhanced_models import EnhancedCourse
        print(f"Enhanced Courses: {EnhancedCourse.objects.count()}")
    except ImportError:
        print("Enhanced Courses: N/A (module not found)")
    
    print(f"Course Documents: {CourseDocument.objects.count()}")
    print(f"Course Files: {CourseFile.objects.count()}")
    print(f"Modules: {Module.objects.count()}")
    print(f"Lessons: {Lesson.objects.count()}")
    print("=" * 40)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == '--stats':
            show_stats()
        elif sys.argv[1] == '--cleanup':
            simple_cleanup()
        else:
            print("Usage:")
            print("  python simple_cleanup.py --stats     # Show database statistics")
            print("  python simple_cleanup.py --cleanup   # Clean up fake data")
    else:
        print("Simple Database Cleanup Script")
        print("Usage:")
        print("  python simple_cleanup.py --stats     # Show database statistics")
        print("  python simple_cleanup.py --cleanup   # Clean up fake data")
