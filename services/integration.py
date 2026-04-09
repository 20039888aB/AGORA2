"""
Services Integration - Connect Services to Django Apps

This module connects the centralized services to the Django apps
to ensure all business logic goes through the service layer.
"""

from django.apps import apps


def get_service(service_name):
    """
    Get service instance by name
    """
    try:
        if service_name == 'user':
            from .user_service import UserService
            return UserService
        elif service_name == 'organization':
            from .organization_service import OrganizationService
            return OrganizationService
        elif service_name == 'course':
            from .course_service import CourseService
            return CourseService
        elif service_name == 'enrollment':
            from .enrollment_service import EnrollmentService
            return EnrollmentService
        elif service_name == 'assignment':
            from .assignment_service import AssignmentService
            return AssignmentService
        elif service_name == 'certificate':
            from .certificate_service import CertificateService
            return CertificateService
        else:
            raise ValueError(f"Unknown service: {service_name}")
    except ImportError as e:
        raise ValueError(f"Service {service_name} not found: {e}")


# Monkey patch to redirect model methods to services
def patch_model_methods():
    """
    Patch model methods to use services instead of direct model access
    """
    # This would be implemented to ensure all model methods go through services
    # For now, this is a placeholder for the concept
    pass


# Initialize services when Django starts
def initialize_services():
    """
    Initialize services when Django starts
    """
    # Import all services to ensure they're loaded
    from . import user_service
    from . import organization_service
    from . import course_service
    from . import enrollment_service
    from . import assignment_service
    from . import certificate_service
    from . import permissions
    from . import signals
    
    # Patch model methods
    patch_model_methods()
