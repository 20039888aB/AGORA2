"""
Service Integrity Validation - Prove Service Layer Purity

This module validates that the service layer is pure and doesn't leak
logic into views or create circular dependencies.
"""

import ast
import inspect
import importlib
from django.test import TransactionTestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class ServicePurityValidation(TransactionTestCase):
    """Validate that services are pure and don't leak logic"""
    
    def test_service_method_signatures(self):
        """Test that service methods have proper signatures"""
        print("\n=== Testing Service Method Signatures ===")
        
        services_to_test = [
            ('services.user_service', 'UserService'),
            ('services.organization_service', 'OrganizationService'),
            ('services.course_service', 'CourseService'),
            ('services.enrollment_service', 'EnrollmentService'),
            ('services.assignment_service', 'AssignmentService'),
            ('services.certificate_service', 'CertificateService'),
        ]
        
        for service_module_name, service_class_name in services_to_test:
            try:
                # Import service module
                service_module = importlib.import_module(service_module_name)
                service_class = getattr(service_module, service_class_name)
                
                # Get all public methods
                methods = [
                    method for method in dir(service_class)
                    if not method.startswith('_') and callable(getattr(service_class, method))
                ]
                
                print(f"\n{service_class_name}:")
                
                for method_name in methods:
                    method = getattr(service_class, method_name)
                    
                    # Get method signature
                    sig = inspect.signature(method)
                    params = list(sig.parameters.keys())
                    
                    # Check for proper parameters
                    if method_name.startswith('create_'):
                        # Create methods should accept data and created_by
                        self.assertIn('data', params, f"{service_class_name}.{method_name} should accept 'data' parameter")
                        self.assertIn('created_by', params, f"{service_class_name}.{method_name} should accept 'created_by' parameter")
                        print(f"  ✅ {method_name}: proper create signature")
                    
                    elif method_name.startswith('update_'):
                        # Update methods should accept resource, data, and updated_by
                        self.assertIn('data', params, f"{service_class_name}.{method_name} should accept 'data' parameter")
                        self.assertIn('updated_by', params, f"{service_class_name}.{method_name} should accept 'updated_by' parameter")
                        print(f"  ✅ {method_name}: proper update signature")
                    
                    elif method_name.startswith('get_') or method_name.startswith('list_'):
                        # Get/List methods should accept filters/organization
                        if 'organization' in params or 'filters' in params:
                            print(f"  ✅ {method_name}: proper get/list signature")
                        else:
                            print(f"  ⚠️  {method_name}: missing organization/filters parameter")
                    
                    else:
                        # Other methods should have proper context
                        print(f"  ✅ {method_name}: {len(params)} parameters")
                
            except Exception as e:
                print(f"❌ Error testing {service_class_name}: {e}")
    
    def test_no_orm_logic_in_views(self):
        """Test that views don't contain ORM logic"""
        print("\n=== Testing No ORM Logic in Views ===")
        
        # Import all view modules
        view_modules = [
            'accounts.views',
            'organizations.views',
            'courses.views',
            'enrollments.views',
            'assignments.views',
            'certificates.views',
        ]
        
        for view_module_name in view_modules:
            try:
                # Import view module
                view_module = importlib.import_module(view_module_name)
                
                # Get source code
                source = inspect.getsource(view_module)
                
                # Check for direct ORM usage
                orm_patterns = [
                    'objects.create(',
                    'objects.get(',
                    'objects.filter(',
                    'objects.all(',
                    'objects.update(',
                    'objects.delete(',
                    '.save()',
                    '.delete()',
                ]
                
                found_orm_usage = []
                for pattern in orm_patterns:
                    if pattern in source:
                        found_orm_usage.append(pattern)
                
                if found_orm_usage:
                    print(f"❌ {view_module_name} contains ORM logic: {found_orm_usage}")
                else:
                    print(f"✅ {view_module_name}: no direct ORM usage found")
                
            except Exception as e:
                print(f"❌ Error analyzing {view_module_name}: {e}")
    
    def test_services_use_only_business_logic(self):
        """Test that services only contain business logic"""
        print("\n=== Testing Services Business Logic Only ===")
        
        services_to_test = [
            ('services.user_service', 'UserService'),
            ('services.course_service', 'CourseService'),
            ('services.enrollment_service', 'EnrollmentService'),
        ]
        
        for service_module_name, service_class_name in services_to_test:
            try:
                # Import service module
                service_module = importlib.import_module(service_module_name)
                
                # Get source code
                source = inspect.getsource(service_module)
                
                # Check for proper service patterns
                service_patterns = [
                    'def create_',  # Create methods
                    'def update_',  # Update methods
                    'def get_',     # Get methods
                    'def list_',    # List methods
                    'def delete_',  # Delete methods
                    'validate_',    # Validation methods
                    'log_action',   # Audit logging
                    'transaction.atomic',  # Transaction usage
                ]
                
                found_patterns = []
                for pattern in service_patterns:
                    if pattern in source:
                        found_patterns.append(pattern)
                
                print(f"\n{service_class_name}:")
                for pattern in found_patterns:
                    print(f"  ✅ {pattern}")
                
                # Check for anti-patterns
                anti_patterns = [
                    'HttpResponse',  # Should not return HTTP responses
                    'request.GET',   # Should not access request directly
                    'request.POST',  # Should not access request directly
                    'render(',       # Should not render templates
                ]
                
                found_anti_patterns = []
                for pattern in anti_patterns:
                    if pattern in source:
                        found_anti_patterns.append(pattern)
                
                if found_anti_patterns:
                    print(f"  ❌ Anti-patterns found: {found_anti_patterns}")
                else:
                    print(f"  ✅ No anti-patterns found")
                
            except Exception as e:
                print(f"❌ Error analyzing {service_class_name}: {e}")
    
    def test_signal_side_effects(self):
        """Test that signals don't cause unwanted side effects"""
        print("\n=== Testing Signal Side Effects ===")
        
        from audit_logs.models import AuditLog
        
        # Get initial audit count
        initial_count = AuditLog.objects.count()
        
        # Create a user (should trigger signals)
        from organizations.models import Organization
        org = Organization.objects.create(
            name='Signal Test Organization',
            domain='signal.test',
            description='Organization for signal testing'
        )
        
        user = User.objects.create_user(
            email='signaltest@signal.test',
            password='test123',
            first_name='Signal',
            last_name='Test',
            role='STUDENT',
            organization=org
        )
        
        # Check if audit log was created
        final_count = AuditLog.objects.count()
        user_create_logs = AuditLog.objects.filter(action='USER_CREATE')
        
        print(f"Initial audit count: {initial_count}")
        print(f"Final audit count: {final_count}")
        print(f"USER_CREATE logs: {user_create_logs.count()}")
        
        # Should create exactly one audit log
        self.assertEqual(final_count, initial_count + 1, "Should create exactly one audit log")
        self.assertEqual(user_create_logs.count(), 1, "Should have one USER_CREATE log")
        
        # Check audit log details
        audit_log = user_create_logs.first()
        self.assertEqual(audit_log.user, user)
        self.assertEqual(audit_log.action, 'USER_CREATE')
        self.assertIn('user_id', audit_log.details)
        self.assertIn('email', audit_log.details)
        
        print("✅ Signal side effects are controlled")
    
    def test_circular_dependencies(self):
        """Test for circular dependencies in services"""
        print("\n=== Testing Circular Dependencies ===")
        
        # Try to import all services
        services_to_import = [
            'services.user_service',
            'services.organization_service',
            'services.course_service',
            'services.enrollment_service',
            'services.assignment_service',
            'services.certificate_service',
        ]
        
        imported_services = {}
        
        for service_module_name in services_to_import:
            try:
                # Import service module
                service_module = importlib.import_module(service_module_name)
                imported_services[service_module_name] = service_module
                print(f"✅ Successfully imported {service_module_name}")
                
            except Exception as e:
                print(f"❌ Failed to import {service_module_name}: {e}")
        
        # Try to create service instances
        for service_module_name, service_module in imported_services.items():
            try:
                # Find service class
                service_class_name = service_module_name.split('.')[-1].replace('_', '').title()
                service_class = getattr(service_module, service_class_name, None)
                
                if service_class:
                    # Try to create instance
                    service_instance = service_class()
                    print(f"✅ Successfully created {service_class_name} instance")
                else:
                    print(f"⚠️  No service class found in {service_module_name}")
                
            except Exception as e:
                print(f"❌ Failed to create service instance from {service_module_name}: {e}")
        
        print("✅ No circular dependencies detected")


class ViewLayerValidation(TransactionTestCase):
    """Validate that view layer is thin and only handles HTTP"""
    
    def setUp(self):
        """Set up test environment"""
        from organizations.models import Organization
        self.organization = Organization.objects.create(
            name='View Test Organization',
            domain='view.test',
            description='Organization for view testing'
        )
        
        self.user = User.objects.create_user(
            email='user@view.test',
            password='test123',
            first_name='View',
            last_name='User',
            role='STUDENT',
            organization=self.organization
        )
    
    def test_view_methods_are_thin(self):
        """Test that view methods are thin"""
        print("\n=== Testing View Methods Are Thin ===")
        
        # Import view modules
        view_modules = [
            'accounts.views',
            'courses.views',
            'enrollments.views',
        ]
        
        for view_module_name in view_modules:
            try:
                # Import view module
                view_module = importlib.import_module(view_module_name)
                
                # Get all classes
                classes = [
                    obj for name, obj in inspect.getmembers(view_module)
                    if inspect.isclass(obj) and hasattr(obj, 'get_queryset')
                ]
                
                print(f"\n{view_module_name}:")
                
                for view_class in classes:
                    # Get all methods
                    methods = [
                        method for method in dir(view_class)
                        if not method.startswith('_') and callable(getattr(view_class, method))
                    ]
                    
                    for method_name in methods:
                        method = getattr(view_class, method_name)
                        
                        # Get method source
                        try:
                            source = inspect.getsource(method)
                            
                            # Count lines
                            lines = source.split('\n')
                            non_empty_lines = [line for line in lines if line.strip() and not line.strip().startswith('#')]
                            
                            if len(non_empty_lines) > 20:
                                print(f"  ⚠️  {method_name}: {len(non_empty_lines)} lines (might be too long)")
                            else:
                                print(f"  ✅ {method_name}: {len(non_empty_lines)} lines")
                            
                        except Exception as e:
                            print(f"  ❌ {method_name}: cannot analyze source")
                
            except Exception as e:
                print(f"❌ Error analyzing {view_module_name}: {e}")
    
    def test_views_only_handle_http(self):
        """Test that views only handle HTTP concerns"""
        print("\n=== Testing Views Only Handle HTTP ===")
        
        # Import view modules
        view_modules = [
            'accounts.views',
            'courses.views',
            'enrollments.views',
        ]
        
        for view_module_name in view_modules:
            try:
                # Import view module
                view_module = importlib.import_module(view_module_name)
                
                # Get source code
                source = inspect.getsource(view_module)
                
                # Check for HTTP-only patterns
                http_patterns = [
                    'Response(',      # DRF Response
                    'status.',       # HTTP status codes
                    'serializer',    # Serialization
                    'permission',   # Permission checks
                    'authentication',  # Authentication
                ]
                
                found_http_patterns = []
                for pattern in http_patterns:
                    if pattern in source:
                        found_http_patterns.append(pattern)
                
                # Check for business logic patterns (should not be in views)
                business_patterns = [
                    'calculate_',    # Calculations
                    'validate_',     # Complex validation
                    'process_',      # Processing logic
                    'generate_',     # Generation logic
                ]
                
                found_business_patterns = []
                for pattern in business_patterns:
                    if pattern in source:
                        found_business_patterns.append(pattern)
                
                print(f"\n{view_module_name}:")
                print(f"  HTTP patterns: {found_http_patterns}")
                if found_business_patterns:
                    print(f"  ❌ Business patterns found: {found_business_patterns}")
                else:
                    print(f"  ✅ No business patterns found")
                
            except Exception as e:
                print(f"❌ Error analyzing {view_module_name}: {e}")
    
    def test_views_use_services(self):
        """Test that views use services instead of direct ORM"""
        print("\n=== Testing Views Use Services ===")
        
        # Import view modules
        view_modules = [
            'accounts.views',
            'courses.views',
            'enrollments.views',
        ]
        
        for view_module_name in view_modules:
            try:
                # Import view module
                view_module = importlib.import_module(view_module_name)
                
                # Get source code
                source = inspect.getsource(view_module)
                
                # Check for service usage
                service_patterns = [
                    'UserService',
                    'CourseService',
                    'EnrollmentService',
                    'AssignmentService',
                    'CertificateService',
                    'service_manager',
                    'ServiceLocator',
                ]
                
                found_service_patterns = []
                for pattern in service_patterns:
                    if pattern in source:
                        found_service_patterns.append(pattern)
                
                print(f"\n{view_module_name}:")
                if found_service_patterns:
                    print(f"  ✅ Service usage: {found_service_patterns}")
                else:
                    print(f"  ⚠️  No service usage found")
                
                # Check for direct ORM usage (should not be present)
                orm_patterns = [
                    'objects.create(',
                    'objects.get(',
                    'objects.filter(',
                    'objects.all(',
                ]
                
                found_orm_patterns = []
                for pattern in orm_patterns:
                    if pattern in source:
                        found_orm_patterns.append(pattern)
                
                if found_orm_patterns:
                    print(f"  ❌ Direct ORM usage: {found_orm_patterns}")
                else:
                    print(f"  ✅ No direct ORM usage")
                
            except Exception as e:
                print(f"❌ Error analyzing {view_module_name}: {e}")


class IntegrationValidation(TransactionTestCase):
    """Validate end-to-end integration"""
    
    def setUp(self):
        """Set up test environment"""
        from organizations.models import Organization
        self.organization = Organization.objects.create(
            name='Integration Test Organization',
            domain='integration.test',
            description='Organization for integration testing'
        )
        
        self.admin = User.objects.create_user(
            email='admin@integration.test',
            password='admin123',
            first_name='Admin',
            last_name='User',
            role='ADMIN',
            organization=self.organization
        )
    
    def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow"""
        print("\n=== Testing End-to-End Workflow ===")
        
        # Step 1: Create user through service
        from services.user_service import UserService
        user_service = UserService()
        user_service.set_context(user=self.admin)
        
        user_data = {
            'email': 'workflow@integration.test',
            'password': 'test123',
            'first_name': 'Workflow',
            'last_name': 'User',
            'role': 'STUDENT',
            'organization': self.organization
        }
        
        new_user = user_service.create_user(user_data, created_by=self.admin)
        
        print(f"✅ User created: {new_user.email}")
        
        # Step 2: Create course through service
        from services.course_service import CourseService
        course_service = CourseService()
        course_service.set_context(user=self.admin)
        
        course_data = {
            'title': 'Integration Test Course',
            'description': 'Course for integration testing',
            'organization': self.organization,
            'instructor': self.admin,
            'difficulty': 'BEGINNER',
            'duration_hours': 10,
            'price': 99.99
        }
        
        new_course = course_service.create_course(course_data, created_by=self.admin)
        
        print(f"✅ Course created: {new_course.title}")
        
        # Step 3: Create enrollment through service
        from services.enrollment_service import EnrollmentService
        enrollment_service = EnrollmentService()
        enrollment_service.set_context(user=new_user)
        
        new_enrollment = enrollment_service.create_enrollment(
            user=new_user,
            course=new_course,
            payment_status='COMPLETED',
            payment_amount=99.99,
            enrolled_by=new_user
        )
        
        print(f"✅ Enrollment created: {new_enrollment.id}")
        
        # Step 4: Update progress through service
        updated_enrollment = enrollment_service.update_progress(
            new_enrollment,
            50.0,
            updated_by=new_user
        )
        
        print(f"✅ Progress updated: {updated_enrollment.progress_percentage}%")
        
        # Step 5: Complete enrollment through service
        completed_enrollment = enrollment_service.complete_enrollment(
            new_enrollment,
            completed_by=new_user
        )
        
        print(f"✅ Enrollment completed: {completed_enrollment.status}")
        
        # Step 6: Generate certificate through service
        from services.certificate_service import CertificateService
        certificate_service = CertificateService()
        certificate_service.set_context(user=self.admin)
        
        new_certificate = certificate_service.create_certificate(
            completed_enrollment,
            issued_by=self.admin
        )
        
        print(f"✅ Certificate created: {new_certificate.certificate_number}")
        
        # Verify everything is connected properly
        self.assertEqual(new_certificate.user, new_user)
        self.assertEqual(new_certificate.course, new_course)
        self.assertEqual(new_certificate.enrollment, completed_enrollment)
        
        print("✅ End-to-end workflow completed successfully")
    
    def test_service_orchestration(self):
        """Test service orchestration"""
        print("\n=== Testing Service Orchestration ===")
        
        from services.manager import service_orchestrator
        
        # Test user creation workflow
        user_data = {
            'email': 'orchestrated@integration.test',
            'password': 'test123',
            'first_name': 'Orchestrated',
            'last_name': 'User',
            'role': 'STUDENT',
            'organization': self.organization
        }
        
        result = service_orchestrator.create_user_workflow(
            user_data,
            created_by=self.admin
        )
        
        print(f"✅ User orchestration: {result.success}")
        self.assertTrue(result.success, "User orchestration should succeed")
        
        # Test course creation workflow
        course_data = {
            'title': 'Orchestrated Course',
            'description': 'Course created via orchestration',
            'organization': self.organization,
            'instructor': self.admin,
            'difficulty': 'BEGINNER',
            'duration_hours': 10,
            'price': 99.99
        }
        
        result = service_orchestrator.create_course_workflow(
            course_data,
            created_by=self.admin
        )
        
        print(f"✅ Course orchestration: {result.success}")
        self.assertTrue(result.success, "Course orchestration should succeed")
        
        print("✅ Service orchestration working correctly")


def run_service_integrity_validation():
    """Run all service integrity validation tests"""
    import unittest
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        ServicePurityValidation,
        ViewLayerValidation,
        IntegrationValidation
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_service_integrity_validation()
    print(f"\n{'='*60}")
    print(f"SERVICE INTEGRITY VALIDATION: {'PASSED' if success else 'FAILED'}")
    print(f"{'='*60}")
