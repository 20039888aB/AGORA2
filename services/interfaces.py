"""
Service Interfaces - Abstract Service Contracts

This module defines interfaces and contracts for all services
to ensure consistency and proper implementation patterns.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, TypeVar, Generic
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from .base import ServiceResponse

User = get_user_model()

# Generic type for model instances
T = TypeVar('T')


class IService(ABC):
    """Base service interface"""
    
    @abstractmethod
    def create(self, data: Dict[str, Any], **kwargs) -> ServiceResponse:
        """Create a new resource"""
        pass
    
    @abstractmethod
    def get_by_id(self, resource_id: str, **kwargs) -> ServiceResponse:
        """Get resource by ID"""
        pass
    
    @abstractmethod
    def update(self, resource_id: str, data: Dict[str, Any], **kwargs) -> ServiceResponse:
        """Update existing resource"""
        pass
    
    @abstractmethod
    def delete(self, resource_id: str, **kwargs) -> ServiceResponse:
        """Delete resource"""
        pass
    
    @abstractmethod
    def list(self, filters: Dict[str, Any] = None, **kwargs) -> ServiceResponse:
        """List resources with optional filters"""
        pass


class IUserService(IService):
    """User service interface"""
    
    @abstractmethod
    def create_user(self, data: Dict[str, Any], created_by: User = None) -> User:
        """Create new user"""
        pass
    
    @abstractmethod
    def update_user(self, user: User, data: Dict[str, Any], updated_by: User = None) -> User:
        """Update user"""
        pass
    
    @abstractmethod
    def soft_delete_user(self, user: User, deleted_by: User = None) -> User:
        """Soft delete user"""
        pass
    
    @abstractmethod
    def restore_user(self, user: User, restored_by: User = None) -> User:
        """Restore soft deleted user"""
        pass
    
    @abstractmethod
    def change_user_role(self, user: User, new_role: str, changed_by: User = None) -> User:
        """Change user role"""
        pass
    
    @abstractmethod
    def get_user_statistics(self, organization: Any = None) -> Dict[str, Any]:
        """Get user statistics"""
        pass
    
    @abstractmethod
    def search_users(self, query: str, organization: Any = None, role: str = None) -> QuerySet[User]:
        """Search users"""
        pass
    
    @abstractmethod
    def validate_user_permissions(self, user: User, resource_type: str, action_type: str, scope_object: Any = None) -> bool:
        """Validate user permissions"""
        pass


class IOrganizationService(IService):
    """Organization service interface"""
    
    @abstractmethod
    def create_organization(self, data: Dict[str, Any], created_by: User = None) -> Any:
        """Create new organization"""
        pass
    
    @abstractmethod
    def update_organization(self, organization: Any, data: Dict[str, Any], updated_by: User = None) -> Any:
        """Update organization"""
        pass
    
    @abstractmethod
    def create_department(self, organization: Any, data: Dict[str, Any], created_by: User = None) -> Any:
        """Create department"""
        pass
    
    @abstractmethod
    def create_team(self, organization: Any, data: Dict[str, Any], created_by: User = None) -> Any:
        """Create team"""
        pass
    
    @abstractmethod
    def add_user_to_department(self, user: User, department: Any, role: str = 'MEMBER', added_by: User = None) -> Any:
        """Add user to department"""
        pass
    
    @abstractmethod
    def add_user_to_team(self, user: User, team: Any, role: str = 'MEMBER', added_by: User = None) -> Any:
        """Add user to team"""
        pass
    
    @abstractmethod
    def get_organization_statistics(self, organization: Any) -> Dict[str, Any]:
        """Get organization statistics"""
        pass
    
    @abstractmethod
    def get_department_hierarchy(self, organization: Any) -> List[Dict[str, Any]]:
        """Get department hierarchy"""
        pass
    
    @abstractmethod
    def validate_organization_access(self, user: User, organization: Any) -> bool:
        """Validate organization access"""
        pass


class ICourseService(IService):
    """Course service interface"""
    
    @abstractmethod
    def create_course(self, data: Dict[str, Any], created_by: User = None) -> Any:
        """Create new course"""
        pass
    
    @abstractmethod
    def update_course(self, course: Any, data: Dict[str, Any], updated_by: User = None) -> Any:
        """Update course"""
        pass
    
    @abstractmethod
    def publish_course(self, course: Any, published_by: User = None) -> Any:
        """Publish course"""
        pass
    
    @abstractmethod
    def archive_course(self, course: Any, archived_by: User = None) -> Any:
        """Archive course"""
        pass
    
    @abstractmethod
    def duplicate_course(self, course: Any, creator: User = None, include_modules: bool = False, include_lessons: bool = False) -> Any:
        """Duplicate course"""
        pass
    
    @abstractmethod
    def create_module(self, course: Any, data: Dict[str, Any], created_by: User = None) -> Any:
        """Create module"""
        pass
    
    @abstractmethod
    def create_lesson(self, module: Any, data: Dict[str, Any], created_by: User = None) -> Any:
        """Create lesson"""
        pass
    
    @abstractmethod
    def reorder_modules(self, course: Any, module_orders: Dict[str, int], reordered_by: User = None) -> None:
        """Reorder modules"""
        pass
    
    @abstractmethod
    def get_course_statistics(self, course: Any) -> Dict[str, Any]:
        """Get course statistics"""
        pass
    
    @abstractmethod
    def get_lesson_statistics(self, lesson: Any) -> Dict[str, Any]:
        """Get lesson statistics"""
        pass
    
    @abstractmethod
    def validate_course_access(self, user: User, course: Any, action: str = 'view') -> bool:
        """Validate course access"""
        pass


class IEnrollmentService(IService):
    """Enrollment service interface"""
    
    @abstractmethod
    def create_enrollment(self, user: User, course: Any, payment_status: str = 'PENDING', payment_amount: float = 0.00, enrolled_by: User = None) -> Any:
        """Create enrollment"""
        pass
    
    @abstractmethod
    def activate_enrollment(self, enrollment: Any, activated_by: User = None) -> Any:
        """Activate enrollment"""
        pass
    
    @abstractmethod
    def complete_enrollment(self, enrollment: Any, completed_by: User = None) -> Any:
        """Complete enrollment"""
        pass
    
    @abstractmethod
    def update_progress(self, enrollment: Any, progress_percentage: float, updated_by: User = None) -> Any:
        """Update enrollment progress"""
        pass
    
    @abstractmethod
    def issue_certificate(self, enrollment: Any, issued_by: User = None) -> Any:
        """Issue certificate"""
        pass
    
    @abstractmethod
    def update_lesson_progress(self, lesson_progress: Any, progress_percentage: float, time_spent: Any = None, updated_by: User = None) -> Any:
        """Update lesson progress"""
        pass
    
    @abstractmethod
    def get_enrollment_statistics(self, enrollment: Any) -> Dict[str, Any]:
        """Get enrollment statistics"""
        pass
    
    @abstractmethod
    def get_user_enrollment_statistics(self, user: User) -> Dict[str, Any]:
        """Get user enrollment statistics"""
        pass
    
    @abstractmethod
    def get_course_enrollment_statistics(self, course: Any) -> Dict[str, Any]:
        """Get course enrollment statistics"""
        pass
    
    @abstractmethod
    def validate_enrollment_access(self, user: User, enrollment: Any, action: str = 'view') -> bool:
        """Validate enrollment access"""
        pass


class IAssignmentService(IService):
    """Assignment service interface"""
    
    @abstractmethod
    def create_assignment(self, data: Dict[str, Any], creator: User = None) -> Any:
        """Create assignment"""
        pass
    
    @abstractmethod
    def publish_assignment(self, assignment: Any, published_by: User = None) -> Any:
        """Publish assignment"""
        pass
    
    @abstractmethod
    def close_assignment(self, assignment: Any, closed_by: User = None) -> Any:
        """Close assignment"""
        pass
    
    @abstractmethod
    def create_question(self, assignment: Any, data: Dict[str, Any], creator: User = None) -> Any:
        """Create assignment question"""
        pass
    
    @abstractmethod
    def create_submission(self, student: User, assignment: Any, attempt_number: int = 1, created_by: User = None) -> Any:
        """Create assignment submission"""
        pass
    
    @abstractmethod
    def submit_assignment(self, submission: Any, submitted_by: User = None) -> Any:
        """Submit assignment"""
        pass
    
    @abstractmethod
    def grade_submission(self, submission: Any, score: float, feedback: str = None, graded_by: User = None) -> Any:
        """Grade assignment submission"""
        pass
    
    @abstractmethod
    def auto_grade_submission(self, submission: Any) -> Any:
        """Auto-grade assignment submission"""
        pass
    
    @abstractmethod
    def upload_file(self, assignment: Any = None, submission: Any = None, file: Any = None, title: str = None, uploaded_by: User = None) -> Any:
        """Upload assignment file"""
        pass
    
    @abstractmethod
    def get_assignment_statistics(self, assignment: Any) -> Dict[str, Any]:
        """Get assignment statistics"""
        pass
    
    @abstractmethod
    def get_question_statistics(self, question: Any) -> Dict[str, Any]:
        """Get question statistics"""
        pass
    
    @abstractmethod
    def validate_assignment_access(self, user: User, assignment: Any, action: str = 'view') -> bool:
        """Validate assignment access"""
        pass


class ICertificateService(IService):
    """Certificate service interface"""
    
    @abstractmethod
    def create_template(self, data: Dict[str, Any], creator: User = None) -> Any:
        """Create certificate template"""
        pass
    
    @abstractmethod
    def set_default_template(self, template: Any, set_by: User = None) -> Any:
        """Set template as default"""
        pass
    
    @abstractmethod
    def create_certificate(self, enrollment: Any, template: Any = None, issued_by: User = None) -> Any:
        """Create certificate"""
        pass
    
    @abstractmethod
    def issue_certificate(self, certificate: Any, issued_by: User = None) -> Any:
        """Issue certificate"""
        pass
    
    @abstractmethod
    def revoke_certificate(self, certificate: Any, revoked_by: User = None, reason: str = '') -> Any:
        """Revoke certificate"""
        pass
    
    @abstractmethod
    def verify_certificate(self, verification_code: str, verified_by: User = None, ip_address: str = None, user_agent: str = '') -> Dict[str, Any]:
        """Verify certificate"""
        pass
    
    @abstractmethod
    def create_batch(self, data: Dict[str, Any], creator: User = None) -> Any:
        """Create certificate batch"""
        pass
    
    @abstractmethod
    def process_batch(self, batch: Any, processed_by: User = None) -> Any:
        """Process certificate batch"""
        pass
    
    @abstractmethod
    def get_certificate_statistics(self, organization: Any = None) -> Dict[str, Any]:
        """Get certificate statistics"""
        pass
    
    @abstractmethod
    def get_template_statistics(self, template: Any) -> Dict[str, Any]:
        """Get template statistics"""
        pass
    
    @abstractmethod
    def validate_certificate_access(self, user: User, certificate: Any, action: str = 'view') -> bool:
        """Validate certificate access"""
        pass


class IValidationService(ABC):
    """Validation service interface"""
    
    @abstractmethod
    def validate_user_data(self, data: Dict[str, Any], context: str = 'create') -> Dict[str, Any]:
        """Validate user data"""
        pass
    
    @abstractmethod
    def validate_course_data(self, data: Dict[str, Any], context: str = 'create') -> Dict[str, Any]:
        """Validate course data"""
        pass
    
    @abstractmethod
    def validate_enrollment_data(self, data: Dict[str, Any], context: str = 'create') -> Dict[str, Any]:
        """Validate enrollment data"""
        pass
    
    @abstractmethod
    def validate_assignment_data(self, data: Dict[str, Any], context: str = 'create') -> Dict[str, Any]:
        """Validate assignment data"""
        pass
    
    @abstractmethod
    def validate_certificate_data(self, data: Dict[str, Any], context: str = 'create') -> Dict[str, Any]:
        """Validate certificate data"""
        pass


class INotificationService(ABC):
    """Notification service interface"""
    
    @abstractmethod
    def send_email_notification(self, subject: str, message: str, recipients: List[str], **kwargs) -> bool:
        """Send email notification"""
        pass
    
    @abstractmethod
    def send_push_notification(self, user: User, title: str, message: str, **kwargs) -> bool:
        """Send push notification"""
        pass
    
    @abstractmethod
    def create_notification(self, user: User, title: str, message: str, notification_type: str = 'INFO', **kwargs) -> Any:
        """Create notification"""
        pass
    
    @abstractmethod
    def send_bulk_notification(self, users: List[User], title: str, message: str, **kwargs) -> bool:
        """Send bulk notification"""
        pass


class ICacheService(ABC):
    """Cache service interface"""
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get cached value"""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, timeout: int = 300) -> None:
        """Set cached value"""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete cached value"""
        pass
    
    @abstractmethod
    def clear_pattern(self, pattern: str) -> None:
        """Clear cache by pattern"""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        pass


class IAuditService(ABC):
    """Audit service interface"""
    
    @abstractmethod
    def log_action(self, user: User, action: str, details: Dict[str, Any], ip_address: str = None) -> Any:
        """Log action"""
        pass
    
    @abstractmethod
    def get_audit_trail(self, user: User = None, action: str = None, start_date: Any = None, end_date: Any = None) -> QuerySet:
        """Get audit trail"""
        pass
    
    @abstractmethod
    def get_action_statistics(self, organization: Any = None, days: int = 30) -> Dict[str, Any]:
        """Get action statistics"""
        pass


class ServiceValidator:
    """
    Service validator to ensure implementations follow contracts
    """
    
    @staticmethod
    def validate_service_implementation(service_class: type, interface_class: type) -> bool:
        """Validate that service class implements interface"""
        try:
            # Get all abstract methods from interface
            interface_methods = set()
            for name, method in interface_class.__dict__.items():
                if getattr(method, '__isabstractmethod__', False):
                    interface_methods.add(name)
            
            # Check if service class implements all interface methods
            service_methods = set(service_class.__dict__.keys())
            
            missing_methods = interface_methods - service_methods
            if missing_methods:
                raise ValueError(f"Service {service_class.__name__} missing methods: {missing_methods}")
            
            return True
            
        except Exception as e:
            raise ValueError(f"Service validation failed: {e}")
    
    @staticmethod
    def validate_all_services() -> Dict[str, bool]:
        """Validate all registered services"""
        from .registry import ServiceRegistry
        
        validation_results = {}
        
        # Define service interfaces mapping
        service_interfaces = {
            'user': IUserService,
            'organization': IOrganizationService,
            'course': ICourseService,
            'enrollment': IEnrollmentService,
            'assignment': IAssignmentService,
            'certificate': ICertificateService,
        }
        
        for service_name, interface_class in service_interfaces.items():
            try:
                service_class = ServiceRegistry.get_service_class(service_name)
                validation_results[service_name] = ServiceValidator.validate_service_implementation(
                    service_class, interface_class
                )
            except Exception as e:
                validation_results[service_name] = False
                print(f"Validation failed for {service_name}: {e}")
        
        return validation_results
