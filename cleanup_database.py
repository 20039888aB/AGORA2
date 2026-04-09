#!/usr/bin/env python
"""
Database Cleanup Script - Remove Fake Data
This script removes all fake/test data from the database while preserving real user accounts and essential data.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agoraprof.settings')
django.setup()

from django.db import transaction
from django.contrib.auth.models import User
from courses.models import Course, Module, Lesson, CourseDocument
from courses.enhanced_models import EnhancedCourse, CourseFile
from enrollments.models import Enrollment
from organizations.models import Organization
from accounts.models import UserProfile
from assignments.models import Assignment, AssignmentSubmission
from notifications.models import Notification

def cleanup_database():
    """
    Clean up database by removing fake/test data while preserving real data
    """
    print("🧹 Starting Database Cleanup...")
    print("=" * 50)
    
    with transaction.atomic():
        # Get real users (not fake/test accounts)
        real_users = User.objects.filter(
            ~Q(email__icontains='test') &
            ~Q(email__icontains='fake') &
            ~Q(email__icontains='demo') &
            ~Q(email__icontains='example') &
            ~Q(email__endswith='test.com')
        )
        
        print(f"📊 Found {real_users.count()} real users to preserve")
        
        # 1. Clean up fake courses and related data
        print("\n🗑️ Cleaning up fake courses...")
        
        # Get fake courses (created by fake users or with fake titles)
        fake_courses = Course.objects.filter(
            Q(title__icontains='test') |
            Q(title__icontains='fake') |
            Q(title__icontains='demo') |
            Q(title__icontains='example') |
            Q(created_by__email__icontains='test') |
            Q(created_by__email__icontains='fake') |
            Q(created_by__email__icontains='demo') |
            Q(created_by__email__icontains='example')
        )
        
        print(f"   Found {fake_courses.count()} fake courses to delete")
        
        # Delete fake course documents
        fake_course_docs = CourseDocument.objects.filter(course__in=fake_courses)
        print(f"   Deleting {fake_course_docs.count()} fake course documents")
        fake_course_docs.delete()
        
        # Delete fake modules and lessons
        fake_modules = Module.objects.filter(course__in=fake_courses)
        print(f"   Deleting {fake_modules.count()} fake modules")
        fake_modules.delete()
        
        fake_lessons = Lesson.objects.filter(course__in=fake_courses)
        print(f"   Deleting {fake_lessons.count()} fake lessons")
        fake_lessons.delete()
        
        # Delete fake courses
        print(f"   Deleting {fake_courses.count()} fake courses")
        fake_courses.delete()
        
        # 2. Clean up fake enhanced courses
        print("\n🗑️ Cleaning up fake enhanced courses...")
        
        fake_enhanced_courses = EnhancedCourse.objects.filter(
            Q(title__icontains='test') |
            Q(title__icontains='fake') |
            Q(title__icontains='demo') |
            Q(title__icontains='example') |
            Q(created_by__email__icontains='test') |
            Q(created_by__email__icontains='fake') |
            Q(created_by__email__icontains='demo') |
            Q(created_by__email__icontains='example')
        )
        
        print(f"   Found {fake_enhanced_courses.count()} fake enhanced courses to delete")
        
        # Delete fake enhanced course files
        fake_enhanced_files = CourseFile.objects.filter(course__in=fake_enhanced_courses)
        print(f"   Deleting {fake_enhanced_files.count()} fake enhanced course files")
        fake_enhanced_files.delete()
        
        # Delete fake enhanced courses
        print(f"   Deleting {fake_enhanced_courses.count()} fake enhanced courses")
        fake_enhanced_courses.delete()
        
        # 3. Clean up fake enrollments
        print("\n🗑️ Cleaning up fake enrollments...")
        
        # Get enrollments for deleted courses
        remaining_courses = Course.objects.all()
        fake_enrollments = Enrollment.objects.filter(
            Q(course__title__icontains='test') |
            Q(course__title__icontains='fake') |
            Q(course__title__icontains='demo') |
            Q(course__title__icontains='example') |
            Q(user__email__icontains='test') |
            Q(user__email__icontains='fake') |
            Q(user__email__icontains='demo') |
            Q(user__email__icontains='example')
        )
        
        print(f"   Found {fake_enrollments.count()} fake enrollments to delete")
        fake_enrollments.delete()
        
        # 4. Clean up fake assignments
        print("\n🗑️ Cleaning up fake assignments...")
        
        fake_assignments = Assignment.objects.filter(
            Q(title__icontains='test') |
            Q(title__icontains='fake') |
            Q(title__icontains='demo') |
            Q(title__icontains='example') |
            Q(created_by__email__icontains='test') |
            Q(created_by__email__icontains='fake') |
            Q(created_by__email__icontains='demo') |
            Q(created_by__email__icontains='example')
        )
        
        print(f"   Found {fake_assignments.count()} fake assignments to delete")
        
        # Delete fake submissions
        fake_submissions = AssignmentSubmission.objects.filter(assignment__in=fake_assignments)
        print(f"   Deleting {fake_submissions.count()} fake submissions")
        fake_submissions.delete()
        
        # Delete fake assignments
        print(f"   Deleting {fake_assignments.count()} fake assignments")
        fake_assignments.delete()
        
        # 5. Clean up fake notifications
        print("\n🗑️ Cleaning up fake notifications...")
        
        fake_notifications = Notification.objects.filter(
            Q(title__icontains='test') |
            Q(message__icontains='test') |
            Q(message__icontains='fake') |
            Q(message__icontains='demo') |
            Q(message__icontains='example') |
            Q(user__email__icontains='test') |
            Q(user__email__icontains='fake') |
            Q(user__email__icontains='demo') |
            Q(user__email__icontains='example')
        )
        
        print(f"   Deleting {fake_notifications.count()} fake notifications")
        fake_notifications.delete()
        
        # 6. Clean up fake organizations (keep real ones)
        print("\n🗑️ Cleaning up fake organizations...")
        
        fake_organizations = Organization.objects.filter(
            Q(name__icontains='test') |
            Q(name__icontains='fake') |
            Q(name__icontains='demo') |
            Q(name__icontains='example') |
            Q(description__icontains='test') |
            Q(description__icontains='fake') |
            Q(description__icontains='demo') |
            Q(description__icontains='example')
        )
        
        print(f"   Found {fake_organizations.count()} fake organizations to delete")
        fake_organizations.delete()
        
        # 7. Clean up fake user profiles
        print("\n🗑️ Cleaning up fake user profiles...")
        
        fake_profiles = UserProfile.objects.filter(
            Q(user__email__icontains='test') |
            Q(user__email__icontains='fake') |
            Q(user__email__icontains='demo') |
            Q(user__email__icontains='example')
        )
        
        print(f"   Deleting {fake_profiles.count()} fake user profiles")
        fake_profiles.delete()
        
        # 8. Clean up orphaned data
        print("\n🧹 Cleaning up orphaned data...")
        
        # Delete course documents without courses
        orphaned_docs = CourseDocument.objects.filter(course__isnull=True)
        print(f"   Deleting {orphaned_docs.count()} orphaned course documents")
        orphaned_docs.delete()
        
        # Delete modules without courses
        orphaned_modules = Module.objects.filter(course__isnull=True)
        print(f"   Deleting {orphaned_modules.count()} orphaned modules")
        orphaned_modules.delete()
        
        # Delete lessons without courses
        orphaned_lessons = Lesson.objects.filter(course__isnull=True)
        print(f"   Deleting {orphaned_lessons.count()} orphaned lessons")
        orphaned_lessons.delete()
        
        # Delete course files without courses
        orphaned_files = CourseFile.objects.filter(course__isnull=True)
        print(f"   Deleting {orphaned_files.count()} orphaned course files")
        orphaned_files.delete()
        
        # Delete enrollments without courses or users
        orphaned_enrollments = Enrollment.objects.filter(
            Q(course__isnull=True) | Q(user__isnull=True)
        )
        print(f"   Deleting {orphaned_enrollments.count()} orphaned enrollments")
        orphaned_enrollments.delete()
        
    print("\n✅ Database Cleanup Complete!")
    print("=" * 50)
    
    # Summary report
    print("\n📊 SUMMARY REPORT:")
    print(f"   Real Users Preserved: {real_users.count()}")
    print(f"   Remaining Courses: {Course.objects.count()}")
    print(f"   Remaining Enhanced Courses: {EnhancedCourse.objects.count()}")
    print(f"   Remaining Organizations: {Organization.objects.count()}")
    print(f"   Remaining Users: {User.objects.count()}")
    print(f"   Remaining Enrollments: {Enrollment.objects.count()}")
    
    print("\n🎯 Database is now clean with only real data!")
    print("🚀 Ready for production use!")
    
    return True

def show_database_stats():
    """Show current database statistics"""
    print("📊 Current Database Statistics:")
    print("=" * 40)
    
    print(f"Users: {User.objects.count()}")
    print(f"Organizations: {Organization.objects.count()}")
    print(f"Regular Courses: {Course.objects.count()}")
    print(f"Enhanced Courses: {EnhancedCourse.objects.count()}")
    print(f"Course Documents: {CourseDocument.objects.count()}")
    print(f"Course Files: {CourseFile.objects.count()}")
    print(f"Modules: {Module.objects.count()}")
    print(f"Lessons: {Lesson.objects.count()}")
    print(f"Enrollments: {Enrollment.objects.count()}")
    print(f"Assignments: {Assignment.objects.count()}")
    print(f"Submissions: {Submission.objects.count()}")
    print(f"Notifications: {Notification.objects.count()}")
    print(f"User Profiles: {UserProfile.objects.count()}")
    
    print("=" * 40)

def confirm_cleanup():
    """Ask for confirmation before cleaning"""
    print("⚠️  DATABASE CLEANUP WARNING")
    print("=" * 50)
    print("This script will DELETE all fake/test data from the database.")
    print("Real user accounts and legitimate data will be preserved.")
    print("This action cannot be undone!")
    print("=" * 50)
    
    response = input("\n❓ Are you sure you want to proceed? (yes/no): ").lower().strip()
    
    if response in ['yes', 'y']:
        print("\n🚀 Proceeding with database cleanup...")
        cleanup_database()
        return True
    else:
        print("\n❌ Database cleanup cancelled.")
        return False

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == '--stats':
            show_database_stats()
        elif sys.argv[1] == '--cleanup':
            confirm_cleanup()
        else:
            print("Usage:")
            print("  python cleanup_database.py --stats     # Show database statistics")
            print("  python cleanup_database.py --cleanup   # Clean up fake data")
    else:
        print("Database Cleanup Script")
        print("Usage:")
        print("  python cleanup_database.py --stats     # Show database statistics")
        print("  python cleanup_database.py --cleanup   # Clean up fake data")
