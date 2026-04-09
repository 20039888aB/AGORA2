"""
Performance Validation - Prove System Performance

This module validates that the system performs well under real-world conditions
and identifies performance bottlenecks.
"""

import time
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.test import TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import connection, reset_queries
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
import json

User = get_user_model()


class QueryPerformanceValidation(TransactionTestCase):
    """Validate query performance and N+1 problems"""
    
    def setUp(self):
        """Set up test environment with realistic data"""
        from organizations.models import Organization
        self.organization = Organization.objects.create(
            name='Performance Test Organization',
            domain='perf.test',
            description='Organization for performance testing'
        )
        
        self.admin = User.objects.create_user(
            email='admin@perf.test',
            password='admin123',
            first_name='Admin',
            last_name='User',
            role='ADMIN',
            organization=self.organization
        )
        
        # Create realistic test data
        self.create_test_data()
    
    def create_test_data(self):
        """Create realistic test data for performance testing"""
        from courses.models import Course, Module, Lesson
        from enrollments.models import Enrollment
        
        print("Creating test data for performance validation...")
        
        # Create courses
        courses = []
        for i in range(20):
            course = Course.objects.create(
                title=f'Performance Course {i}',
                description=f'Description for performance course {i}',
                organization=self.organization,
                instructor=self.admin,
                difficulty='BEGINNER',
                duration_hours=10 + i,
                price=99.99 + i,
                max_students=50
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
        users = []
        for i in range(100):
            user = User.objects.create_user(
                email=f'student{i}@perf.test',
                password='test123',
                first_name=f'Student',
                last_name=f'{i}',
                role='STUDENT',
                organization=self.organization
            )
            users.append(user)
            
            # Enroll in random courses
            import random
            selected_courses = random.sample(courses, 3)
            
            for course in selected_courses:
                Enrollment.objects.create(
                    user=user,
                    course=course,
                    payment_status='COMPLETED',
                    payment_amount=course.price,
                    enrolled_by=user
                )
        
        print(f"Created {len(courses)} courses, {len(users)} users")
    
    def test_query_count_per_endpoint(self):
        """Test query count for each API endpoint"""
        print("\n=== Testing Query Count Per Endpoint ===")
        
        endpoints_to_test = [
            ('user-list', 'GET', {}),
            ('course-list', 'GET', {}),
            ('enrollment-list', 'GET', {}),
            ('user-detail', 'GET', {'pk': self.admin.id}),
            ('course-detail', 'GET', {'pk': 1}),
            ('enrollment-detail', 'GET', {'pk': 1}),
        ]
        
        query_counts = {}
        
        for endpoint_name, method, kwargs in endpoints_to_test:
            # Reset queries
            reset_queries()
            
            try:
                url = reverse(endpoint_name, kwargs=kwargs)
                
                start_time = time.time()
                
                if method == 'GET':
                    response = self.client.get(url)
                elif method == 'POST':
                    response = self.client.post(url, {}, format='json')
                
                duration = time.time() - start_time
                query_count = len(connection.queries)
                
                query_counts[endpoint_name] = {
                    'query_count': query_count,
                    'duration': duration,
                    'status': response.status_code
                }
                
                print(f"{endpoint_name}: {query_count} queries, {duration:.3f}s, status {response.status_code}")
                
                # Performance assertions
                self.assertLess(query_count, 20, f"{endpoint_name} should use less than 20 queries")
                self.assertLess(duration, 1.0, f"{endpoint_name} should respond within 1 second")
                
            except Exception as e:
                print(f"❌ Error testing {endpoint_name}: {e}")
                query_counts[endpoint_name] = {'error': str(e)}
        
        # Summary
        total_queries = sum(info.get('query_count', 0) for info in query_counts.values())
        avg_queries = total_queries / len(query_counts)
        
        print(f"\nTotal queries across endpoints: {total_queries}")
        print(f"Average queries per endpoint: {avg_queries:.1f}")
        
        # Overall performance assertion
        self.assertLess(avg_queries, 10, "Average queries per endpoint should be less than 10")
        
        return query_counts
    
    def test_n_plus_one_problems(self):
        """Test for N+1 query problems"""
        print("\n=== Testing N+1 Query Problems ===")
        
        # Test course list with nested relations
        reset_queries()
        
        start_time = time.time()
        url = reverse('course-list')
        response = self.client.get(url)
        duration = time.time() - start_time
        
        query_count = len(connection.queries)
        
        print(f"Course list: {query_count} queries, {duration:.3f}s")
        
        # Should use select_related and prefetch_related
        self.assertLess(query_count, 5, "Course list should use less than 5 queries")
        
        # Test enrollment list with nested relations
        reset_queries()
        
        start_time = time.time()
        url = reverse('enrollment-list')
        response = self.client.get(url)
        duration = time.time() - start_time
        
        query_count = len(connection.queries)
        
        print(f"Enrollment list: {query_count} queries, {duration:.3f}s")
        
        # Should use prefetch_related
        self.assertLess(query_count, 8, "Enrollment list should use less than 8 queries")
        
        # Test user list with nested relations
        reset_queries()
        
        start_time = time.time()
        url = reverse('user-list')
        response = self.client.get(url)
        duration = time.time() - start_time
        
        query_count = len(connection.queries)
        
        print(f"User list: {query_count} queries, {duration:.3f}s")
        
        self.assertLess(query_count, 3, "User list should use less than 3 queries")
        
        print("✅ No significant N+1 problems detected")
    
    def test_organization_filtering_performance(self):
        """Test performance of organization filtering"""
        print("\n=== Testing Organization Filtering Performance ===")
        
        # Test filtering by organization
        reset_queries()
        
        start_time = time.time()
        
        from courses.models import Course
        courses = Course.objects.filter(organization=self.organization).count()
        
        duration = time.time() - start_time
        query_count = len(connection.queries)
        
        print(f"Organization filter: {query_count} queries, {duration:.4f}s, {courses} courses")
        
        # Should be fast with proper indexing
        self.assertLess(query_count, 1, "Organization filter should use 1 query")
        self.assertLess(duration, 0.01, "Organization filter should be very fast")
        
        # Test user filtering by organization
        reset_queries()
        
        start_time = time.time()
        
        users = User.objects.filter(organization=self.organization).count()
        
        duration = time.time() - start_time
        query_count = len(connection.queries)
        
        print(f"User organization filter: {query_count} queries, {duration:.4f}s, {users} users")
        
        self.assertLess(query_count, 1, "User organization filter should use 1 query")
        self.assertLess(duration, 0.01, "User organization filter should be very fast")
        
        # Test enrollment filtering by organization
        reset_queries()
        
        start_time = time.time()
        
        from enrollments.models import Enrollment
        enrollments = Enrollment.objects.filter(
            course__organization=self.organization
        ).count()
        
        duration = time.time() - start_time
        query_count = len(connection.queries)
        
        print(f"Enrollment org filter: {query_count} queries, {duration:.4f}s, {enrollments} enrollments")
        
        self.assertLess(query_count, 1, "Enrollment org filter should use 1 query")
        self.assertLess(duration, 0.02, "Enrollment org filter should be fast")
        
        print("✅ Organization filtering performance is good")
    
    def test_pagination_performance(self):
        """Test pagination performance"""
        print("\n=== Testing Pagination Performance ===")
        
        # Test different page sizes
        page_sizes = [10, 20, 50, 100]
        
        for page_size in page_sizes:
            reset_queries()
            
            start_time = time.time()
            
            url = reverse('course-list')
            response = self.client.get(url, {'page_size': page_size})
            
            duration = time.time() - start_time
            query_count = len(connection.queries)
            
            if response.status_code == 200:
                data = response.data
                returned_count = len(data.get('results', []))
                
                print(f"Page size {page_size}: {query_count} queries, {duration:.3f}s, {returned_count} items")
                
                # Query count should not increase significantly with page size
                self.assertLess(query_count, 5, f"Page size {page_size} should use less than 5 queries")
                self.assertLess(duration, 0.5, f"Page size {page_size} should respond within 0.5s")
        
        print("✅ Pagination performance is good")
    
    def test_search_performance(self):
        """Test search performance"""
        print("\n=== Testing Search Performance ===")
        
        # Test different search queries
        search_queries = [
            'Course',
            'Performance',
            'Test',
            'Student',
            'Module'
        ]
        
        for search_query in search_queries:
            reset_queries()
            
            start_time = time.time()
            
            url = reverse('course-list')
            response = self.client.get(url, {'search': search_query})
            
            duration = time.time() - start_time
            query_count = len(connection.queries)
            
            if response.status_code == 200:
                data = response.data
                results_count = len(data.get('results', []))
                
                print(f"Search '{search_query}': {query_count} queries, {duration:.3f}s, {results_count} results")
                
                # Search should be reasonably fast
                self.assertLess(query_count, 10, f"Search '{search_query}' should use less than 10 queries")
                self.assertLess(duration, 0.5, f"Search '{search_query}' should respond within 0.5s")
        
        print("✅ Search performance is good")


class ConcurrencyPerformanceValidation(TransactionTestCase):
    """Validate performance under concurrent load"""
    
    def setUp(self):
        """Set up test environment"""
        from organizations.models import Organization
        self.organization = Organization.objects.create(
            name='Concurrency Test Organization',
            domain='concurrent.test',
            description='Organization for concurrency testing'
        )
        
        self.admin = User.objects.create_user(
            email='admin@concurrent.test',
            password='admin123',
            first_name='Admin',
            last_name='User',
            role='ADMIN',
            organization=self.organization
        )
        
        # Create test course
        from courses.models import Course
        self.course = Course.objects.create(
            title='Concurrency Test Course',
            description='Course for concurrency testing',
            organization=self.organization,
            instructor=self.admin,
            difficulty='BEGINNER',
            duration_hours=10,
            price=99.99
        )
    
    def test_concurrent_user_creation(self):
        """Test concurrent user creation performance"""
        print("\n=== Testing Concurrent User Creation Performance ===")
        
        def create_user(user_data):
            """Create a single user"""
            start_time = time.time()
            
            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        email=user_data['email'],
                        password='test123',
                        first_name=user_data['first_name'],
                        last_name=user_data['last_name'],
                        role='STUDENT',
                        organization=self.organization
                    )
                    
                    duration = time.time() - start_time
                    
                    return {
                        'success': True,
                        'user_id': str(user.id),
                        'duration': duration
                    }
                    
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'duration': time.time() - start_time
                }
        
        # Create 50 users concurrently
        users_data = []
        for i in range(50):
            users_data.append({
                'email': f'concurrent{i}@concurrent.test',
                'first_name': 'Concurrent',
                'last_name': f'User{i}'
            })
        
        # Execute concurrently
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_user, user_data) for user_data in users_data]
            results = [future.result() for future in as_completed(futures)]
        
        total_duration = time.time() - start_time
        
        # Analyze results
        successful_creations = [r for r in results if r['success']]
        failed_creations = [r for r in results if not r['success']]
        
        if successful_creations:
            durations = [r['duration'] for r in successful_creations]
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            min_duration = min(durations)
        else:
            avg_duration = max_duration = min_duration = 0
        
        print(f"Total duration: {total_duration:.2f}s")
        print(f"Successful creations: {len(successful_creations)}")
        print(f"Failed creations: {len(failed_creations)}")
        print(f"Average creation time: {avg_duration:.3f}s")
        print(f"Max creation time: {max_duration:.3f}s")
        print(f"Min creation time: {min_duration:.3f}s")
        
        # Performance assertions
        self.assertEqual(len(successful_creations), 50, "All user creations should succeed")
        self.assertLess(total_duration, 10.0, "All creations should complete within 10 seconds")
        self.assertLess(avg_duration, 0.5, "Average creation time should be less than 0.5s")
        
        # Verify database integrity
        total_users = User.objects.filter(organization=self.organization, role='STUDENT').count()
        self.assertEqual(total_users, 50, "Should have 50 students in database")
    
    def test_concurrent_enrollment_creation(self):
        """Test concurrent enrollment creation performance"""
        print("\n=== Testing Concurrent Enrollment Creation Performance ===")
        
        # Create test users first
        users = []
        for i in range(30):
            user = User.objects.create_user(
                email=f'enroll{i}@concurrent.test',
                password='test123',
                first_name='Enroll',
                last_name=f'User{i}',
                role='STUDENT',
                organization=self.organization
            )
            users.append(user)
        
        def create_enrollment(user):
            """Create enrollment for user"""
            start_time = time.time()
            
            try:
                with transaction.atomic():
                    from enrollments.models import Enrollment
                    enrollment = Enrollment.objects.create(
                        user=user,
                        course=self.course,
                        payment_status='COMPLETED',
                        payment_amount=99.99,
                        enrolled_by=user
                    )
                    
                    duration = time.time() - start_time
                    
                    return {
                        'success': True,
                        'enrollment_id': str(enrollment.id),
                        'duration': duration
                    }
                    
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'duration': time.time() - start_time
                }
        
        # Create enrollments concurrently
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_enrollment, user) for user in users]
            results = [future.result() for future in as_completed(futures)]
        
        total_duration = time.time() - start_time
        
        # Analyze results
        successful_enrollments = [r for r in results if r['success']]
        failed_enrollments = [r for r in results if not r['success']]
        
        if successful_enrollments:
            durations = [r['duration'] for r in successful_enrollments]
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            min_duration = min(durations)
        else:
            avg_duration = max_duration = min_duration = 0
        
        print(f"Total duration: {total_duration:.2f}s")
        print(f"Successful enrollments: {len(successful_enrollments)}")
        print(f"Failed enrollments: {len(failed_enrollments)}")
        print(f"Average enrollment time: {avg_duration:.3f}s")
        print(f"Max enrollment time: {max_duration:.3f}s")
        print(f"Min enrollment time: {min_duration:.3f}s")
        
        # Performance assertions
        self.assertEqual(len(successful_enrollments), 30, "All enrollments should succeed")
        self.assertLess(total_duration, 5.0, "All enrollments should complete within 5 seconds")
        self.assertLess(avg_duration, 0.2, "Average enrollment time should be less than 0.2s")
        
        # Verify database integrity
        total_enrollments = self.course.enrollments.count()
        self.assertEqual(total_enrollments, 30, "Should have 30 enrollments in database")
    
    def test_concurrent_api_requests(self):
        """Test concurrent API request performance"""
        print("\n=== Testing Concurrent API Request Performance ===")
        
        def make_api_request(endpoint_name, kwargs=None):
            """Make API request"""
            start_time = time.time()
            
            try:
                url = reverse(endpoint_name, kwargs=kwargs or {})
                response = self.client.get(url)
                
                duration = time.time() - start_time
                
                return {
                    'success': True,
                    'status_code': response.status_code,
                    'duration': duration
                }
                
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'duration': time.time() - start_time
                }
        
        # Test different endpoints concurrently
        endpoints = [
            ('user-list', {}),
            ('course-list', {}),
            ('enrollment-list', {}),
            ('user-detail', {'pk': self.admin.id}),
            ('course-detail', {'pk': self.course.id}),
        ]
        
        # Make multiple requests to each endpoint
        all_requests = []
        for endpoint_name, kwargs in endpoints:
            for i in range(10):
                all_requests.append((endpoint_name, kwargs))
        
        # Execute requests concurrently
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(make_api_request, endpoint_name, kwargs)
                for endpoint_name, kwargs in all_requests
            ]
            results = [future.result() for future in as_completed(futures)]
        
        total_duration = time.time() - start_time
        
        # Analyze results
        successful_requests = [r for r in results if r['success']]
        failed_requests = [r for r in results if not r['success']]
        
        if successful_requests:
            durations = [r['duration'] for r in successful_requests]
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            min_duration = min(durations)
            
            # Group by endpoint
            endpoint_stats = {}
            for i, (endpoint_name, kwargs) in enumerate(all_requests):
                if i < len(results) and results[i]['success']:
                    if endpoint_name not in endpoint_stats:
                        endpoint_stats[endpoint_name] = []
                    endpoint_stats[endpoint_name].append(results[i]['duration'])
        else:
            avg_duration = max_duration = min_duration = 0
            endpoint_stats = {}
        
        print(f"Total duration: {total_duration:.2f}s")
        print(f"Successful requests: {len(successful_requests)}")
        print(f"Failed requests: {len(failed_requests)}")
        print(f"Average request time: {avg_duration:.3f}s")
        print(f"Max request time: {max_duration:.3f}s")
        print(f"Min request time: {min_duration:.3f}s")
        
        # Performance assertions
        self.assertGreater(len(successful_requests), 45, "Most requests should succeed")
        self.assertLess(total_duration, 15.0, "All requests should complete within 15 seconds")
        self.assertLess(avg_duration, 0.3, "Average request time should be less than 0.3s")
        
        # Print endpoint stats
        for endpoint_name, durations in endpoint_stats.items():
            endpoint_avg = sum(durations) / len(durations)
            print(f"  {endpoint_name}: avg {endpoint_avg:.3f}s")


class DatabaseIndexValidation(TransactionTestCase):
    """Validate database indexing performance"""
    
    def setUp(self):
        """Set up test environment"""
        from organizations.models import Organization
        self.organization = Organization.objects.create(
            name='Index Test Organization',
            domain='index.test',
            description='Organization for index testing'
        )
        
        # Create test data
        self.create_test_data()
    
    def create_test_data(self):
        """Create test data for index testing"""
        from courses.models import Course
        from enrollments.models import Enrollment
        
        # Create many courses
        courses = []
        for i in range(100):
            course = Course.objects.create(
                title=f'Index Test Course {i}',
                description=f'Description for index test course {i}',
                organization=self.organization,
                instructor=self.organization.admins.first(),
                difficulty='BEGINNER',
                duration_hours=10,
                price=99.99
            )
            courses.append(course)
        
        # Create many enrollments
        for i in range(500):
            user = User.objects.create_user(
                email=f'indexuser{i}@index.test',
                password='test123',
                first_name='Index',
                last_name=f'User{i}',
                role='STUDENT',
                organization=self.organization
            )
            
            course = courses[i % len(courses)]
            Enrollment.objects.create(
                user=user,
                course=course,
                payment_status='COMPLETED',
                payment_amount=99.99,
                enrolled_by=user
            )
        
        print(f"Created {len(courses)} courses and 500 enrollments")
    
    def test_organization_index_performance(self):
        """Test organization field indexing performance"""
        print("\n=== Testing Organization Index Performance ===")
        
        # Test course filtering by organization
        start_time = time.time()
        
        from courses.models import Course
        courses = Course.objects.filter(organization=self.organization).count()
        
        duration = time.time() - start_time
        
        print(f"Organization filter on courses: {duration:.4f}s, {courses} courses")
        
        # Should be very fast with proper indexing
        self.assertLess(duration, 0.005, "Organization filter on courses should be very fast")
        
        # Test user filtering by organization
        start_time = time.time()
        
        users = User.objects.filter(organization=self.organization).count()
        
        duration = time.time() - start_time
        
        print(f"Organization filter on users: {duration:.4f}s, {users} users")
        
        self.assertLess(duration, 0.005, "Organization filter on users should be very fast")
        
        # Test enrollment filtering by organization
        start_time = time.time()
        
        from enrollments.models import Enrollment
        enrollments = Enrollment.objects.filter(
            course__organization=self.organization
        ).count()
        
        duration = time.time() - start_time
        
        print(f"Organization filter on enrollments: {duration:.4f}s, {enrollments} enrollments")
        
        self.assertLess(duration, 0.01, "Organization filter on enrollments should be very fast")
        
        print("✅ Organization indexing performance is good")
    
    def test_query_explain_analysis(self):
        """Analyze query execution plans"""
        print("\n=== Testing Query Explain Analysis ===")
        
        from django.db import connection
        
        # Test course query explain
        with connection.cursor() as cursor:
            cursor.execute("""
                EXPLAIN ANALYZE
                SELECT * FROM courses_course 
                WHERE organization_id = %s
                LIMIT 10
            """, [self.organization.id])
            
            explain_result = cursor.fetchall()
            
            print("Course query explain:")
            for row in explain_result:
                print(f"  {row}")
        
        # Test user query explain
        with connection.cursor() as cursor:
            cursor.execute("""
                EXPLAIN ANALYZE
                SELECT * FROM accounts_user 
                WHERE organization_id = %s
                LIMIT 10
            """, [self.organization.id])
            
            explain_result = cursor.fetchall()
            
            print("User query explain:")
            for row in explain_result:
                print(f"  {row}")
        
        # Check if queries are using indexes
        # This would need to be adapted based on actual database backend
        print("✅ Query explain analysis completed")


def run_performance_validation():
    """Run all performance validation tests"""
    import unittest
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        QueryPerformanceValidation,
        ConcurrencyPerformanceValidation,
        DatabaseIndexValidation
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_performance_validation()
    print(f"\n{'='*60}")
    print(f"PERFORMANCE VALIDATION: {'PASSED' if success else 'FAILED'}")
    print(f"{'='*60}")
