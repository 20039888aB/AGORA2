#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agoraprof.settings')
django.setup()

from courses.models import Course
from organizations.models import Organization

def check_courses():
    print("=== COURSE SYSTEM CHECK ===")
    
    # Check total courses
    total_courses = Course.objects.count()
    print(f"\nTotal courses in database: {total_courses}")
    
    # Check organizations
    total_orgs = Organization.objects.count()
    print(f"Total organizations: {total_orgs}")
    
    if total_courses > 0:
        print("\n=== COURSES FOUND ===")
        courses = Course.objects.all()[:10]  # Show first 10
        
        for course in courses:
            org_name = course.organization.name if course.organization else "No Organization"
            print(f"- {course.title}")
            print(f"  Organization: {org_name}")
            print(f"  Status: {course.status}")
            print(f"  Difficulty: {course.difficulty}")
            print(f"  Duration: {course.duration_hours} hours")
            print(f"  Price: ${course.price}")
            print(f"  Created: {course.created_at}")
            print()
    else:
        print("\n❌ No courses found in the database")
        print("You need to create some courses first!")
    
    # Check course categories
    from courses.models import Category
    total_categories = Category.objects.count()
    print(f"Total course categories: {total_categories}")
    
    if total_categories > 0:
        print("\n=== CATEGORIES FOUND ===")
        categories = Category.objects.all()[:5]
        for category in categories:
            org_name = category.organization.name if category.organization else "No Organization"
            print(f"- {category.name} (Org: {org_name})")
    
    print("\n=== RECOMMENDATIONS ===")
    if total_courses == 0:
        print("📝 To create courses:")
        print("1. Go to: http://127.0.0.1:8000/courses/create/")
        print("2. Fill out the course creation form")
        print("3. Upload PDF documents")
        print("4. Click 'Publish Course'")
    else:
        print("✅ Courses exist! You can:")
        print("1. View courses at: http://127.0.0.1:8000/courses/")
        print("2. Create more courses at: http://127.0.0.1:8000/courses/create/")
        print("3. Manage courses at: http://127.0.0.1:8000/courses/manage/")

if __name__ == "__main__":
    check_courses()
