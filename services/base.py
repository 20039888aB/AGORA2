"""
Base Service Layer - Foundation for All Services

This module provides the foundation for all service classes
with common patterns, error handling, and utilities.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from functools import wraps
import logging

User = get_user_model()

# Generic type for model instances
ModelType = TypeVar('ModelType', bound=models.Model)

logger = logging.getLogger(__name__)


class BaseService(ABC):
    """
    Abstract base class for all service classes
    Provides common patterns and utilities
    """
    
    def __init__(self):
        self.user = None
        self.organization = None
        self.errors = []
    
    def set_context(self, user: User = None, organization: Any = None):
        """Set execution context for service operations"""
        self.user = user
        self.organization = organization or (user.organization if user else None)
    
    def validate_permissions(self, user: User, action: str, resource: Any = None) -> bool:
        """
        Validate user permissions for an action
        Override in subclasses for specific permission logic
        """
        return True
    
    def validate_business_rules(self, **kwargs) -> bool:
        """
        Validate business rules before operation
        Override in subclasses for specific business logic
        """
        return True
    
    def log_action(self, action: str, details: Dict[str, Any], user: User = None):
        """
        Log action with audit trail
        """
        from audit_logs.models import AuditLog
        
        try:
            AuditLog.objects.create(
                user=user or self.user,
                action=action,
                details=details,
                ip_address=getattr(user or self.user, 'last_login_ip', None)
            )
        except Exception as e:
            logger.error(f"Failed to log action {action}: {e}")
    
    def handle_error(self, error: Exception, context: str = "") -> None:
        """
        Handle errors consistently
        """
        error_msg = f"{context}: {str(error)}" if context else str(error)
        self.errors.append(error_msg)
        logger.error(error_msg)
        raise ValidationError(error_msg)
    
    @staticmethod
    def transaction_wrapper(func):
        """
        Decorator to wrap service methods in database transactions
        """
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            with transaction.atomic():
                try:
                    return func(self, *args, **kwargs)
                except Exception as e:
                    self.handle_error(e, func.__name__)
        return wrapper
        return wrapper
    
    @staticmethod
    def permission_required(permission_class: str):
        """
        Decorator to check permissions before method execution
        """
        def decorator(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                if not hasattr(self, 'user') or not self.user:
                    raise ValidationError("User context not set")
                
                # Import permission class dynamically
                try:
                    from services.permissions import permission_class
                    permission_checker = permission_class()
                    
                    if not permission_checker.has_permission(None, None):
                        raise ValidationError(f"Permission denied: {permission_class.__name__}")
                except ImportError:
                    raise ValidationError(f"Permission class {permission_class} not found")
                
                return func(self, *args, **kwargs)
            return wrapper
        return decorator


class QuerySetMixin:
    """
    Mixin for common queryset operations
    """
    
    @staticmethod
    def filter_by_organization(queryset: models.QuerySet, organization: Any) -> models.QuerySet:
        """Filter queryset by organization"""
        if organization:
            return queryset.filter(organization=organization)
        return queryset
    
    @staticmethod
    def filter_by_user(queryset: models.QuerySet, user: User) -> models.QuerySet:
        """Filter queryset by user"""
        if user:
            return queryset.filter(user=user)
        return queryset
    
    @staticmethod
    def apply_filters(queryset: models.QuerySet, filters: Dict[str, Any]) -> models.QuerySet:
        """Apply multiple filters to queryset"""
        for field, value in filters.items():
            if value is not None:
                queryset = queryset.filter(**{field: value})
        return queryset
    
    @staticmethod
    def apply_search(queryset: models.QuerySet, search_fields: List[str], search_query: str) -> models.QuerySet:
        """Apply search across multiple fields"""
        if not search_query:
            return queryset
        
        from django.db.models import Q
        q_objects = Q()
        
        for field in search_fields:
            q_objects |= Q(**{f"{field}__icontains": search_query})
        
        return queryset.filter(q_objects)


class ValidationMixin:
    """
    Mixin for common validation patterns
    """
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> None:
        """Validate required fields are present"""
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        if missing_fields:
            raise ValidationError(f"Required fields missing: {', '.join(missing_fields)}")
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number format"""
        import re
        pattern = r'^\+?1?\d{9,15}$'
        return re.match(pattern, phone) is not None
    
    @staticmethod
    def validate_positive_number(value: Any, field_name: str = "value") -> None:
        """Validate positive number"""
        try:
            num_value = float(value)
            if num_value <= 0:
                raise ValidationError(f"{field_name} must be positive")
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name} must be a valid number")
    
    @staticmethod
    def validate_date_range(start_date, end_date, field_prefix: str = "") -> None:
        """Validate date range"""
        if start_date and end_date and start_date >= end_date:
            raise ValidationError(f"{field_prefix}start date must be before end date")
    
    @staticmethod
    def validate_choice(value: str, choices: List[str], field_name: str = "value") -> None:
        """Validate value against choices"""
        if value not in choices:
            raise ValidationError(f"{field_name} must be one of: {', '.join(choices)}")


class PaginationMixin:
    """
    Mixin for pagination operations
    """
    
    @staticmethod
    def paginate_queryset(queryset: models.QuerySet, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """Paginate queryset and return pagination info"""
        total_count = queryset.count()
        total_pages = (total_count + page_size - 1) // page_size
        
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        
        items = queryset[start_index:end_index]
        
        return {
            'items': items,
            'total_count': total_count,
            'total_pages': total_pages,
            'current_page': page,
            'page_size': page_size,
            'has_next': page < total_pages,
            'has_previous': page > 1,
        }
    
    @staticmethod
    def get_page_info(page: int, page_size: int, total_count: int) -> Dict[str, Any]:
        """Get pagination info without queryset"""
        total_pages = (total_count + page_size - 1) // page_size
        
        return {
            'current_page': page,
            'page_size': page_size,
            'total_count': total_count,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_previous': page > 1,
        }


class CacheMixin:
    """
    Mixin for caching operations
    """
    
    @staticmethod
    def get_cache_key(prefix: str, *args) -> str:
        """Generate cache key"""
        key_parts = [prefix] + [str(arg) for arg in args]
        return ':'.join(key_parts)
    
    @staticmethod
    def cache_result(cache_key: str, result: Any, timeout: int = 300) -> None:
        """Cache result"""
        from django.core.cache import cache
        cache.set(cache_key, result, timeout)
    
    @staticmethod
    def get_cached_result(cache_key: str, default: Any = None) -> Any:
        """Get cached result"""
        from django.core.cache import cache
        return cache.get(cache_key, default)
    
    @staticmethod
    def invalidate_cache(cache_key: str) -> None:
        """Invalidate cache"""
        from django.core.cache import cache
        cache.delete(cache_key)


class NotificationMixin:
    """
    Mixin for notification operations
    """
    
    @staticmethod
    def send_email_notification(
        subject: str,
        message: str,
        recipients: List[str],
        from_email: str = None,
        template_context: Dict[str, Any] = None
    ) -> bool:
        """Send email notification"""
        from django.core.mail import send_mail
        from django.conf import settings
        from django.template.loader import render_to_string
        
        try:
            if template_context:
                message = render_to_string('emails/notification.html', template_context)
            
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email or settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipients,
                fail_silently=True,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    @staticmethod
    def send_push_notification(user: User, title: str, message: str, data: Dict[str, Any] = None) -> bool:
        """Send push notification (placeholder for implementation)"""
        # This would integrate with a push notification service
        logger.info(f"Push notification sent to {user.email}: {title}")
        return True
    
    @staticmethod
    def create_notification(
        user: User,
        title: str,
        message: str,
        notification_type: str = 'INFO',
        data: Dict[str, Any] = None
    ) -> Any:
        """Create notification record"""
        from notifications.models import Notification
        
        try:
            notification = Notification.objects.create(
                user=user,
                title=title,
                message=message,
                notification_type=notification_type,
                data=data or {}
            )
            return notification
        except Exception as e:
            logger.error(f"Failed to create notification: {e}")
            return None


class ServiceResponse:
    """
    Standardized service response
    """
    
    def __init__(self, success: bool = True, data: Any = None, message: str = "", errors: List[str] = None):
        self.success = success
        self.data = data
        self.message = message
        self.errors = errors or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'success': self.success,
            'data': self.data,
            'message': self.message,
            'errors': self.errors
        }
    
    @classmethod
    def success_response(cls, data: Any = None, message: str = "") -> 'ServiceResponse':
        """Create success response"""
        return cls(success=True, data=data, message=message)
    
    @classmethod
    def error_response(cls, message: str, errors: List[str] = None, data: Any = None) -> 'ServiceResponse':
        """Create error response"""
        return cls(success=False, message=message, errors=errors, data=data)


class ServiceMetrics:
    """
    Service metrics and monitoring
    """
    
    @staticmethod
    def log_service_call(service_name: str, method: str, user: User = None, duration: float = None) -> None:
        """Log service call for metrics"""
        logger.info(f"Service call: {service_name}.{method} by {user.email if user else 'system'} took {duration}s")
    
    @staticmethod
    def log_performance(service_name: str, operation: str, metrics: Dict[str, Any]) -> None:
        """Log performance metrics"""
        logger.info(f"Performance: {service_name}.{operation}: {metrics}")
    
    @staticmethod
    def log_error(service_name: str, error: Exception, context: Dict[str, Any] = None) -> None:
        """Log error with context"""
        logger.error(f"Error in {service_name}: {str(error)} | Context: {context}")
