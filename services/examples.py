"""
Services Layer Usage Examples

This module provides comprehensive examples of how to use
the services layer in the AgoraProf LMS.
"""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from typing import Dict, Any, List, Optional

from .manager import service_manager, service_orchestrator
from .registry import ServiceLocator, ServiceFactory
from .config import get_service_settings
from .base import ServiceResponse

User = get_user_model()


class UserServiceExamples:
    """Examples for UserService usage"""
    
    @staticmethod
    def create_new_user():
        """Example: Create a new user with validation"""
        # Get service instance
        user_service = ServiceLocator.get_user_service()
        
        # Prepare user data
        user_data = {
            'email': 'newuser@example.com',
            'password': 'SecurePassword123!',
            'first_name': 'John',
            'last_name': 'Doe',
            'role': 'STUDENT',
            'organization_id': 'org-uuid-here',
            'phone': '+1234567890',
            'address': '123 Main St, City, State',
            'profile': {
                'employee_id': 'EMP001',
                'department': 'Engineering',
                'position': 'Software Developer',
                'skills': ['Python', 'Django', 'JavaScript'],
                'certifications': ['AWS Certified Developer']
            }
        }
        
        try:
            # Create user
            user = user_service.create_user(user_data, created_by=None)
            
            print(f"User created successfully: {user.email}")
            return user
            
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
    
    @staticmethod
    def update_user_profile():
        """Example: Update user profile with validation"""
        user_service = ServiceLocator.get_user_service()
        
        # Get existing user
        try:
            user = User.objects.get(email='existing@example.com')
        except User.DoesNotExist:
            print("User not found")
            return None
        
        # Prepare update data
        update_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'phone': '+9876543210',
            'bio': 'Experienced software developer with expertise in web applications.',
            'profile': {
                'position': 'Senior Software Developer',
                'skills': ['Python', 'Django', 'React', 'AWS'],
                'certifications': ['AWS Certified Developer', 'Google Cloud Professional']
            }
        }
        
        try:
            # Update user
            updated_user = user_service.update_user(user, update_data, updated_by=user)
            
            print(f"User updated successfully: {updated_user.email}")
            return updated_user
            
        except Exception as e:
            print(f"Error updating user: {e}")
            return None
    
    @staticmethod
    def change_user_role():
        """Example: Change user role with audit logging"""
        user_service = ServiceLocator.get_user_service()
        
        # Get user
        user = User.objects.get(email='user@example.com')
        admin = User.objects.get(email='admin@example.com')
        
        try:
            # Change role
            updated_user = user_service.change_user_role(
                user, 
                'MANAGER', 
                changed_by=admin
            )
            
            print(f"User role changed to: {updated_user.role}")
            return updated_user
            
        except Exception as e:
            print(f"Error changing user role: {e}")
            return None
    
    @staticmethod
    def get_user_analytics():
        """Example: Get user analytics and statistics"""
        user_service = ServiceLocator.get_user_service()
        
        # Get organization statistics
        org_stats = user_service.get_user_statistics(organization_id='org-uuid')
        
        # Search users
        search_results = user_service.search_users(
            query='john',
            organization_id='org-uuid',
            role='STUDENT'
        )
        
        print(f"Total users: {org_stats['total_users']}")
        print(f"Active users: {org_stats['active_users']}")
        print(f"Search results: {search_results.count()} users")
        
        return {
            'statistics': org_stats,
            'search_results': search_results
        }


class CourseServiceExamples:
    """Examples for CourseService usage"""
    
    @staticmethod
    def create_comprehensive_course():
        """Example: Create a comprehensive course with modules and lessons"""
        course_service = ServiceLocator.get_course_service()
        
        # Prepare course data
        course_data = {
            'title': 'Advanced Python Development',
            'description': 'Master advanced Python concepts and best practices',
            'short_description': 'Advanced Python course for experienced developers',
            'organization_id': 'org-uuid',
            'instructor_id': 'instructor-uuid',
            'category_id': 'programming-uuid',
            'difficulty': 'INTERMEDIATE',
            'duration_hours': 40,
            'price': 299.99,
            'max_students': 50,
            'prerequisites': ['Basic Python knowledge', 'Object-oriented programming'],
            'objectives': [
                'Master advanced Python concepts',
                'Build scalable applications',
                'Implement best practices'
            ],
            'outcomes': [
                'Create production-ready Python applications',
                'Understand design patterns',
                'Implement testing strategies'
            ],
            'tags': ['python', 'programming', 'advanced'],
            'language': 'en',
            'certificate_enabled': True,
            'is_featured': True
        }
        
        try:
            # Create course
            course = course_service.create_course(course_data, created_by=None)
            
            # Create modules
            modules_data = [
                {
                    'title': 'Advanced Python Fundamentals',
                    'description': 'Deep dive into Python fundamentals',
                    'order': 1
                },
                {
                    'title': 'Design Patterns',
                    'description': 'Common design patterns in Python',
                    'order': 2
                },
                {
                    'title': 'Testing and Debugging',
                    'description': 'Comprehensive testing strategies',
                    'order': 3
                }
            ]
            
            for module_data in modules_data:
                module = course_service.create_module(course, module_data, created_by=None)
                
                # Create lessons for each module
                lessons_data = [
                    {
                        'title': f'{module.title} - Introduction',
                        'description': 'Introduction to the module',
                        'lesson_type': 'TEXT',
                        'content': 'Welcome to this module...',
                        'order': 1,
                        'duration_minutes': 15
                    },
                    {
                        'title': f'{module.title} - Core Concepts',
                        'description': 'Main concepts of the module',
                        'lesson_type': 'VIDEO',
                        'content': 'Video content...',
                        'order': 2,
                        'duration_minutes': 45
                    },
                    {
                        'title': f'{module.title} - Practice',
                        'description': 'Hands-on practice',
                        'lesson_type': 'ASSIGNMENT',
                        'content': 'Practice exercises...',
                        'order': 3,
                        'duration_minutes': 60
                    }
                ]
                
                for lesson_data in lessons_data:
                    course_service.create_lesson(module, lesson_data, created_by=None)
            
            print(f"Course created successfully: {course.title}")
            return course
            
        except Exception as e:
            print(f"Error creating course: {e}")
            return None
    
    @staticmethod
    def publish_and_manage_course():
        """Example: Publish course and manage lifecycle"""
        course_service = ServiceLocator.get_course_service()
        
        # Get course
        course = course_service.get_course_by_id('course-uuid')
        
        try:
            # Publish course
            published_course = course_service.publish_course(course, published_by=None)
            print(f"Course published: {published_course.title}")
            
            # Get course statistics
            stats = course_service.get_course_statistics(published_course)
            print(f"Course stats: {stats}")
            
            # Archive course (when needed)
            # archived_course = course_service.archive_course(published_course, archived_by=None)
            
            return published_course
            
        except Exception as e:
            print(f"Error managing course: {e}")
            return None
    
    @staticmethod
    def get_course_analytics():
        """Example: Get comprehensive course analytics"""
        course_service = ServiceLocator.get_course_service()
        
        # Get course statistics
        course = course_service.get_course_by_id('course-uuid')
        course_stats = course_service.get_course_statistics(course)
        
        # Get lesson statistics
        lesson_stats = []
        for module in course.modules.all():
            for lesson in module.lessons.all():
                stats = course_service.get_lesson_statistics(lesson)
                lesson_stats.append({
                    'lesson_title': lesson.title,
                    'stats': stats
                })
        
        print(f"Course completion rate: {course_stats['completion_rate']}%")
        print(f"Average progress: {course_stats['average_progress']}%")
        
        return {
            'course_stats': course_stats,
            'lesson_stats': lesson_stats
        }


class EnrollmentServiceExamples:
    """Examples for EnrollmentService usage"""
    
    @staticmethod
    def complete_enrollment_workflow():
        """Example: Complete enrollment workflow with progress tracking"""
        enrollment_service = ServiceLocator.get_enrollment_service()
        
        try:
            # Create enrollment
            user = User.objects.get(email='student@example.com')
            course = enrollment_service.get_course_by_id('course-uuid')
            
            enrollment = enrollment_service.create_enrollment(
                user=user,
                course=course,
                payment_status='COMPLETED',
                payment_amount=299.99,
                enrolled_by=user
            )
            
            print(f"Enrollment created: {enrollment.id}")
            
            # Simulate lesson progress
            for module in course.modules.all():
                for lesson in module.lessons.all():
                    # Get lesson progress
                    lesson_progress = enrollment.lesson_progress.get(lesson=lesson)
                    
                    # Update progress (simulate 80% completion)
                    enrollment_service.update_lesson_progress(
                        lesson_progress,
                        progress_percentage=80.0,
                        time_spent=timezone.timedelta(minutes=45),
                        updated_by=user
                    )
            
            # Update overall progress
            enrollment_service.update_progress(enrollment, 75.0, updated_by=user)
            
            print(f"Enrollment progress: {enrollment.progress_percentage}%")
            
            # Complete enrollment
            completed_enrollment = enrollment_service.complete_enrollment(enrollment, completed_by=user)
            
            print(f"Enrollment completed: {completed_enrollment.status}")
            return completed_enrollment
            
        except Exception as e:
            print(f"Error in enrollment workflow: {e}")
            return None
    
    @staticmethod
    def get_enrollment_analytics():
        """Example: Get comprehensive enrollment analytics"""
        enrollment_service = ServiceLocator.get_enrollment_service()
        
        # Get user enrollment statistics
        user = User.objects.get(email='student@example.com')
        user_stats = enrollment_service.get_user_enrollment_statistics(user)
        
        # Get course enrollment statistics
        course = enrollment_service.get_course_by_id('course-uuid')
        course_stats = enrollment_service.get_course_enrollment_statistics(course)
        
        # Get organization enrollment statistics
        org_stats = enrollment_service.get_organization_enrollment_statistics('org-uuid')
        
        print(f"User enrollments: {user_stats['total_enrollments']}")
        print(f"Course enrollments: {course_stats['total_enrollments']}")
        print(f"Organization enrollments: {org_stats['total_enrollments']}")
        
        return {
            'user_stats': user_stats,
            'course_stats': course_stats,
            'org_stats': org_stats
        }


class ServiceManagerExamples:
    """Examples for ServiceManager usage"""
    
    @staticmethod
    def execute_with_monitoring():
        """Example: Execute service method with monitoring"""
        # Execute user service method with monitoring
        result = service_manager.execute_service_method(
            service_name='user',
            method_name='get_user_statistics',
            user=None,  # System user
            kwargs={'organization_id': 'org-uuid'},
            use_transaction=True,
            use_cache=True
        )
        
        if result.success:
            print(f"Statistics: {result.data}")
        else:
            print(f"Error: {result.message}")
        
        return result
    
    @staticmethod
    def batch_operations():
        """Example: Execute batch operations"""
        operations = [
            {
                'service': 'user',
                'method': 'get_user_statistics',
                'kwargs': {'organization_id': 'org-uuid'}
            },
            {
                'service': 'course',
                'method': 'get_organization_courses',
                'kwargs': {'organization_id': 'org-uuid', 'status': 'PUBLISHED'}
            },
            {
                'service': 'enrollment',
                'method': 'get_organization_enrollment_statistics',
                'kwargs': {'organization_id': 'org-uuid'}
            }
        ]
        
        # Execute batch operations
        results = service_manager.batch_execute(operations, fail_fast=False)
        
        for i, result in enumerate(results):
            if result.success:
                print(f"Operation {i+1}: SUCCESS")
            else:
                print(f"Operation {i+1}: FAILED - {result.message}")
        
        return results
    
    @staticmethod
    def performance_monitoring():
        """Example: Performance monitoring"""
        import time
        import uuid
        
        # Start timing
        operation_id = str(uuid.uuid4())
        service_manager.service_monitor.start_timing(operation_id)
        
        # Execute operation
        result = service_manager.execute_service_method(
            service_name='user',
            method_name='search_users',
            user=None,
            kwargs={'query': 'john', 'organization_id': 'org-uuid'}
        )
        
        # End timing
        duration = service_manager.service_monitor.end_timing(
            operation_id, 
            'user', 
            'search_users'
        )
        
        # Get performance summary
        summary = service_manager.service_monitor.get_performance_summary('user', 'search_users')
        
        print(f"Operation duration: {duration:.3f}s")
        print(f"Average duration: {summary['avg_duration']:.3f}s")
        print(f"Max duration: {summary['max_duration']:.3f}s")
        
        return summary


class ServiceOrchestratorExamples:
    """Examples for ServiceOrchestrator usage"""
    
    @staticmethod
    def complete_onboarding_workflow():
        """Example: Complete user onboarding workflow"""
        # User data for onboarding
        user_data = {
            'email': 'newuser@example.com',
            'password': 'SecurePassword123!',
            'first_name': 'New',
            'last_name': 'User',
            'role': 'STUDENT',
            'organization_id': 'org-uuid',
            'profile': {
                'phone': '+1234567890',
                'address': '123 Main St',
                'department': 'Engineering',
                'position': 'Software Developer'
            }
        }
        
        # Execute onboarding workflow
        result = service_orchestrator.create_user_workflow(
            user_data,
            created_by=None
        )
        
        if result.success:
            print(f"User onboarded successfully: {result.data['user_id']}")
        else:
            print(f"Onboarding failed: {result.message}")
        
        return result
    
    @staticmethod
    def course_creation_workflow():
        """Example: Course creation workflow with modules"""
        course_data = {
            'title': 'Complete Web Development',
            'description': 'Learn web development from scratch',
            'organization_id': 'org-uuid',
            'instructor_id': 'instructor-uuid',
            'difficulty': 'BEGINNER',
            'duration_hours': 60,
            'price': 499.99,
            'modules': [
                {
                    'title': 'HTML & CSS Fundamentals',
                    'description': 'Learn the basics of HTML and CSS',
                    'order': 1
                },
                {
                    'title': 'JavaScript Essentials',
                    'description': 'Master JavaScript programming',
                    'order': 2
                },
                {
                    'title': 'React Development',
                    'description': 'Build modern web apps with React',
                    'order': 3
                }
            ]
        }
        
        result = service_orchestrator.create_course_workflow(
            course_data,
            created_by=None
        )
        
        if result.success:
            print(f"Course created: {result.data['course_id']}")
        else:
            print(f"Course creation failed: {result.message}")
        
        return result


class ConfigurationExamples:
    """Examples for service configuration usage"""
    
    @staticmethod
    def service_configuration():
        """Example: Service configuration usage"""
        # Get service settings
        user_settings = get_service_settings('user')
        
        # Check if feature is enabled
        avatar_upload_enabled = user_settings.get_feature_setting(
            'user_management.avatar_upload', 
            default=False
        )
        
        # Get cache timeout
        cache_timeout = user_settings.get_cache_timeout('user_profile')
        
        # Get rate limit
        rate_limit = user_settings.get_rate_limit('user_creation')
        
        print(f"Avatar upload enabled: {avatar_upload_enabled}")
        print(f"Cache timeout: {cache_timeout}s")
        print(f"Rate limit: {rate_limit} per hour")
        
        return {
            'avatar_upload_enabled': avatar_upload_enabled,
            'cache_timeout': cache_timeout,
            'rate_limit': rate_limit
        }
    
    @staticmethod
    def environment_specific_config():
        """Example: Environment-specific configuration"""
        from .config import config_manager
        
        # Get configuration
        cache_config = config_manager.get_config('cache')
        monitoring_config = config_manager.get_config('monitoring')
        security_config = config_manager.get_config('security')
        
        # Check if caching is enabled
        caching_enabled = cache_config['enabled']
        
        # Get log level
        log_level = monitoring_config['log_level']
        
        # Check if encryption is enabled
        encryption_enabled = security_config['encryption_enabled']
        
        print(f"Caching enabled: {caching_enabled}")
        print(f"Log level: {log_level}")
        print(f"Encryption enabled: {encryption_enabled}")
        
        return {
            'caching_enabled': caching_enabled,
            'log_level': log_level,
            'encryption_enabled': encryption_enabled
        }


class ErrorHandlingExamples:
    """Examples for error handling in services"""
    
    @staticmethod
    def handle_service_errors():
        """Example: Handle service errors gracefully"""
        try:
            user_service = ServiceLocator.get_user_service()
            
            # Try to create user with invalid data
            user_data = {
                'email': 'invalid-email',  # Invalid email
                'password': '123',  # Too short
                'first_name': '',  # Required field missing
                'role': 'INVALID_ROLE'  # Invalid role
            }
            
            user = user_service.create_user(user_data, created_by=None)
            
        except Exception as e:
            print(f"Service error: {e}")
            
            # Handle specific error types
            if "already exists" in str(e):
                print("User already exists")
            elif "required" in str(e).lower():
                print("Required fields missing")
            elif "invalid" in str(e).lower():
                print("Invalid data provided")
            else:
                print("Unknown error occurred")
    
    @staticmethod
    def service_response_handling():
        """Example: Handle service responses"""
        result = service_manager.execute_service_method(
            service_name='user',
            method_name='get_user_statistics',
            user=None,
            kwargs={'organization_id': 'invalid-uuid'}
        )
        
        if result.success:
            print(f"Success: {result.data}")
        else:
            print(f"Error: {result.message}")
            
            # Handle specific errors
            for error in result.errors:
                if "not found" in error.lower():
                    print("Resource not found")
                elif "permission" in error.lower():
                    print("Permission denied")
                elif "validation" in error.lower():
                    print("Validation error")
                else:
                    print(f"Other error: {error}")


def run_all_examples():
    """Run all examples"""
    print("=== Service Layer Usage Examples ===\n")
    
    print("1. UserService Examples")
    UserServiceExamples.create_new_user()
    UserServiceExamples.get_user_analytics()
    
    print("\n2. CourseService Examples")
    CourseServiceExamples.create_comprehensive_course()
    CourseServiceExamples.get_course_analytics()
    
    print("\n3. EnrollmentService Examples")
    EnrollmentServiceExamples.complete_enrollment_workflow()
    EnrollmentServiceExamples.get_enrollment_analytics()
    
    print("\n4. ServiceManager Examples")
    ServiceManagerExamples.execute_with_monitoring()
    ServiceManagerExamples.batch_operations()
    
    print("\n5. ServiceOrchestrator Examples")
    ServiceOrchestratorExamples.complete_onboarding_workflow()
    
    print("\n6. Configuration Examples")
    ConfigurationExamples.service_configuration()
    
    print("\n7. Error Handling Examples")
    ErrorHandlingExamples.handle_service_errors()
    ErrorHandlingExamples.service_response_handling()
    
    print("\n=== All Examples Completed ===")


if __name__ == '__main__':
    run_all_examples()
