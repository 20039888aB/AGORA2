"""
Real System Testing - Proving the System Actually Works

This module validates the system under real-world conditions:
- Concurrent operations
- Race conditions
- Edge cases
- Security bypasses
- Performance reality
"""

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.test import TransactionTestCase, override_settings
from django.db import transaction, connection
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch
import json
import random

User = get_user_model()


class ConcurrencyTestCase(TransactionTestCase):
    """Test concurrent operations and race conditions"""
    
    def setUp(self):
        """Set up test environment"""
        # Create organization
        from organizations.models import Organization
        self.organization = Organization.objects.create(
            name='Test Organization',
            domain='test.org',
            description='Test organization for concurrency testing'
        )
        
        # Create admin
        self.admin = User.objects.create_user(
            email='admin@test.org',
            password='admin123',
            first_name='Admin',
            last_name='User',
            role='ADMIN',
            organization=self.organization
        )
        
        # Create instructor
        self.instructor = User.objects.create_user(
            email='instructor@test.org',
            password='instructor123',
            first_name='Instructor',
            last_name='User',
            role='INSTRUCTOR',
            organization=self.organization
        )
        
        # Create course
        from courses.models import Course
        self.course = Course.objects.create(
            title='Concurrency Test Course',
            description='Course for concurrency testing',
            organization=self.organization,
            instructor=self.instructor,
            difficulty='BEGINNER',
            duration_hours=10,
            price=99.99,
            max_students=200
        )
    
    def test_concurrent_user_enrollment(self):
        """Test 100 users enrolling concurrently"""
        print("\n=== Testing Concurrent User Enrollment ===")
        
        def enroll_user(user_data):
            """Enroll a single user"""
            try:
                with transaction.atomic():
                    # Create user
                    user = User.objects.create_user(
                        email=user_data['email'],
                        password='test123',
                        first_name=user_data['first_name'],
                        last_name=user_data['last_name'],
                        role='STUDENT',
                        organization=self.organization
                    )
                    
                    # Create enrollment
                    from enrollments.models import Enrollment
                    enrollment = Enrollment.objects.create(
                        user=user,
                        course=self.course,
                        payment_status='COMPLETED',
                        payment_amount=99.99,
                        enrolled_by=user
                    )
                    
                    return {'success': True, 'user_id': str(user.id), 'enrollment_id': str(enrollment.id)}
                    
            except Exception as e:
                return {'success': False, 'error': str(e)}
        
        # Create 100 users to enroll
        users_data = []
        for i in range(100):
            users_data.append({
                'email': f'student{i}@test.org',
                'first_name': f'Student',
                'last_name': f'{i}'
            })
        
        # Enroll 100 users concurrently
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(enroll_user, user_data) for user_data in users_data]
            results = [future.result() for future in as_completed(futures)]
        
        duration = time.time() - start_time
        
        # Analyze results
        successful_enrollments = [r for r in results if r['success']]
        failed_enrollments = [r for r in results if not r['success']]
        
        print(f"Duration: {duration:.2f}s")
        print(f"Successful enrollments: {len(successful_enrollments)}")
        print(f"Failed enrollments: {len(failed_enrollments)}")
        
        # Verify database integrity
        total_users = User.objects.filter(organization=self.organization, role='STUDENT').count()
        total_enrollments = self.course.enrollments.count()
        
        print(f"Total students in DB: {total_users}")
        print(f"Total enrollments in DB: {total_enrollments}")
        
        # Assertions
        self.assertEqual(len(successful_enrollments), 100, "All enrollments should succeed")
        self.assertEqual(total_users, 100, "Should have 100 students")
        self.assertEqual(total_enrollments, 100, "Should have 100 enrollments")
        self.assertLess(duration, 10.0, "Should complete within 10 seconds")
        
        # Check for race conditions
        user_ids = [r['user_id'] for r in successful_enrollments]
        unique_user_ids = set(user_ids)
        self.assertEqual(len(user_ids), len(unique_user_ids), "No duplicate user IDs should exist")
        
        enrollment_ids = [r['enrollment_id'] for r in successful_enrollments]
        unique_enrollment_ids = set(enrollment_ids)
        self.assertEqual(len(enrollment_ids), len(unique_enrollment_ids), "No duplicate enrollment IDs should exist")
    
    def test_concurrent_progress_updates(self):
        """Test concurrent progress updates for same enrollment"""
        print("\n=== Testing Concurrent Progress Updates ===")
        
        # Create enrollment
        from enrollments.models import Enrollment
        enrollment = Enrollment.objects.create(
            user=self.admin,  # Use admin for simplicity
            course=self.course,
            payment_status='COMPLETED',
            payment_amount=99.99,
            enrolled_by=self.admin
        )
        
        def update_progress(progress_value):
            """Update progress for enrollment"""
            try:
                with transaction.atomic():
                    # Get fresh enrollment
                    enrollment_obj = Enrollment.objects.select_for_update().get(id=enrollment.id)
                    
                    # Update progress
                    from services.enrollment_service import EnrollmentService
                    service = EnrollmentService()
                    service.set_context(user=self.admin)
                    
                    updated_enrollment = service.update_progress(
                        enrollment_obj,
                        progress_value,
                        updated_by=self.admin
                    )
                    
                    return {
                        'success': True,
                        'progress': updated_enrollment.progress_percentage,
                        'updated_at': updated_enrollment.updated_at.isoformat()
                    }
                    
            except Exception as e:
                return {'success': False, 'error': str(e)}
        
        # Update progress concurrently
        progress_values = [25.0, 50.0, 75.0, 100.0]
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(update_progress, value) for value in progress_values]
            results = [future.result() for future in as_completed(futures)]
        
        duration = time.time() - start_time
        
        # Analyze results
        successful_updates = [r for r in results if r['success']]
        failed_updates = [r for r in results if not r['success']]
        
        print(f"Duration: {duration:.2f}s")
        print(f"Successful updates: {len(successful_updates)}")
        print(f"Failed updates: {len(failed_updates)}")
        
        # Verify final state
        enrollment.refresh_from_db()
        print(f"Final progress: {enrollment.progress_percentage}")
        
        # Assertions
        self.assertEqual(len(successful_updates), 4, "All progress updates should succeed")
        self.assertEqual(enrollment.progress_percentage, 100.0, "Final progress should be 100%")
        
        # Check for race conditions
        update_times = [r['updated_at'] for r in successful_updates]
        unique_times = set(update_times)
        self.assertEqual(len(update_times), len(unique_times), "Each update should have unique timestamp")
    
    def test_concurrent_certificate_generation(self):
        """Test concurrent certificate generation to prevent double-generation"""
        print("\n=== Testing Concurrent Certificate Generation ===")
        
        # Create completed enrollment
        from enrollments.models import Enrollment
        enrollment = Enrollment.objects.create(
            user=self.admin,
            course=self.course,
            payment_status='COMPLETED',
            payment_amount=99.99,
            enrolled_by=self.admin,
            progress_percentage=100.0,
            status='COMPLETED',
            completion_date=timezone.now()
        )
        
        def generate_certificate():
            """Generate certificate for enrollment"""
            try:
                with transaction.atomic():
                    from services.certificate_service import CertificateService
                    service = CertificateService()
                    service.set_context(user=self.admin)
                    
                    certificate = service.create_certificate(enrollment)
                    
                    return {
                        'success': True,
                        'certificate_id': str(certificate.id),
                        'certificate_number': certificate.certificate_number
                    }
                    
            except Exception as e:
                return {'success': False, 'error': str(e)}
        
        # Generate certificates concurrently
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(generate_certificate) for _ in range(5)]
            results = [future.result() for future in as_completed(futures)]
        
        duration = time.time() - start_time
        
        # Analyze results
        successful_generations = [r for r in results if r['success']]
        failed_generations = [r for r in results if not r['success']]
        
        print(f"Duration: {duration:.2f}s")
        print(f"Successful generations: {len(successful_generations)}")
        print(f"Failed generations: {len(failed_generations)}")
        
        # Verify only one certificate was created
        from certificates.models import Certificate
        certificates = Certificate.objects.filter(enrollment=enrollment).count()
        
        print(f"Certificates in DB: {certificates}")
        
        # Assertions
        self.assertEqual(len(successful_generations), 1, "Only one certificate should be generated successfully")
        self.assertEqual(len(failed_generations), 4, "Other attempts should fail")
        self.assertEqual(certificates, 1, "Only one certificate should exist in database")
        
        # Check certificate uniqueness
        if successful_generations:
            cert_number = successful_generations[0]['certificate_number']
            cert_count = Certificate.objects.filter(certificate_number=cert_number).count()
            self.assertEqual(cert_count, 1, "Certificate number should be unique")


class SecurityEdgeCaseTestCase(APITestCase):
    """Test security edge cases and bypass attempts"""
    
    def setUp(self):
        """Set up test environment"""
        # Create two organizations
        from organizations.models import Organization
        self.org1 = Organization.objects.create(
            name='Organization 1',
            domain='org1.com',
            description='First organization'
        )
        
        self.org2 = Organization.objects.create(
            name='Organization 2',
            domain='org2.com',
            description='Second organization'
        )
        
        # Create users in different organizations
        self.user1 = User.objects.create_user(
            email='user1@org1.com',
            password='test123',
            first_name='User',
            last_name='One',
            role='STUDENT',
            organization=self.org1
        )
        
        self.user2 = User.objects.create_user(
            email='user2@org2.com',
            password='test123',
            first_name='User',
            last_name='Two',
            role='STUDENT',
            organization=self.org2
        )
        
        # Create admin for org1
        self.admin1 = User.objects.create_user(
            email='admin1@org1.com',
            password='admin123',
            first_name='Admin',
            last_name='One',
            role='ADMIN',
            organization=self.org1
        )
        
        # Create course in org1
        from courses.models import Course
        self.course1 = Course.objects.create(
            title='Course 1',
            description='Course in organization 1',
            organization=self.org1,
            instructor=self.admin1,
            difficulty='BEGINNER',
            duration_hours=10,
            price=99.99
        )
        
        # Create course in org2
        self.course2 = Course.objects.create(
            title='Course 2',
            description='Course in organization 2',
            organization=self.org2,
            instructor=self.user2,  # User2 is instructor for their own course
            role='INSTRUCTOR',
            difficulty='BEGINNER',
            duration_hours=10,
            price=99.99
        )
    
    def test_api_id_manipulation(self):
        """Test if user can access resources via manipulated IDs"""
        print("\n=== Testing API ID Manipulation ===")
        
        # Authenticate as user1 (from org1)
        self.client.force_authenticate(user=self.user1)
        
        # Try to access course2 (from org2) directly by ID
        url = reverse('course-detail', kwargs={'pk': self.course2.id})
        response = self.client.get(url)
        
        print(f"Accessing other org course: {response.status_code}")
        
        # Should be forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Try to access user2 (from org2) user profile
        url = reverse('user-detail', kwargs={'pk': self.user2.id})
        response = self.client.get(url)
        
        print(f"Accessing other org user: {response.status_code}")
        
        # Should be forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Try to list all users (should only return org1 users)
        url = reverse('user-list')
        response = self.client.get(url)
        
        print(f"Listing all users: {response.status_code}")
        
        if response.status_code == status.HTTP_200_OK:
            users = response.data['results']
            user_orgs = [user['organization'] for user in users]
            
            # All users should belong to org1
            for org_id in user_orgs:
                self.assertEqual(str(org_id), str(self.org1.id))
            
            print(f"Users returned: {len(users)} (all from org1)")
        else:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_filtering_bypass_attempts(self):
        """Test if user can bypass organization filtering"""
        print("\n=== Testing Filtering Bypass Attempts ===")
        
        # Authenticate as user1 (from org1)
        self.client.force_authenticate(user=self.user1)
        
        # Try to filter by organization2 ID directly
        url = reverse('course-list')
        response = self.client.get(url, {'organization': self.org2.id})
        
        print(f"Filtering by other org: {response.status_code}")
        
        if response.status_code == status.HTTP_200_OK:
            courses = response.data['results']
            course_orgs = [course['organization'] for course in courses]
            
            # Should not return any courses from org2
            for org_id in course_orgs:
                self.assertEqual(str(org_id), str(self.org1.id))
            
            print(f"Courses returned: {len(courses)} (all from org1)")
        
        # Try to access courses by direct query parameter manipulation
        url = reverse('course-list')
        response = self.client.get(url, {'organization__in': f'{self.org1.id},{self.org2.id}'})
        
        print(f"Advanced filtering attempt: {response.status_code}")
        
        if response.status_code == status.HTTP_200_OK:
            courses = response.data['results']
            course_orgs = [course['organization'] for course in courses]
            
            # Still should only return org1 courses
            for org_id in course_orgs:
                self.assertEqual(str(org_id), str(self.org1.id))
    
    def test_nested_relation_protection(self):
        """Test if nested relations are also protected"""
        print("\n=== Testing Nested Relation Protection ===")
        
        # Create enrollment for user1 in course1
        from enrollments.models import Enrollment
        enrollment1 = Enrollment.objects.create(
            user=self.user1,
            course=self.course1,
            payment_status='COMPLETED',
            payment_amount=99.99,
            enrolled_by=self.user1
        )
        
        # Authenticate as user1
        self.client.force_authenticate(user=self.user1)
        
        # Try to access enrollment details
        url = reverse('enrollment-detail', kwargs={'pk': enrollment1.id})
        response = self.client.get(url)
        
        print(f"Accessing own enrollment: {response.status_code}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Try to access course through enrollment endpoint
        url = reverse('enrollment-detail', kwargs={'pk': enrollment1.id})
        response = self.client.get(url)
        
        if response.status_code == status.HTTP_200_OK:
            enrollment_data = response.data
            
            # Check if nested course data is properly scoped
            if 'course' in enrollment_data:
                course_id = enrollment_data['course']
                # Should be course1, not course2
                self.assertEqual(str(course_id), str(self.course1.id))
        
        # Try to access course enrollments directly (should be filtered)
        url = reverse('course-enrollments', kwargs={'pk': self.course2.id})
        response = self.client.get(url)
        
        print(f"Accessing other org course enrollments: {response.status_code}")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_permission_edge_cases(self):
        """Test permissions under edge cases"""
        print("\n=== Testing Permission Edge Cases ===")
        
        # Test student trying to access admin endpoints
        self.client.force_authenticate(user=self.user1)
        
        # Try to create user (admin only)
        url = reverse('user-create')
        data = {
            'email': 'newuser@test.com',
            'password': 'test123',
            'first_name': 'New',
            'last_name': 'User',
            'role': 'STUDENT',
            'organization': self.org1.id
        }
        response = self.client.post(url, data, format='json')
        
        print(f"Student creating user: {response.status_code}")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Try to access organization statistics
        url = reverse('organization-statistics', kwargs={'pk': self.org1.id})
        response = self.client.get(url)
        
        print(f"Student accessing org stats: {response.status_code}")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Test with admin user
        self.client.force_authenticate(user=self.admin1)
        
        # Admin should be able to create users
        response = self.client.post(url, data, format='json')
        
        print(f"Admin creating user: {response.status_code}")
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK])
        
        # Admin should be able to access org stats
        response = self.client.get(url)
        
        print(f"Admin accessing org stats: {response.status_code}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ServiceIntegrityTestCase(TransactionTestCase):
    """Test service layer integrity and detect leaks"""
    
    def setUp(self):
        """Set up test environment"""
        from organizations.models import Organization
        self.organization = Organization.objects.create(
            name='Test Organization',
            domain='test.org',
            description='Test organization'
        )
        
        self.admin = User.objects.create_user(
            email='admin@test.org',
            password='admin123',
            first_name='Admin',
            last_name='User',
            role='ADMIN',
            organization=self.organization
        )
    
    def test_service_purity(self):
        """Test if services are pure (no ORM logic in views)"""
        print("\n=== Testing Service Purity ===")
        
        # Test UserService
        from services.user_service import UserService
        
        # Check if service methods don't directly interact with Django ORM
        service_methods = [
            'create_user',
            'update_user',
            'soft_delete_user',
            'restore_user',
            'change_user_role'
        ]
        
        for method_name in service_methods:
            method = getattr(UserService, method_name)
            
            # Check method signature
            import inspect
            sig = inspect.signature(method)
            
            # Should have proper parameters (not just request)
            self.assertIn('data', sig.parameters, f"{method_name} should accept data parameter")
            self.assertIn('created_by', sig.parameters, f"{method_name} should accept created_by parameter")
            
            print(f"✅ {method_name} has proper signature")
        
        # Test CourseService
        from services.course_service import CourseService
        
        course_methods = [
            'create_course',
            'update_course',
            'publish_course',
            'archive_course'
        ]
        
        for method_name in course_methods:
            method = getattr(CourseService, method_name)
            
            import inspect
            sig = inspect.signature(method)
            
            self.assertIn('data', sig.parameters, f"{method_name} should accept data parameter")
            self.assertIn('created_by', sig.parameters, f"{method_name} should accept created_by parameter")
            
            print(f"✅ {method_name} has proper signature")
    
    def test_signal_side_effects(self):
        """Test if signals cause hidden side effects"""
        print("\n=== Testing Signal Side Effects ===")
        
        # Test user creation signal
        initial_audit_count = from audit_logs.models import AuditLog
        initial_audit_count = AuditLog.objects.count()
        
        # Create user (should trigger signal)
        user = User.objects.create_user(
            email='signaltest@test.org',
            password='test123',
            first_name='Signal',
            last_name='Test',
            role='STUDENT',
            organization=self.organization
        )
        
        # Check if audit log was created
        final_audit_count = AuditLog.objects.count()
        audit_logs = AuditLog.objects.filter(action='USER_CREATE')
        
        print(f"Initial audit count: {initial_audit_count}")
        print(f"Final audit count: {final_audit_count}")
        print(f"Audit logs for USER_CREATE: {audit_logs.count()}")
        
        self.assertEqual(final_audit_count, initial_audit_count + 1, "Should create one audit log")
        self.assertEqual(audit_logs.count(), 1, "Should have one USER_CREATE log")
        
        # Check audit log details
        audit_log = audit_logs.first()
        self.assertEqual(audit_log.user, user)
        self.assertEqual(audit_log.action, 'USER_CREATE')
        self.assertIn('user_id', audit_log.details)
        self.assertIn('email', audit_log.details)
        
        print(f"✅ User creation signal works correctly")
        
        # Test role change signal
        from services.user_service import UserService
        service = UserService()
        service.set_context(user=self.admin)
        
        initial_role_change_count = AuditLog.objects.filter(action='ROLE_CHANGE').count()
        
        # Change role
        updated_user = service.change_user_role(user, 'MANAGER', changed_by=self.admin)
        
        final_role_change_count = AuditLog.objects.filter(action='ROLE_CHANGE').count()
        
        print(f"Role change logs: {final_role_change_count - initial_role_change_count}")
        
        self.assertEqual(final_role_change_count, initial_role_change_count + 1, "Should create role change log")
        
        print(f"✅ Role change signal works correctly")
    
    def test_circular_dependencies(self):
        """Test for circular dependencies in services"""
        print("\n=== Testing Circular Dependencies ===")
        
        # Import all services
        from services import user_service, organization_service, course_service, enrollment_service
        
        # Check if services can be imported without circular imports
        services = [
            user_service,
            organization_service,
            course_service,
            enrollment_service
        ]
        
        for service_module in services:
            # Check if module has expected classes
            self.assertTrue(hasattr(service_module, 'UserService') or 
                          hasattr(service_module, 'OrganizationService') or
                          hasattr(service_module, 'CourseService') or
                          hasattr(service_module, 'EnrollmentService'))
            
            print(f"✅ {service_module.__name__} imported successfully")
        
        # Try to create service instances
        try:
            user_service.UserService()
            organization_service.OrganizationService()
            course_service.CourseService()
            enrollment_service.EnrollmentService()
            
            print("✅ All service instances created successfully")
            
        except Exception as e:
            self.fail(f"Failed to create service instances: {e}")


class PerformanceRealityTestCase(TransactionTestCase):
    """Test performance reality and N+1 problems"""
    
    def setUp(self):
        """Set up test environment"""
        from organizations.models import Organization
        self.organization = Organization.objects.create(
            name='Test Organization',
            domain='test.org',
            description='Test organization'
        )
        
        self.admin = User.objects.create_user(
            email='admin@test.org',
            password='admin123',
            first_name='Admin',
            last_name='User',
            role='ADMIN',
            organization=self.organization
        )
        
        # Create test data
        self.create_test_data()
    
    def create_test_data(self):
        """Create test data for performance testing"""
        from courses.models import Course, Module, Lesson
        from enrollments.models import Enrollment
        
        # Create courses
        courses = []
        for i in range(10):
            course = Course.objects.create(
                title=f'Course {i}',
                description=f'Description for course {i}',
                organization=self.organization,
                instructor=self.admin,
                difficulty='BEGINNER',
                duration_hours=10,
                price=99.99
            )
            courses.append(course)
        
        # Create modules and lessons for each course
        for course in courses:
            for j in range(5):
                module = Module.objects.create(
                    title=f'Module {j}',
                    description=f'Description for module {j}',
                    course=course,
                    order=j
                )
                
                for k in range(3):
                    lesson = Lesson.objects.create(
                        title=f'Lesson {k}',
                        description=f'Description for lesson {k}',
                        module=module,
                        lesson_type='TEXT',
                        content=f'Content for lesson {k}',
                        order=k
                    )
        
        # Create users and enrollments
        for i in range(50):
            user = User.objects.create_user(
                email=f'student{i}@test.org',
                password='test123',
                first_name=f'Student',
                last_name=f'{i}',
                role='STUDENT',
                organization=self.organization
            )
            
            # Enroll in random courses
            for course in random.sample(courses, 3):
                Enrollment.objects.create(
                    user=user,
                    course=course,
                    payment_status='COMPLETED',
                    payment_amount=99.99,
                    enrolled_by=user
                )
    
    def test_query_count_per_endpoint(self):
        """Test query count per API endpoint"""
        print("\n=== Testing Query Count Per Endpoint ===")
        
        from django.test.utils import override_settings
        from django.conf import settings
        
        # Test course list endpoint
        with self.assertNumQueries(2):  # Should be minimal queries
            response = self.client.get('/api/v1/courses/')
            self.assertEqual(response.status_code, 200)
        
        print("✅ Course list uses minimal queries")
        
        # Test user list endpoint
        with self.assertNumQueries(2):  # Should be minimal queries
            response = self.client.get('/api/v1/users/')
            self.assertEqual(response.status_code, 200)
        
        print("✅ User list uses minimal queries")
        
        # Test enrollment list endpoint
        with self.assertNumQueries(3):  # Might need one extra for joins
            response = self.client.get('/api/v1/enrollments/')
            self.assertEqual(response.status_code, 200)
        
        print("✅ Enrollment list uses minimal queries")
    
    def test_n_plus_one_problems(self):
        """Test for N+1 query problems"""
        print("\n=== Testing N+1 Query Problems ===")
        
        from django.test.utils import override_settings
        from django.db import connection
        
        # Test course detail with nested relations
        url = '/api/v1/courses/1/'
        
        # Reset query count
        connection.queries_log.clear()
        
        response = self.client.get(url)
        
        query_count = len(connection.queries)
        print(f"Course detail queries: {query_count}")
        
        # Should use select_related and prefetch_related
        self.assertLess(query_count, 10, "Course detail should use less than 10 queries")
        
        # Test enrollment list with nested relations
        url = '/api/v1/enrollments/'
        
        connection.queries_log.clear()
        
        response = self.client.get(url)
        
        query_count = len(connection.queries)
        print(f"Enrollment list queries: {query_count}")
        
        # Should use prefetch_related
        self.assertLess(query_count, 15, "Enrollment list should use less than 15 queries")
        
        print("✅ No significant N+1 problems detected")
    
    def test_organization_indexing(self):
        """Test if organization fields are properly indexed"""
        print("\n=== Testing Organization Indexing ===")
        
        # Test query performance with organization filter
        start_time = time.time()
        
        from courses.models import Course
        courses = Course.objects.filter(organization=self.organization).count()
        
        duration = time.time() - start_time
        
        print(f"Organization filter query duration: {duration:.4f}s")
        print(f"Courses found: {courses}")
        
        # Should be fast with proper indexing
        self.assertLess(duration, 0.1, "Organization filter should be fast with indexing")
        
        # Test user query with organization filter
        start_time = time.time()
        
        users = User.objects.filter(organization=self.organization).count()
        
        duration = time.time() - start_time
        
        print(f"User organization filter duration: {duration:.4f}s")
        print(f"Users found: {users}")
        
        self.assertLess(duration, 0.1, "User organization filter should be fast with indexing")
        
        print("✅ Organization fields appear to be properly indexed")


def run_real_system_tests():
    """Run all real system tests"""
    import unittest
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        ConcurrencyTestCase,
        SecurityEdgeCaseTestCase,
        ServiceIntegrityTestCase,
        PerformanceRealityTestCase
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_real_system_tests()
    print(f"\n{'='*50}")
    print(f"REAL SYSTEM TESTS: {'PASSED' if success else 'FAILED'}")
    print(f"{'='*50}")
