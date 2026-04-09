#!/usr/bin/env python
"""
Test Enhanced Course System
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agoraprof.settings')
django.setup()

def test_enhanced_system():
    """Test the enhanced course system"""
    
    print("🧪 Testing Enhanced Course System")
    print("=" * 50)
    
    try:
        # Test 1: Model imports
        print("\n📦 1. Testing Model Imports...")
        from courses.enhanced_models import EnhancedCourse, CourseFile
        print("   ✅ EnhancedCourse imported successfully")
        print("   ✅ CourseFile imported successfully")
        
        # Test 2: View imports
        print("\n📝 2. Testing View Imports...")
        from content.enhanced_views import (
            enhanced_course_create_view,
            enhanced_course_detail_view,
            enhanced_course_edit_view,
            enhanced_courses_list_view
        )
        print("   ✅ Enhanced views imported successfully")
        
        # Test 3: URL imports
        print("\n🔗 3. Testing URL Imports...")
        from content.enhanced_urls import urlpatterns
        print("   ✅ Enhanced URLs imported successfully")
        
        # Test 4: Database tables
        print("\n🗄️ 4. Testing Database Tables...")
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('enhanced_courses', 'course_files')")
            tables = cursor.fetchall()
            if len(tables) == 2:
                print("   ✅ Enhanced database tables exist")
                for table in tables:
                    print(f"      - {table[0]}")
            else:
                print("   ❌ Enhanced database tables missing")
                print("   💡 Run: python manage.py migrate")
                return False
        
        # Test 5: URL patterns
        print("\n🌐 5. Testing URL Patterns...")
        from django.urls import reverse
        try:
            create_url = reverse('content:enhanced_course_create')
            list_url = reverse('content:enhanced_courses_list')
            print(f"   ✅ Course create URL: {create_url}")
            print(f"   ✅ Course list URL: {list_url}")
        except Exception as e:
            print(f"   ❌ URL reversal failed: {str(e)}")
            return False
        
        # Test 6: Admin registration
        print("\n🔧 6. Testing Admin Registration...")
        from django.contrib import admin
        try:
            enhanced_course_admin = admin.site._registry.get('enhancedcourse')
            course_file_admin = admin.site._registry.get('coursefile')
            if enhanced_course_admin:
                print("   ✅ EnhancedCourse admin registered")
            else:
                print("   ❌ EnhancedCourse admin not registered")
            
            if course_file_admin:
                print("   ✅ CourseFile admin registered")
            else:
                print("   ❌ CourseFile admin not registered")
        except Exception as e:
            print(f"   ❌ Admin check failed: {str(e)}")
        
        print("\n✅ Enhanced Course System Tests Complete!")
        print("=" * 50)
        
        print("\n🎯 Next Steps:")
        print("1. Start server: python manage.py runserver 8000")
        print("2. Visit: http://127.0.0.1:8000/content/enhanced/courses/")
        print("3. Test course creation and file upload")
        print("4. Test course editing and management")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_enhanced_system()
    sys.exit(0 if success else 1)
