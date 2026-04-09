"""
Service Registry - Centralized Service Management

This module provides a registry pattern for managing all services
with dependency injection, factory patterns, and service discovery.
"""

from typing import Dict, Type, Any, Optional, List
from django.conf import settings
from django.contrib.auth import get_user_model
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class ServiceRegistry:
    """
    Centralized service registry for dependency injection
    and service management
    """
    
    _services: Dict[str, Any] = {}
    _instances: Dict[str, Any] = {}
    
    @classmethod
    def register(cls, name: str, service_class: Type[Any]) -> None:
        """Register a service class"""
        cls._services[name] = service_class
        logger.info(f"Service registered: {name}")
    
    @classmethod
    def register_instance(cls, name: str, instance: Any) -> None:
        """Register a service instance"""
        cls._instances[name] = instance
        logger.info(f"Service instance registered: {name}")
    
    @classmethod
    def get_service(cls, name: str) -> Any:
        """Get service instance (lazy initialization)"""
        if name not in cls._instances:
            if name in cls._services:
                cls._instances[name] = cls._services[name]()
            else:
                raise ValueError(f"Service '{name}' not registered")
        return cls._instances[name]
    
    @classmethod
    def get_service_class(cls, name: str) -> Type[Any]:
        """Get service class"""
        if name not in cls._services:
            raise ValueError(f"Service '{name}' not registered")
        return cls._services[name]
    
    @classmethod
    def list_services(cls) -> List[str]:
        """List all registered services"""
        return list(cls._services.keys())
    
    @classmethod
    def clear_registry(cls) -> None:
        """Clear all registered services (for testing)"""
        cls._services.clear()
        cls._instances.clear()
        logger.info("Service registry cleared")


class ServiceFactory:
    """
    Factory pattern for creating service instances
    with proper dependency injection
    """
    
    @staticmethod
    def create_service(service_name: str, user: User = None, **kwargs) -> Any:
        """Create service instance with context"""
        try:
            service_class = ServiceRegistry.get_service_class(service_name)
            
            # Create instance
            instance = service_class()
            
            # Set context if user provided
            if user and hasattr(instance, 'set_context'):
                instance.set_context(user=user)
            
            # Apply additional configuration
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            
            return instance
            
        except ValueError as e:
            logger.error(f"Failed to create service '{service_name}': {e}")
            raise
    
    @staticmethod
    def create_user_service(user: User = None, **kwargs) -> Any:
        """Create user service with user context"""
        return ServiceFactory.create_service('user', user=user, **kwargs)
    
    @staticmethod
    def create_organization_service(user: User = None, **kwargs) -> Any:
        """Create organization service with user context"""
        return ServiceFactory.create_service('organization', user=user, **kwargs)
    
    @staticmethod
    def create_course_service(user: User = None, **kwargs) -> Any:
        """Create course service with user context"""
        return ServiceFactory.create_service('course', user=user, **kwargs)
    
    @staticmethod
    def create_enrollment_service(user: User = None, **kwargs) -> Any:
        """Create enrollment service with user context"""
        return ServiceFactory.create_service('enrollment', user=user, **kwargs)
    
    @staticmethod
    def create_assignment_service(user: User = None, **kwargs) -> Any:
        """Create assignment service with user context"""
        return ServiceFactory.create_service('assignment', user=user, **kwargs)
    
    @staticmethod
    def create_certificate_service(user: User = None, **kwargs) -> Any:
        """Create certificate service with user context"""
        return ServiceFactory.create_service('certificate', user=user, **kwargs)


class ServiceLocator:
    """
    Service locator pattern for dependency resolution
    """
    
    @staticmethod
    def get_user_service(user: User = None) -> Any:
        """Get user service"""
        return ServiceFactory.create_user_service(user=user)
    
    @staticmethod
    def get_organization_service(user: User = None) -> Any:
        """Get organization service"""
        return ServiceFactory.create_organization_service(user=user)
    
    @staticmethod
    def get_course_service(user: User = None) -> Any:
        """Get course service"""
        return ServiceFactory.create_course_service(user=user)
    
    @staticmethod
    def get_enrollment_service(user: User = None) -> Any:
        """Get enrollment service"""
        return ServiceFactory.create_enrollment_service(user=user)
    
    @staticmethod
    def get_assignment_service(user: User = None) -> Any:
        """Get assignment service"""
        return ServiceFactory.create_assignment_service(user=user)
    
    @staticmethod
    def get_certificate_service(user: User = None) -> Any:
        """Get certificate service"""
        return ServiceFactory.create_certificate_service(user=user)


class ServiceConfig:
    """
    Configuration management for services
    """
    
    @staticmethod
    def get_setting(service_name: str, setting_name: str, default: Any = None) -> Any:
        """Get service-specific setting"""
        service_settings = getattr(settings, 'SERVICES', {})
        service_config = service_settings.get(service_name, {})
        return service_config.get(setting_name, default)
    
    @staticmethod
    def is_enabled(service_name: str) -> bool:
        """Check if service is enabled"""
        return ServiceConfig.get_setting(service_name, 'enabled', True)
    
    @staticmethod
    def get_cache_timeout(service_name: str, operation: str = 'default') -> int:
        """Get cache timeout for service operation"""
        cache_settings = ServiceConfig.get_setting(service_name, 'cache', {})
        return cache_settings.get(f'{operation}_timeout', 300)
    
    @staticmethod
    def get_pagination_size(service_name: str) -> int:
        """Get pagination size for service"""
        return ServiceConfig.get_setting(service_name, 'pagination_size', 20)


class ServiceHealthChecker:
    """
    Health checking for services
    """
    
    @staticmethod
    def check_service_health(service_name: str) -> Dict[str, Any]:
        """Check health of a specific service"""
        try:
            service = ServiceRegistry.get_service(service_name)
            
            # Basic health checks
            health_status = {
                'service': service_name,
                'status': 'healthy',
                'timestamp': timezone.now().isoformat(),
                'checks': {}
            }
            
            # Check database connectivity
            try:
                from django.db import connection
                connection.ensure_connection()
                health_status['checks']['database'] = 'healthy'
            except Exception as e:
                health_status['checks']['database'] = f'unhealthy: {str(e)}'
                health_status['status'] = 'unhealthy'
            
            # Check service-specific health
            if hasattr(service, 'health_check'):
                service_health = service.health_check()
                health_status['checks'].update(service_health)
            
            return health_status
            
        except Exception as e:
            return {
                'service': service_name,
                'status': 'unhealthy',
                'timestamp': timezone.now().isoformat(),
                'error': str(e)
            }
    
    @staticmethod
    def check_all_services() -> Dict[str, Any]:
        """Check health of all registered services"""
        services = ServiceRegistry.list_services()
        health_report = {
            'overall_status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'services': {}
        }
        
        unhealthy_services = []
        
        for service_name in services:
            health = ServiceHealthChecker.check_service_health(service_name)
            health_report['services'][service_name] = health
            
            if health['status'] != 'healthy':
                unhealthy_services.append(service_name)
        
        if unhealthy_services:
            health_report['overall_status'] = 'degraded'
            health_report['unhealthy_services'] = unhealthy_services
        
        return health_report


# Auto-register all services when module is imported
def auto_register_services():
    """Auto-register all service classes"""
    try:
        from .user_service import UserService
        from .organization_service import OrganizationService
        from .course_service import CourseService
        from .enrollment_service import EnrollmentService
        from .assignment_service import AssignmentService
        from .certificate_service import CertificateService
        
        ServiceRegistry.register('user', UserService)
        ServiceRegistry.register('organization', OrganizationService)
        ServiceRegistry.register('course', CourseService)
        ServiceRegistry.register('enrollment', EnrollmentService)
        ServiceRegistry.register('assignment', AssignmentService)
        ServiceRegistry.register('certificate', CertificateService)
        
        logger.info("All services auto-registered successfully")
        
    except ImportError as e:
        logger.error(f"Failed to auto-register services: {e}")


# Initialize services on import
auto_register_services()
