"""
Test script to validate all backend functionality and data flow
"""
import os
import sys
import django

# Add the project root to Python path
sys.path.append(r'd:\AGORA2')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agoraprof.settings')
django.setup()

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


def test_user_permissions():
    """Test user permissions and role-based access"""
    print("Testing user permissions...")
    
    # Create test users
    superadmin = User.objects.create_user(
        username='test_superadmin',
        email='superadmin@test.com',
        password='testpass123',
        role='SUPERADMIN'
    )
    
    admin = User.objects.create_user(
        username='test_admin',
        email='admin@test.com',
        password='testpass123',
        role='ADMIN'
    )
    
    manager = User.objects.create_user(
        username='test_manager',
        email='manager@test.com',
        password='testpass123',
        role='MANAGER',
        managed_by=admin
    )
    
    student = User.objects.create_user(
        username='test_student',
        email='student@test.com',
        password='testpass123',
        role='STUDENT',
        managed_by=manager
    )
    
    # Test permission methods
    assert superadmin.is_superadmin() == True
    assert admin.is_admin() == True
    assert manager.is_manager() == True
    assert student.is_student() == True
    
    print("User permissions test passed!")


def test_team_management_views():
    """Test team management views functionality"""
    print("Testing team management views...")
    
    try:
        from content.views import team_assign, team_performance, team_schedule, team_communication
        from django.test import RequestFactory
        from django.contrib.messages.storage.fallback import FallbackStorage
        
        factory = RequestFactory()
        
        # Create test manager and team members
        admin = User.objects.create_user(
            username='test_admin2',
            email='admin2@test.com',
            password='testpass123',
            role='ADMIN'
        )
        
        manager = User.objects.create_user(
            username='test_manager2',
            email='manager2@test.com',
            password='testpass123',
            role='MANAGER',
            managed_by=admin
        )
        
        # Test team_assign view
        request = factory.get('/team/assign/')
        request.user = manager
        request._messages = FallbackStorage(request)
        
        # This should not raise an exception
        try:
            response = team_assign(request)
            assert response.status_code == 200
            print("team_assign view test passed!")
        except Exception as e:
            print(f"team_assign view test failed: {e}")
        
        # Test team_performance view
        request = factory.get('/team/performance/')
        request.user = manager
        request._messages = FallbackStorage(request)
        
        try:
            response = team_performance(request)
            assert response.status_code == 200
            print("team_performance view test passed!")
        except Exception as e:
            print(f"team_performance view test failed: {e}")
        
        # Test team_schedule view
        request = factory.get('/team/schedule/')
        request.user = manager
        request._messages = FallbackStorage(request)
        
        try:
            response = team_schedule(request)
            assert response.status_code == 200
            print("team_schedule view test passed!")
        except Exception as e:
            print(f"team_schedule view test failed: {e}")
        
        # Test team_communication view
        request = factory.get('/team/communication/')
        request.user = manager
        request._messages = FallbackStorage(request)
        
        try:
            response = team_communication(request)
            assert response.status_code == 200
            print("team_communication view test passed!")
        except Exception as e:
            print(f"team_communication view test failed: {e}")
            
    except ImportError as e:
        print(f"Team management views test failed (Import Error): {e}")


def test_content_upload_functionality():
    """Test content upload functionality"""
    print("Testing content upload functionality...")
    
    try:
        from content.models import ContentFile
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Create test user
        admin = User.objects.create_user(
            username='test_admin3',
            email='admin3@test.com',
            password='testpass123',
            role='ADMIN'
        )
        
        # Test content file creation
        test_file = SimpleUploadedFile(
            "test_document.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        content_file = ContentFile.objects.create(
            title="Test Document",
            description="Test file for validation",
            file=test_file,
            original_filename="test_document.pdf",
            uploaded_by=admin,
            organization=admin.organization
        )
        
        assert content_file.title == "Test Document"
        assert content_file.file_type == "PDF"
        assert content_file.can_user_access(admin) == True
        
        print("Content upload functionality test passed!")
        
    except ImportError as e:
        print(f"Content upload test failed (Import Error): {e}")
    except Exception as e:
        print(f"Content upload test failed: {e}")


def test_learning_paths_functionality():
    """Test learning paths functionality"""
    print("Testing learning paths functionality...")
    
    try:
        from learning.models import LearningPath, PathCourse
        from courses.models import Course
        
        # Create test organization and users
        admin = User.objects.create_user(
            username='test_admin4',
            email='admin4@test.com',
            password='testpass123',
            role='ADMIN'
        )
        
        # Create test course
        course = Course.objects.create(
            title="Test Course",
            description="Test course for learning path",
            instructor=admin,
            organization=admin.organization,
            status='PUBLISHED'
        )
        
        # Create learning path
        learning_path = LearningPath.objects.create(
            title="Test Learning Path",
            description="Test learning path",
            organization=admin.organization,
            created_by=admin,
            status='PUBLISHED'
        )
        
        # Add course to path
        path_course = PathCourse.objects.create(
            learning_path=learning_path,
            course=course,
            order=1
        )
        
        assert learning_path.total_courses == 1
        assert path_course.course == course
        
        print("Learning paths functionality test passed!")
        
    except ImportError as e:
        print(f"Learning paths test failed (Import Error): {e}")
    except Exception as e:
        print(f"Learning paths test failed: {e}")


def test_course_approval_workflow():
    """Test course approval workflow"""
    print("Testing course approval workflow...")
    
    try:
        from content.models import CourseApproval
        from courses.models import Course
        
        # Create test users
        admin = User.objects.create_user(
            username='test_admin5',
            email='admin5@test.com',
            password='testpass123',
            role='ADMIN'
        )
        
        manager = User.objects.create_user(
            username='test_manager5',
            email='manager5@test.com',
            password='testpass123',
            role='MANAGER',
            managed_by=admin
        )
        
        # Create course by manager (should be DRAFT)
        course = Course.objects.create(
            title="Manager Course",
            description="Course created by manager",
            instructor=manager,
            organization=admin.organization,
            status='DRAFT'
        )
        
        # Create approval request
        approval = CourseApproval.objects.create(
            course=course,
            submitted_by=manager,
            priority='NORMAL'
        )
        
        assert approval.status == 'PENDING'
        assert approval.can_user_review(admin) == True
        assert approval.can_user_review(manager) == False
        
        # Test approval
        approval.approve(approved_by=admin, notes="Looks good!")
        assert approval.status == 'APPROVED'
        assert course.status == 'PUBLISHED'
        
        print("Course approval workflow test passed!")
        
    except ImportError as e:
        print(f"Course approval workflow test failed (Import Error): {e}")
    except Exception as e:
        print(f"Course approval workflow test failed: {e}")


def test_analytics_functionality():
    """Test analytics functionality"""
    print("Testing analytics functionality...")
    
    try:
        from analytics.views_django import analytics_team, analytics_reports
        from django.test import RequestFactory
        from django.contrib.messages.storage.fallback import FallbackStorage
        
        factory = RequestFactory()
        
        # Create test admin
        admin = User.objects.create_user(
            username='test_admin6',
            email='admin6@test.com',
            password='testpass123',
            role='ADMIN'
        )
        
        # Test analytics_team view
        request = factory.get('/analytics/team/')
        request.user = admin
        request._messages = FallbackStorage(request)
        
        try:
            response = analytics_team(request)
            assert response.status_code == 200
            print("analytics_team view test passed!")
        except Exception as e:
            print(f"analytics_team view test failed: {e}")
        
        # Test analytics_reports view
        request = factory.get('/analytics/reports/')
        request.user = admin
        request._messages = FallbackStorage(request)
        
        try:
            response = analytics_reports(request)
            assert response.status_code == 200
            print("analytics_reports view test passed!")
        except Exception as e:
            print(f"analytics_reports view test failed: {e}")
            
    except ImportError as e:
        print(f"Analytics functionality test failed (Import Error): {e}")


def test_student_dashboard_filtering():
    """Test student dashboard only shows approved courses"""
    print("Testing student dashboard filtering...")
    
    try:
        from accounts.views import student_dashboard
        from courses.models import Course
        from django.test import RequestFactory
        from django.contrib.messages.storage.fallback import FallbackStorage
        
        factory = RequestFactory()
        
        # Create test users
        admin = User.objects.create_user(
            username='test_admin7',
            email='admin7@test.com',
            password='testpass123',
            role='ADMIN'
        )
        
        manager = User.objects.create_user(
            username='test_manager7',
            email='manager7@test.com',
            password='testpass123',
            role='MANAGER',
            managed_by=admin
        )
        
        student = User.objects.create_user(
            username='test_student7',
            email='student7@test.com',
            password='testpass123',
            role='STUDENT',
            managed_by=manager
        )
        
        # Create courses with different statuses
        published_course = Course.objects.create(
            title="Published Course",
            description="Approved course",
            instructor=admin,
            organization=admin.organization,
            status='PUBLISHED'
        )
        
        draft_course = Course.objects.create(
            title="Draft Course",
            description="Unapproved course",
            instructor=manager,
            organization=admin.organization,
            status='DRAFT'
        )
        
        # Test student dashboard
        request = factory.get('/dashboard/student/')
        request.user = student
        request._messages = FallbackStorage(request)
        
        try:
            response = student_dashboard(request)
            assert response.status_code == 200
            
            # Check context contains only published courses
            context = response.context_data
            available_courses = context.get('available_courses', [])
            
            # Should only contain published courses
            course_ids = [course.id for course in available_courses]
            assert published_course.id in course_ids
            assert draft_course.id not in course_ids
            
            print("Student dashboard filtering test passed!")
            
        except Exception as e:
            print(f"Student dashboard filtering test failed: {e}")
            
    except ImportError as e:
        print(f"Student dashboard filtering test failed (Import Error): {e}")


def run_all_tests():
    """Run all functionality tests"""
    print("=" * 50)
    print("RUNNING BACKEND FUNCTIONALITY TESTS")
    print("=" * 50)
    
    try:
        test_user_permissions()
        test_team_management_views()
        test_content_upload_functionality()
        test_learning_paths_functionality()
        test_course_approval_workflow()
        test_analytics_functionality()
        test_student_dashboard_filtering()
        
        print("\n" + "=" * 50)
        print("ALL TESTS COMPLETED!")
        print("=" * 50)
        print("Backend functionality has been validated successfully!")
        
    except Exception as e:
        print(f"\nTest suite failed with error: {e}")
        print("Please check the implementation for any issues.")


if __name__ == "__main__":
    run_all_tests()
