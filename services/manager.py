"""
Service Manager - Advanced Service Management

This module provides advanced service management with
dependency injection, caching, monitoring, and orchestration.
"""

from typing import Any, Dict, List, Optional, Union, Callable
from functools import wraps
from django.core.cache import cache
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
import logging
import time
import uuid

from .base import BaseService, ServiceResponse, ServiceMetrics
from .registry import ServiceRegistry, ServiceFactory, ServiceLocator, ServiceConfig

User = get_user_model()
logger = logging.getLogger(__name__)


class ServiceManager:
    """
    Advanced service manager with caching, monitoring, and orchestration
    """
    
    def __init__(self):
        self.cache_enabled = getattr(settings, 'SERVICES_CACHE_ENABLED', True)
        self.monitoring_enabled = getattr(settings, 'SERVICES_MONITORING_ENABLED', True)
        self.default_timeout = getattr(settings, 'SERVICES_DEFAULT_TIMEOUT', 30)
    
    def get_service(self, service_name: str, user: User = None, use_cache: bool = True) -> Any:
        """Get service with caching and monitoring"""
        start_time = time.time()
        
        try:
            # Check cache first
            if use_cache and self.cache_enabled:
                cache_key = f"service:{service_name}:{user.id if user else 'anonymous'}"
                cached_service = cache.get(cache_key)
                if cached_service:
                    logger.debug(f"Service {service_name} retrieved from cache")
                    return cached_service
            
            # Get service from registry
            service = ServiceFactory.create_service(service_name, user=user)
            
            # Cache the service
            if use_cache and self.cache_enabled:
                cache_timeout = ServiceConfig.get_cache_timeout(service_name)
                cache.set(cache_key, service, cache_timeout)
            
            # Log metrics
            if self.monitoring_enabled:
                duration = time.time() - start_time
                ServiceMetrics.log_service_call(service_name, 'get_service', user, duration)
            
            return service
            
        except Exception as e:
            if self.monitoring_enabled:
                ServiceMetrics.log_error(service_name, e, {'operation': 'get_service'})
            raise
    
    def execute_service_method(
        self,
        service_name: str,
        method_name: str,
        user: User = None,
        args: tuple = (),
        kwargs: Dict[str, Any] = None,
        use_transaction: bool = True,
        use_cache: bool = True
    ) -> ServiceResponse:
        """Execute service method with monitoring and transaction support"""
        start_time = time.time()
        kwargs = kwargs or {}
        
        try:
            service = self.get_service(service_name, user, use_cache)
            
            if not hasattr(service, method_name):
                raise AttributeError(f"Service {service_name} has no method '{method_name}'")
            
            method = getattr(service, method_name)
            
            # Execute with transaction if required
            if use_transaction:
                with transaction.atomic():
                    result = method(*args, **kwargs)
            else:
                result = method(*args, **kwargs)
            
            # Log success
            if self.monitoring_enabled:
                duration = time.time() - start_time
                ServiceMetrics.log_service_call(
                    service_name, 
                    method_name, 
                    user, 
                    duration
                )
            
            return ServiceResponse.success_response(data=result)
            
        except Exception as e:
            # Log error
            if self.monitoring_enabled:
                ServiceMetrics.log_error(
                    service_name, 
                    e, 
                    {
                        'method': method_name,
                        'args': args,
                        'kwargs': kwargs
                    }
                )
            
            return ServiceResponse.error_response(
                message=f"Service {service_name}.{method_name} failed: {str(e)}",
                errors=[str(e)]
            )
    
    def batch_execute(
        self,
        operations: List[Dict[str, Any]],
        user: User = None,
        fail_fast: bool = True
    ) -> List[ServiceResponse]:
        """Execute multiple service operations"""
        results = []
        
        for i, operation in enumerate(operations):
            try:
                result = self.execute_service_method(
                    service_name=operation['service'],
                    method_name=operation['method'],
                    user=user,
                    args=operation.get('args', ()),
                    kwargs=operation.get('kwargs', {})
                )
                results.append(result)
                
            except Exception as e:
                error_result = ServiceResponse.error_response(
                    message=f"Operation {i+1} failed: {str(e)}",
                    errors=[str(e)]
                )
                results.append(error_result)
                
                if fail_fast:
                    break
        
        return results


class ServiceOrchestrator:
    """
    Service orchestrator for complex workflows
    """
    
    def __init__(self, service_manager: ServiceManager = None):
        self.service_manager = service_manager or ServiceManager()
    
    def create_user_workflow(self, user_data: Dict[str, Any], created_by: User = None) -> ServiceResponse:
        """Orchestrate user creation workflow"""
        try:
            # Step 1: Create user
            user_service = self.service_manager.get_service('user', created_by)
            user = user_service.create_user(user_data, created_by)
            
            # Step 2: Create user profile
            profile_data = user_data.get('profile', {})
            if profile_data:
                user_service.update_user_profile(user, profile_data, created_by)
            
            # Step 3: Send welcome notification
            from .base import NotificationMixin
            NotificationMixin.send_email_notification(
                subject='Welcome to AgoraProf',
                message=f'Welcome {user.full_name}!',
                recipients=[user.email]
            )
            
            return ServiceResponse.success_response(
                data={'user_id': str(user.id)},
                message='User created successfully'
            )
            
        except Exception as e:
            return ServiceResponse.error_response(
                message=f"User creation workflow failed: {str(e)}",
                errors=[str(e)]
            )
    
    def create_course_workflow(self, course_data: Dict[str, Any], created_by: User = None) -> ServiceResponse:
        """Orchestrate course creation workflow"""
        try:
            # Step 1: Create course
            course_service = self.service_manager.get_service('course', created_by)
            course = course_service.create_course(course_data, created_by)
            
            # Step 2: Create default modules if specified
            modules_data = course_data.get('modules', [])
            if modules_data:
                for module_data in modules_data:
                    course_service.create_module(course, module_data, created_by)
            
            # Step 3: Notify instructors
            if course.instructor and course.instructor != created_by:
                from .base import NotificationMixin
                NotificationMixin.send_email_notification(
                    subject='New Course Assigned',
                    message=f'You have been assigned as instructor for {course.title}',
                    recipients=[course.instructor.email]
                )
            
            return ServiceResponse.success_response(
                data={'course_id': str(course.id)},
                message='Course created successfully'
            )
            
        except Exception as e:
            return ServiceResponse.error_response(
                message=f"Course creation workflow failed: {str(e)}",
                errors=[str(e)]
            )
    
    def enrollment_workflow(self, enrollment_data: Dict[str, Any], user: User = None) -> ServiceResponse:
        """Orchestrate enrollment workflow"""
        try:
            # Step 1: Create enrollment
            enrollment_service = self.service_manager.get_service('enrollment', user)
            enrollment = enrollment_service.create_enrollment(
                user=user,
                course=enrollment_data['course'],
                payment_status=enrollment_data.get('payment_status', 'PENDING'),
                payment_amount=enrollment_data.get('payment_amount', 0.00),
                enrolled_by=user
            )
            
            # Step 2: Process payment if completed
            if enrollment_data.get('payment_status') == 'COMPLETED':
                enrollment_service.activate_enrollment(enrollment, user)
            
            # Step 3: Send confirmation
            from .base import NotificationMixin
            NotificationMixin.send_email_notification(
                subject='Course Enrollment Confirmation',
                message=f'You have been enrolled in {enrollment.course.title}',
                recipients=[user.email]
            )
            
            return ServiceResponse.success_response(
                data={'enrollment_id': str(enrollment.id)},
                message='Enrollment completed successfully'
            )
            
        except Exception as e:
            return ServiceResponse.error_response(
                message=f"Enrollment workflow failed: {str(e)}",
                errors=[str(e)]
            )
    
    def assignment_submission_workflow(self, submission_data: Dict[str, Any], user: User = None) -> ServiceResponse:
        """Orchestrate assignment submission workflow"""
        try:
            # Step 1: Create submission
            assignment_service = self.service_manager.get_service('assignment', user)
            submission = assignment_service.create_submission(
                student=user,
                assignment=submission_data['assignment'],
                attempt_number=submission_data.get('attempt_number', 1)
            )
            
            # Step 2: Submit assignment
            assignment_service.submit_assignment(submission, user)
            
            # Step 3: Auto-grade if applicable
            if submission_data.get('auto_grade', False):
                assignment_service.auto_grade_submission(submission)
            
            # Step 4: Notify instructor
            from .base import NotificationMixin
            NotificationMixin.send_email_notification(
                subject='New Assignment Submission',
                message=f'{user.full_name} submitted {submission.assignment.title}',
                recipients=[submission.assignment.course.instructor.email]
            )
            
            return ServiceResponse.success_response(
                data={'submission_id': str(submission.id)},
                message='Assignment submitted successfully'
            )
            
        except Exception as e:
            return ServiceResponse.error_response(
                message=f"Assignment submission workflow failed: {str(e)}",
                errors=[str(e)]
            )
    
    def certificate_issuance_workflow(self, enrollment_data: Dict[str, Any], user: User = None) -> ServiceResponse:
        """Orchestrate certificate issuance workflow"""
        try:
            # Step 1: Get enrollment
            enrollment_service = self.service_manager.get_service('enrollment', user)
            enrollment = enrollment_data['enrollment']
            
            # Step 2: Issue certificate
            certificate_service = self.service_manager.get_service('certificate', user)
            certificate = certificate_service.create_certificate(enrollment, user=user)
            
            # Step 3: Send certificate notification
            from .base import NotificationMixin
            NotificationMixin.send_email_notification(
                subject='Certificate Issued',
                message=f'Congratulations! You have earned a certificate for {enrollment.course.title}',
                recipients=[enrollment.user.email]
            )
            
            return ServiceResponse.success_response(
                data={'certificate_id': str(certificate.id)},
                message='Certificate issued successfully'
            )
            
        except Exception as e:
            return ServiceResponse.error_response(
                message=f"Certificate issuance workflow failed: {str(e)}",
                errors=[str(e)]
            )


class ServiceCache:
    """
    Advanced caching for services
    """
    
    def __init__(self):
        self.default_timeout = 300
        self.key_prefix = 'agoraprof_service'
    
    def get_cache_key(self, service_name: str, operation: str, *args) -> str:
        """Generate cache key"""
        key_parts = [self.key_prefix, service_name, operation] + [str(arg) for arg in args]
        return ':'.join(key_parts)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get cached value"""
        return cache.get(key, default)
    
    def set(self, key: str, value: Any, timeout: int = None) -> None:
        """Set cached value"""
        timeout = timeout or self.default_timeout
        cache.set(key, value, timeout)
    
    def delete(self, key: str) -> None:
        """Delete cached value"""
        cache.delete(key)
    
    def clear_service_cache(self, service_name: str) -> None:
        """Clear all cache for a service"""
        pattern = f"{self.key_prefix}:{service_name}:*"
        cache.delete_pattern(pattern)
    
    def clear_all_cache(self) -> None:
        """Clear all service cache"""
        pattern = f"{self.key_prefix}:*"
        cache.delete_pattern(pattern)


class ServiceMonitor:
    """
    Service monitoring and metrics collection
    """
    
    def __init__(self):
        self.metrics = {}
        self.start_times = {}
    
    def start_timing(self, operation_id: str) -> None:
        """Start timing an operation"""
        self.start_times[operation_id] = time.time()
    
    def end_timing(self, operation_id: str, service_name: str, method: str) -> float:
        """End timing and return duration"""
        start_time = self.start_times.pop(operation_id, None)
        if start_time:
            duration = time.time() - start_time
            self.record_metric(service_name, method, duration)
            return duration
        return 0.0
    
    def record_metric(self, service_name: str, method: str, duration: float) -> None:
        """Record performance metric"""
        key = f"{service_name}.{method}"
        if key not in self.metrics:
            self.metrics[key] = []
        
        self.metrics[key].append({
            'duration': duration,
            'timestamp': timezone.now().isoformat()
        })
        
        # Keep only last 100 metrics per operation
        if len(self.metrics[key]) > 100:
            self.metrics[key] = self.metrics[key][-100:]
    
    def get_metrics(self, service_name: str = None, method: str = None) -> Dict[str, Any]:
        """Get collected metrics"""
        if service_name and method:
            key = f"{service_name}.{method}"
            return {'metrics': self.metrics.get(key, [])}
        elif service_name:
            service_metrics = {}
            for key, values in self.metrics.items():
                if key.startswith(f"{service_name}."):
                    service_metrics[key] = values
            return {'metrics': service_metrics}
        else:
            return {'metrics': self.metrics}
    
    def get_performance_summary(self, service_name: str, method: str = None) -> Dict[str, Any]:
        """Get performance summary"""
        metrics = self.get_metrics(service_name, method)['metrics']
        
        if not metrics:
            return {'count': 0, 'avg_duration': 0, 'max_duration': 0, 'min_duration': 0}
        
        durations = [m['duration'] for m in metrics]
        
        return {
            'count': len(metrics),
            'avg_duration': sum(durations) / len(durations),
            'max_duration': max(durations),
            'min_duration': min(durations),
            'last_10_avg': sum(durations[-10:]) / min(len(durations), 10)
        }


# Global service manager instance
service_manager = ServiceManager()
service_orchestrator = ServiceOrchestrator(service_manager)
service_cache = ServiceCache()
service_monitor = ServiceMonitor()
