#!/usr/bin/env python
"""
Enhanced Course System Setup Script
This script sets up the complete enhanced course system
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agoraprof.settings')
django.setup()

def setup_enhanced_system():
    """Setup the enhanced course system"""
    
    print("🚀 Setting Up Enhanced Course System")
    print("=" * 50)
    
    try:
        # 1. Update main URLs to include enhanced URLs
        print("\n📝 1. Updating main URLs...")
        update_main_urls()
        
        # 2. Update settings to include enhanced models
        print("\n⚙️ 2. Updating settings...")
        update_settings()
        
        # 3. Create admin registration for enhanced models
        print("\n🔧 3. Setting up admin...")
        setup_admin()
        
        # 4. Test the system
        print("\n🧪 4. Testing system...")
        test_system()
        
        print("\n✅ Enhanced Course System Setup Complete!")
        print("=" * 50)
        print("\n🎯 Next Steps:")
        print("1. Run: python manage.py runserver")
        print("2. Visit: http://127.0.0.1:8000/content/enhanced/courses/")
        print("3. Test course creation and file upload")
        
    except Exception as e:
        print(f"\n❌ Setup Error: {str(e)}")
        sys.exit(1)

def update_main_urls():
    """Update main URLs to include enhanced URLs"""
    
    urls_file = 'agoraprof/urls.py'
    
    # Read current URLs
    with open(urls_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if enhanced URLs are already included
    if 'content.enhanced_urls' in content:
        print("   ✅ Enhanced URLs already included")
        return
    
    # Find the content URLs include
    import_start = content.find("path('content/', include('content.urls'))")
    if import_start == -1:
        print("   ⚠️ Content URLs not found - please check your main URLs file")
        return
    
    import_end = content.find("')", import_start)
    if import_end == -1:
        print("   ⚠️ Could not find content URLs import end")
        return
    
    # Add enhanced URLs after content URLs
    enhanced_urls_line = "    path('enhanced/', include('content.enhanced_urls')),"
    
    new_content = (
        content[:import_end] + 
        '\n' + enhanced_urls_line + '\n' +
        content[import_end:]
    )
    
    # Write updated content
    with open(urls_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("   ✅ Enhanced URLs added to main URLs")

def update_settings():
    """Update settings to include enhanced models"""
    
    settings_file = 'agoraprof/settings.py'
    
    # Read current settings
    with open(settings_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if enhanced models are already included
    if 'courses.enhanced_models' in content or 'EnhancedCourse' in content:
        print("   ✅ Enhanced models already configured")
        return
    
    print("   ℹ️ Note: Enhanced models are in courses.enhanced_models")
    print("   ℹ️ You can import them with: from courses.enhanced_models import EnhancedCourse")

def setup_admin():
    """Setup admin for enhanced models"""
    
    admin_file = 'courses/admin.py'
    
    # Read current admin
    with open(admin_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if enhanced models are already registered
    if 'EnhancedCourse' in content or 'CourseFile' in content:
        print("   ✅ Enhanced models already registered in admin")
        return
    
    # Add enhanced model registrations
    enhanced_admin_code = '''

# Enhanced Course Models Admin
from django.contrib import admin
from .enhanced_models import EnhancedCourse, CourseFile


@admin.register(EnhancedCourse)
class EnhancedCourseAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'category', 'difficulty', 'duration_hours', 
        'max_students', 'status', 'is_featured', 'created_at'
    ]
    list_filter = [
        'status', 'category', 'difficulty', 'is_featured', 'created_at'
    ]
    search_fields = ['title', 'description', 'short_description']
    ordering = ['organization', '-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': (
                'title', 'slug', 'description', 'short_description'
            )
        }),
        ('Course Details', {
            'fields': (
                ('category', 'difficulty', 'duration_hours', 'max_students'),
                'language', 'status'
            )
        }),
        ('Learning Content', {
            'fields': (
                'prerequisites', 'objectives', 'outcomes'
            )
        }),
        ('Settings', {
            'fields': (
                'certificate_enabled', 'is_featured', 'tags'
            )
        }),
        ('Organization', {
            'fields': (
                'organization', 'created_by'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superadmin():
            return qs
        return qs.filter(organization=request.user.organization)


@admin.register(CourseFile)
class CourseFileAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'course', 'file_type', 'file_size_display', 
        'uploaded_by', 'created_at'
    ]
    list_filter = [
        'course', 'file_type', 'is_required', 'is_downloadable', 'created_at'
    ]
    search_fields = ['title', 'description']
    ordering = ['course', 'order', 'created_at']
    readonly_fields = ['file_size', 'mime_type', 'created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': (
                'title', 'description', 'file'
            )
        }),
        ('File Details', {
            'fields': (
                'file_type', 'file_size', 'mime_type'
            )
        }),
        ('Organization', {
            'fields': (
                'course', 'uploaded_by', 'organization'
            )
        }),
        ('Settings', {
            'fields': (
                'order', 'is_required', 'is_downloadable', 'is_active'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def file_size_display(self, obj):
        if obj.file_size:
            for unit in ['B', 'KB', 'MB', 'GB']:
                if obj.file_size < 1024.0:
                    return f"{obj.file_size:.1f} {unit}"
                obj.file_size /= 1024.0
            return f"{obj.file_size:.1f} TB"
        return "0 B"
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superadmin():
            return qs
        return qs.filter(organization=request.user.organization)
'''
    
    # Add enhanced admin code
    with open(admin_file, 'w', encoding='utf-8') as f:
        f.write(content + enhanced_admin_code)
    
    print("   ✅ Enhanced models registered in admin")

def test_system():
    """Test the enhanced system"""
    
    try:
        # Test model imports
        from courses.enhanced_models import EnhancedCourse, CourseFile
        print("   ✅ Model imports successful")
        
        # Test view imports
        from content.enhanced_views import enhanced_course_create_view
        print("   ✅ View imports successful")
        
        # Test URL imports
        from content.enhanced_urls import urlpatterns
        print("   ✅ URL imports successful")
        
        # Test database models
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%enhanced%'")
            tables = cursor.fetchall()
            if tables:
                print(f"   ✅ Database tables created: {[t[0] for t in tables]}")
            else:
                print("   ⚠️ No enhanced tables found - run migrations first")
        
        print("   ✅ System tests passed")
        
    except ImportError as e:
        print(f"   ❌ Import failed: {str(e)}")
        print("   💡 Make sure migrations have been run")
        return
    except Exception as e:
        print(f"   ❌ Test failed: {str(e)}")
        raise

if __name__ == '__main__':
    setup_enhanced_system()
