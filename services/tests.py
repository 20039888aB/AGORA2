"""
Services Testing Framework - Comprehensive Testing Suite

This module provides comprehensive testing utilities and test cases
for all services in the AgoraProf LMS.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
import time
import json

from .base import BaseService, ServiceResponse
from .registry import ServiceRegistry, ServiceFactory
from .manager import ServiceManager, ServiceOrchestrator
from .config import ServiceConfigManager, get_service_settings
from .interfaces import IUserService, ICourseService, IEnrollmentService

User = get_user_model()


class ServiceTestCase(TestCase):
    """Base test case for service tests"""
    
    def setUp(self):
        """Set up test environment"""
        self.service_manager = ServiceManager()
        self.config_manager = ServiceConfigManager()
        
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            password='test123',
            first_name='Test',
            last_name='User',
            role='STUDENT'
        )
        
        # Create admin user
        self.admin = User.objects.create_user(
            email='admin@example.com',
            password='admin123',
            first_name='Admin',
            last_name='User',
            role='ADMIN'
        )
        
        # Create test organization
        from organizations.models import Organization
        self.organization = Organization.objects.create(
            name='Test Organization',
            domain='test.org',
            description='Test organization for testing'
        )
        
        # Assign user to organization
        self.user.organization = self.organization
        self.user.save()
        
        self.admin.organization = self.organization
        self.admin.save()
    
    def tearDown(self):
        """Clean up test environment"""
        cache.clear()


class UserServiceTestCase(ServiceTestCase):
    """Test cases for UserService"""
    
    def setUp(self):
        super().setUp()
        self.user_service = ServiceFactory.create_user_service(self.user)
    
    def test_create_user_success(self):
        """Test successful user creation"""
        data = {
            'email': 'newuser@example.com',
            'password': 'password123',
            'first_name': 'New',
            'last_name': 'User',
            'role': 'STUDENT',
            'organization': self.organization
        }
        
        user = self.user_service.create_user(data, created_by=self.admin)
        
        self.assertIsNotNone(user)
        self.assertEqual(user.email, data['email'])
        self.assertEqual(user.first_name, data['first_name'])
        self.assertEqual(user.role, data['role'])
        self.assertEqual(user.organization, data['organization'])
    
    def test_create_user_duplicate_email(self):
        """Test user creation with duplicate email"""
        data = {
            'email': self.user.email,
            'password': 'password123',
            'first_name': 'Duplicate',
            'last_name': 'User',
            'role': 'STUDENT',
            'organization': self.organization
        }
        
        with self.assertRaises(Exception) as context:
            self.user_service.create_user(data, created_by=self.admin)
        
        self.assertIn('already exists', str(context.exception))
    
    def test_update_user_success(self):
        """Test successful user update"""
        data = {
            'first_name': 'Updated',
            'last_name': 'User',
            'phone': '+1234567890'
        }
        
        updated_user = self.user_service.update_user(self.user, data, updated_by=self.admin)
        
        self.assertEqual(updated_user.first_name, data['first_name'])
        self.assertEqual(updated_user.last_name, data['last_name'])
        self.assertEqual(updated_user.phone, data['phone'])
    
    def test_soft_delete_user(self):
        """Test soft delete user"""
        deleted_user = self.user_service.soft_delete_user(self.user, deleted_by=self.admin)
        
        self.assertTrue(deleted_user.is_deleted)
        self.assertFalse(deleted_user.is_active)
        self.assertIsNotNone(deleted_user.deleted_at)
    
    def test_restore_user(self):
        """Test restore soft deleted user"""
        # First soft delete
        self.user_service.soft_delete_user(self.user, deleted_by=self.admin)
        
        # Then restore
        restored_user = self.user_service.restore_user(self.user, restored_by=self.admin)
        
        self.assertFalse(restored_user.is_deleted)
        self.assertTrue(restored_user.is_active)
        self.assertIsNone(restored_user.deleted_at)
    
    def test_change_user_role(self):
        """Test user role change"""
        updated_user = self.user_service.change_user_role(
            self.user, 
            'MANAGER', 
            changed_by=self.admin
        )
        
        self.assertEqual(updated_user.role, 'MANAGER')
        self.assertEqual(updated_user.role_update_count, 1)
        self.assertIsNotNone(updated_user.role_updated_at)
    
    def test_get_user_statistics(self):
        """Test user statistics"""
        stats = self.user_service.get_user_statistics(self.organization)
        
        self.assertIn('total_users', stats)
        self.assertIn('active_users', stats)
        self.assertIn('students', stats)
        self.assertIn('managers', stats)
        self.assertIn('admins', stats)
        
        # Verify counts
        self.assertEqual(stats['total_users'], 2)  # self.user + self.admin
        self.assertEqual(stats['students'], 1)
        self.assertEqual(stats['admins'], 1)
    
    def test_search_users(self):
        """Test user search"""
        # Create more users for testing
        User.objects.create_user(
            email='john@example.com',
            password='password123',
            first_name='John',
            last_name='Doe',
            role='STUDENT',
            organization=self.organization
        )
        
        results = self.user_service.search_users('john', organization=self.organization)
        
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().first_name, 'John')
    
    def test_validate_user_permissions(self):
        """Test user permission validation"""
        # Test admin permissions
        self.assertTrue(
            self.user_service.validate_user_permissions(
                self.admin, 
                'create_user', 
                self.organization
            )
        )
        
        # Test student permissions (should be limited)
        self.assertFalse(
            self.user_service.validate_user_permissions(
                self.user, 
                'create_user', 
                self.organization
            )
        )


class CourseServiceTestCase(ServiceTestCase):
    """Test cases for CourseService"""
    
    def setUp(self):
        super().setUp()
        self.course_service = ServiceFactory.create_course_service(self.admin)
        
        # Create test course
        from courses.models import Course
        self.course = Course.objects.create(
            title='Test Course',
            description='Test course description',
            organization=self.organization,
            instructor=self.admin,
            difficulty='BEGINNER',
            duration_hours=10,
            price=99.99
        )
    
    def test_create_course_success(self):
        """Test successful course creation"""
        data = {
            'title': 'New Course',
            'description': 'New course description',
            'organization': self.organization,
            'instructor': self.admin,
            'difficulty': 'INTERMEDIATE',
            'duration_hours': 20,
            'price': 199.99
        }
        
        course = self.course_service.create_course(data, created_by=self.admin)
        
        self.assertIsNotNone(course)
        self.assertEqual(course.title, data['title'])
        self.assertEqual(course.organization, data['organization'])
        self.assertEqual(course.instructor, data['instructor'])
    
    def test_publish_course(self):
        """Test course publishing"""
        self.course_service.publish_course(self.course, published_by=self.admin)
        
        self.assertEqual(self.course.status, 'PUBLISHED')
        self.assertIsNotNone(self.course.published_at)
    
    def test_archive_course(self):
        """Test course archiving"""
        self.course_service.archive_course(self.course, archived_by=self.admin)
        
        self.assertEqual(self.course.status, 'ARCHIVED')
        self.assertIsNotNone(self.course.archived_at)
    
    def test_duplicate_course(self):
        """Test course duplication"""
        duplicated_course = self.course_service.duplicate_course(
            self.course, 
            creator=self.admin,
            include_modules=False,
            include_lessons=False
        )
        
        self.assertIsNotNone(duplicated_course)
        self.assertIn('Copy', duplicated_course.title)
        self.assertEqual(duplicated_course.organization, self.course.organization)
    
    def test_get_course_statistics(self):
        """Test course statistics"""
        stats = self.course_service.get_course_statistics(self.course)
        
        self.assertIn('total_enrollments', stats)
        self.assertIn('active_enrollments', stats)
        self.assertIn('completed_enrollments', stats)
        self.assertIn('average_progress', stats)
    
    def test_validate_course_access(self):
        """Test course access validation"""
        # Admin should have full access
        self.assertTrue(
            self.course_service.validate_course_access(
                self.admin, 
                self.course, 
                'edit'
            )
        )
        
        # Student should have limited access
        self.assertFalse(
            self.course_service.validate_course_access(
                self.user, 
                self.course, 
                'edit'
            )
        )


class EnrollmentServiceTestCase(ServiceTestCase):
    """Test cases for EnrollmentService"""
    
    def setUp(self):
        super().setUp()
        self.enrollment_service = ServiceFactory.create_enrollment_service(self.user)
        
        # Create test course
        from courses.models import Course
        self.course = Course.objects.create(
            title='Test Course',
            description='Test course description',
            organization=self.organization,
            instructor=self.admin,
            difficulty='BEGINNER',
            duration_hours=10,
            price=99.99
        )
    
    def test_create_enrollment_success(self):
        """Test successful enrollment creation"""
        enrollment = self.enrollment_service.create_enrollment(
            user=self.user,
            course=self.course,
            payment_status='COMPLETED',
            payment_amount=99.99,
            enrolled_by=self.user
        )
        
        self.assertIsNotNone(enrollment)
        self.assertEqual(enrollment.user, self.user)
        self.assertEqual(enrollment.course, self.course)
        self.assertEqual(enrollment.status, 'ACTIVE')
        self.assertEqual(enrollment.payment_status, 'COMPLETED')
    
    def test_complete_enrollment(self):
        """Test enrollment completion"""
        # Create enrollment first
        enrollment = self.enrollment_service.create_enrollment(
            user=self.user,
            course=self.course,
            payment_status='COMPLETED',
            payment_amount=99.99,
            enrolled_by=self.user
        )
        
        # Complete enrollment
        completed_enrollment = self.enrollment_service.complete_enrollment(
            enrollment, 
            completed_by=self.admin
        )
        
        self.assertEqual(completed_enrollment.status, 'COMPLETED')
        self.assertIsNotNone(completed_enrollment.completion_date)
        self.assertEqual(completed_enrollment.progress_percentage, 100.00)
    
    def test_update_progress(self):
        """Test progress update"""
        # Create enrollment first
        enrollment = self.enrollment_service.create_enrollment(
            user=self.user,
            course=self.course,
            payment_status='COMPLETED',
            payment_amount=99.99,
            enrolled_by=self.user
        )
        
        # Update progress
        updated_enrollment = self.enrollment_service.update_progress(
            enrollment, 
            50.0, 
            updated_by=self.user
        )
        
        self.assertEqual(updated_enrollment.progress_percentage, 50.0)
        self.assertIsNotNone(updated_enrollment.last_accessed_at)
    
    def test_get_enrollment_statistics(self):
        """Test enrollment statistics"""
        # Create enrollment first
        enrollment = self.enrollment_service.create_enrollment(
            user=self.user,
            course=self.course,
            payment_status='COMPLETED',
            payment_amount=99.99,
            enrolled_by=self.user
        )
        
        stats = self.enrollment_service.get_enrollment_statistics(enrollment)
        
        self.assertIn('total_lessons', stats)
        self.assertIn('completed_lessons', stats)
        self.assertIn('average_lesson_progress', stats)
        self.assertIn('days_since_enrollment', stats)


class ServiceManagerTestCase(ServiceTestCase):
    """Test cases for ServiceManager"""
    
    def test_get_service_with_cache(self):
        """Test getting service with caching"""
        service = self.service_manager.get_service('user', self.user, use_cache=True)
        
        self.assertIsNotNone(service)
        self.assertEqual(service.user, self.user)
    
    def test_get_service_without_cache(self):
        """Test getting service without caching"""
        service = self.service_manager.get_service('user', self.user, use_cache=False)
        
        self.assertIsNotNone(service)
        self.assertEqual(service.user, self.user)
    
    def test_execute_service_method_success(self):
        """Test successful service method execution"""
        result = self.service_manager.execute_service_method(
            service_name='user',
            method_name='get_user_statistics',
            user=self.admin,
            kwargs={'organization': self.organization}
        )
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.data)
        self.assertIn('total_users', result.data)
    
    def test_execute_service_method_error(self):
        """Test service method execution with error"""
        result = self.service_manager.execute_service_method(
            service_name='user',
            method_name='get_user_statistics',
            user=self.user,
            kwargs={'organization': self.organization}
        )
        
        # This should fail because user is not admin
        self.assertFalse(result.success)
        self.assertIn('permission', result.message.lower())
    
    def test_batch_execute(self):
        """Test batch execution of service methods"""
        operations = [
            {
                'service': 'user',
                'method': 'get_user_statistics',
                'kwargs': {'organization': self.organization}
            },
            {
                'service': 'user',
                'method': 'search_users',
                'kwargs': {'query': 'test', 'organization': self.organization}
            }
        ]
        
        results = self.service_manager.batch_execute(operations, user=self.admin)
        
        self.assertEqual(len(results), 2)
        self.assertTrue(results[0].success)
        self.assertTrue(results[1].success)


class ServiceOrchestratorTestCase(ServiceTestCase):
    """Test cases for ServiceOrchestrator"""
    
    def test_create_user_workflow(self):
        """Test user creation workflow"""
        user_data = {
            'email': 'workflow@example.com',
            'password': 'password123',
            'first_name': 'Workflow',
            'last_name': 'User',
            'role': 'STUDENT',
            'organization': self.organization,
            'profile': {
                'phone': '+1234567890',
                'address': '123 Workflow St'
            }
        }
        
        result = self.service_manager.service_orchestrator.create_user_workflow(
            user_data, 
            created_by=self.admin
        )
        
        self.assertTrue(result.success)
        self.assertIn('created successfully', result.message)
    
    def test_create_course_workflow(self):
        """Test course creation workflow"""
        course_data = {
            'title': 'Workflow Course',
            'description': 'Course created via workflow',
            'organization': self.organization,
            'instructor': self.admin,
            'difficulty': 'BEGINNER',
            'duration_hours': 15,
            'price': 149.99,
            'modules': [
                {
                    'title': 'Module 1',
                    'description': 'First module',
                    'order': 1
                },
                {
                    'title': 'Module 2',
                    'description': 'Second module',
                    'order': 2
                }
            ]
        }
        
        result = self.service_manager.service_orchestrator.create_course_workflow(
            course_data, 
            created_by=self.admin
        )
        
        self.assertTrue(result.success)
        self.assertIn('created successfully', result.message)


class ServiceConfigTestCase(ServiceTestCase):
    """Test cases for Service Configuration"""
    
    def test_config_manager_initialization(self):
        """Test config manager initialization"""
        self.assertIsNotNone(self.config_manager)
        self.assertIsNotNone(self.config_manager.config_cache)
        self.assertIn('cache', self.config_manager.config_cache)
        self.assertIn('monitoring', self.config_manager.config_cache)
    
    def test_get_cache_config(self):
        """Test cache configuration"""
        cache_config = self.config_manager.get_config('cache')
        
        self.assertIn('enabled', cache_config)
        self.assertIn('default_timeout', cache_config)
        self.assertIn('backend', cache_config)
    
    def test_get_monitoring_config(self):
        """Test monitoring configuration"""
        monitoring_config = self.config_manager.get_config('monitoring')
        
        self.assertIn('enabled', monitoring_config)
        self.assertIn('log_level', monitoring_config)
        self.assertIn('metrics_retention_days', monitoring_config)
    
    def test_get_security_config(self):
        """Test security configuration"""
        security_config = self.config_manager.get_config('security')
        
        self.assertIn('encryption_enabled', security_config)
        self.assertIn('rate_limiting_enabled', security_config)
        self.assertIn('audit_enabled', security_config)
    
    def test_service_settings(self):
        """Test service settings"""
        user_settings = get_service_settings('user')
        
        self.assertIsNotNone(user_settings)
        self.assertEqual(user_settings.service_name, 'user')
    
    def test_feature_enabled(self):
        """Test feature enabled check"""
        # This will depend on actual configuration
        enabled = self.config_manager.is_feature_enabled('user_management.profile_enabled')
        self.assertIsInstance(enabled, bool)
    
    def test_validate_config(self):
        """Test configuration validation"""
        validation_result = self.config_manager.validate_config()
        
        self.assertIn('valid', validation_result)
        self.assertIn('environment', validation_result)
        self.assertIn('issues', validation_result)


class ServicePerformanceTestCase(ServiceTestCase):
    """Performance tests for services"""
    
    def test_user_service_performance(self):
        """Test user service performance"""
        service = ServiceFactory.create_user_service(self.admin)
        
        # Measure performance
        start_time = time.time()
        
        # Create multiple users
        for i in range(100):
            data = {
                'email': f'perfuser{i}@example.com',
                'password': 'password123',
                'first_name': f'User {i}',
                'last_name': f'Test {i}',
                'role': 'STUDENT',
                'organization': self.organization
            }
            service.create_user(data, created_by=self.admin)
        
        duration = time.time() - start_time
        
        # Performance assertions
        self.assertLess(duration, 5.0, "User creation took too long")
        
        # Average time per operation
        avg_time = duration / 100
        self.assertLess(avg_time, 0.05, "Average time per user creation too high")
    
    def test_service_manager_performance(self):
        """Test service manager performance"""
        operations = []
        
        # Create operations list
        for i in range(50):
            operations.append({
                'service': 'user',
                'method': 'get_user_statistics',
                'kwargs': {'organization': self.organization}
            })
        
        # Measure performance
        start_time = time.time()
        
        results = self.service_manager.batch_execute(operations, user=self.admin)
        
        duration = time.time() - start_time
        
        # Performance assertions
        self.assertLess(duration, 3.0, "Batch execution took too long")
        self.assertEqual(len(results), 50)
        
        # Check all operations succeeded
        successful_count = sum(1 for result in results if result.success)
        self.assertEqual(successful_count, 50)
    
    def test_cache_performance(self):
        """Test cache performance"""
        service = self.service_manager.get_service('user', self.admin, use_cache=True)
        
        # First call (cache miss)
        start_time = time.time()
        user_stats1 = service.get_user_statistics(self.organization)
        first_duration = time.time() - start_time
        
        # Second call (cache hit)
        start_time = time.time()
        user_stats2 = service.get_user_statistics(self.organization)
        second_duration = time.time() - start_time
        
        # Cache should make second call faster
        self.assertLess(second_duration, first_duration)
        self.assertEqual(user_stats1, user_stats2)


class ServiceIntegrationTestCase(TransactionTestCase):
    """Integration tests for services"""
    
    def setUp(self):
        super().setUp()
        
        # Create test organization
        from organizations.models import Organization
        self.organization = Organization.objects.create(
            name='Integration Test Organization',
            domain='integration.test',
            description='Organization for integration testing'
        )
        
        # Create admin user
        self.admin = User.objects.create_user(
            email='admin@integration.test',
            password='admin123',
            first_name='Admin',
            last_name='User',
            role='ADMIN',
            organization=self.organization
        )
        
        # Create student user
        self.student = User.objects.create_user(
            email='student@integration.test',
            password='student123',
            first_name='Student',
            last_name='User',
            role='STUDENT',
            organization=self.organization
        )
    
    def test_complete_user_workflow(self):
        """Test complete user workflow"""
        # Create user
        user_service = ServiceFactory.create_user_service(self.admin)
        user_data = {
            'email': 'workflow@example.com',
            'password': 'password123',
            'first_name': 'Workflow',
            'last_name': 'User',
            'role': 'STUDENT',
            'organization': self.organization
        }
        user = user_service.create_user(user_data, created_by=self.admin)
        
        # Create course
        course_service = ServiceFactory.create_course_service(self.admin)
        course_data = {
            'title': 'Integration Test Course',
            'description': 'Course for integration testing',
            'organization': self.organization,
            'instructor': self.admin,
            'difficulty': 'BEGINNER',
            'duration_hours=10': 10,
            'price': 99.99
        }
        course = course_service.create_course(course_data, created_by=self.admin)
        
        # Create enrollment
        enrollment_service = ServiceFactory.create_enrollment_service(user)
        enrollment = enrollment_service.create_enrollment(
            user=user,
            course=course,
            payment_status='COMPLETED',
            payment_amount=99.99,
            enrolled_by=user
        )
        
        # Verify workflow completed
        self.assertIsNotNone(user)
        self.assertIsNotNone(course)
        self.assertIsNotNone(enrollment)
        self.assertEqual(enrollment.user, user)
        self.assertEqual(enrollment.course, course)
    
    def test_service_transaction_rollback(self):
        """Test service transaction rollback"""
        with self.assertRaises(Exception):
            with transaction.atomic():
                # Create user
                user_service = ServiceFactory.create_user_service(self.admin)
                user_data = {
                    'email': 'rollback@example.com',
                    'password': 'password123',
                    'first_name': 'Rollback',
                    'last_name': 'User',
                    'role': 'STUDENT',
                    'organization': self.organization
                }
                user = user_service.create_user(user_data, created_by=self.admin)
                
                # Force an error
                raise Exception("Forced error for rollback test")
        
        # Verify user was not created
        with self.assertRaises(User.DoesNotExist):
            User.objects.get(email='rollback@example.com')


# Test runner
def run_service_tests():
    """Run all service tests"""
    import unittest
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        UserServiceTestCase,
        CourseServiceTestCase,
        EnrollmentServiceTestCase,
        ServiceManagerTestCase,
        ServiceOrchestratorTestCase,
        ServiceConfigTestCase,
        ServicePerformanceTestCase,
        ServiceIntegrationTestCase
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_service_tests()
    print(f"Tests {'PASSED' if success else 'FAILED'}")
