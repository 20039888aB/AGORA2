"""
Service Configuration - Centralized Service Settings

This module provides centralized configuration management
for all services with environment-specific settings and defaults.
"""

from typing import Dict, Any, List, Optional
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
import os
import logging

logger = logging.getLogger(__name__)


class ServiceConfigManager:
    """
    Centralized service configuration manager
    """
    
    def __init__(self):
        self.config_cache = {}
        self.environment = getattr(settings, 'ENVIRONMENT', 'development')
        self.load_configurations()
    
    def load_configurations(self):
        """Load all service configurations"""
        self.config_cache = {
            'cache': self.get_cache_config(),
            'monitoring': self.get_monitoring_config(),
            'notifications': self.get_notification_config(),
            'security': self.get_security_config(),
            'performance': self.get_performance_config(),
            'features': self.get_feature_config(),
            'integrations': self.get_integration_config(),
        }
    
    def get_cache_config(self) -> Dict[str, Any]:
        """Get cache configuration"""
        return {
            'enabled': getattr(settings, 'SERVICES_CACHE_ENABLED', True),
            'default_timeout': getattr(settings, 'SERVICES_CACHE_DEFAULT_TIMEOUT', 300),
            'timeout_overrides': getattr(settings, 'SERVICES_CACHE_TIMEOUTS', {}),
            'backend': getattr(settings, 'CACHES', {}).get('default', {}).get('BACKEND', 'django.core.cache.backends.locmem.LocMemCache'),
            'key_prefix': getattr(settings, 'SERVICES_CACHE_KEY_PREFIX', 'agoraprof_service'),
            'max_entries': getattr(settings, 'SERVICES_CACHE_MAX_ENTRIES', 1000),
            'compression': getattr(settings, 'SERVICES_CACHE_COMPRESSION', False),
        }
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration"""
        return {
            'enabled': getattr(settings, 'SERVICES_MONITORING_ENABLED', True),
            'log_level': getattr(settings, 'SERVICES_LOG_LEVEL', 'INFO'),
            'metrics_retention_days': getattr(settings, 'SERVICES_METRICS_RETENTION_DAYS', 30),
            'performance_thresholds': getattr(settings, 'SERVICES_PERFORMANCE_THRESHOLDS', {
                'warning': 1.0,  # seconds
                'critical': 5.0,  # seconds
            }),
            'error_notification_threshold': getattr(settings, 'SERVICES_ERROR_NOTIFICATION_THRESHOLD', 5),
            'track_slow_queries': getattr(settings, 'SERVICES_TRACK_SLOW_QUERIES', True),
            'slow_query_threshold': getattr(settings, 'SERVICES_SLOW_QUERY_THRESHOLD', 0.5),
        }
    
    def get_notification_config(self) -> Dict[str, Any]:
        """Get notification configuration"""
        return {
            'email_enabled': getattr(settings, 'SERVICES_EMAIL_ENABLED', True),
            'push_enabled': getattr(settings, 'SERVICES_PUSH_ENABLED', False),
            'sms_enabled': getattr(settings, 'SERVICES_SMS_ENABLED', False),
            'email_backend': getattr(settings, 'EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend'),
            'email_from': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@agoraprof.com'),
            'email_reply_to': getattr(settings, 'SERVICES_EMAIL_REPLY_TO', None),
            'email_bcc': getattr(settings, 'SERVICES_EMAIL_BCC', []),
            'rate_limit': getattr(settings, 'SERVICES_NOTIFICATION_RATE_LIMIT', {
                'user': 10,  # per hour
                'organization': 100,  # per hour
            }),
            'queue_enabled': getattr(settings, 'SERVICES_QUEUE_ENABLED', False),
            'queue_backend': getattr(settings, 'SERVICES_QUEUE_BACKEND', 'django.core.mail.backends.locmem.EmailBackend'),
        }
    
    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration"""
        return {
            'encryption_enabled': getattr(settings, 'SERVICES_ENCRYPTION_ENABLED', True),
            'encryption_key': getattr(settings, 'SERVICES_ENCRYPTION_KEY', ''),
            'rate_limiting_enabled': getattr(settings, 'SERVICES_RATE_LIMITING_ENABLED', True),
            'rate_limits': getattr(settings, 'SERVICES_RATE_LIMITS', {
                'api': {
                    'user': 1000,  # per hour
                    'organization': 5000,  # per hour
                },
                'file_upload': {
                    'user': 50,  # per hour
                    'organization': 500,  # per hour
                },
            }),
            'audit_enabled': getattr(settings, 'SERVICES_AUDIT_ENABLED', True),
            'audit_retention_days': getattr(settings, 'SERVICES_AUDIT_RETENTION_DAYS', 365),
            'permission_cache_timeout': getattr(settings, 'SERVICES_PERMISSION_CACHE_TIMEOUT', 300),
            'session_timeout': getattr(settings, 'SERVICES_SESSION_TIMEOUT', 3600),  # 1 hour
        }
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance configuration"""
        return {
            'pagination_default_size': getattr(settings, 'SERVICES_PAGINATION_DEFAULT_SIZE', 20),
            'pagination_max_size': getattr(settings, 'SERVICES_PAGINATION_MAX_SIZE', 100),
            'bulk_operations_max_size': getattr(settings, 'SERVICES_BULK_OPERATIONS_MAX_SIZE', 100),
            'query_timeout': getattr(settings, 'SERVICES_QUERY_TIMEOUT', 30),  # seconds
            'connection_pool_size': getattr(settings, 'SERVICES_CONNECTION_POOL_SIZE', 20),
            'connection_pool_max_overflow': getattr(settings, 'SERVICES_CONNECTION_POOL_MAX_OVERFLOW', 10),
            'optimize_queries': getattr(settings, 'SERVICES_OPTIMIZE_QUERIES', True),
            'prefetch_related': getattr(settings, 'SERVICES_PREFETCH_RELATED', True),
            'select_related': getattr(settings, 'SERVICES_SELECT_RELATED', True),
        }
    
    def get_feature_config(self) -> Dict[str, Any]:
        """Get feature configuration"""
        return {
            'user_management': {
                'profile_enabled': getattr(settings, 'SERVICES_USER_PROFILE_ENABLED', True),
                'avatar_upload': getattr(settings, 'SERVICES_USER_AVATAR_UPLOAD', True),
                'password_complexity': getattr(settings, 'SERVICES_PASSWORD_COMPLEXITY', True),
                'multi_factor_auth': getattr(settings, 'SERVICES_MFA_ENABLED', False),
                'social_login': getattr(settings, 'SERVICES_SOCIAL_LOGIN_ENABLED', False),
            },
            'course_management': {
                'video_streaming': getattr(settings, 'SERVICES_VIDEO_STREAMING_ENABLED', False),
                'file_upload': getattr(settings, 'SERVICES_FILE_UPLOAD_ENABLED', True),
                'auto_grading': getattr(settings, 'SERVICES_AUTO_GRADING_ENABLED', True),
                'plagiarism_check': getattr(settings, 'SERVICES_PLAGIARISM_CHECK_ENABLED', False),
                'advanced_analytics': getattr(settings, 'SERVICES_ADVANCED_ANALYTICS_ENABLED', True),
            },
            'certificates': {
                'pdf_generation': getattr(settings, 'SERVICES_PDF_GENERATION_ENABLED', True),
                'digital_signatures': getattr(settings, 'SERVICES_DIGITAL_SIGNATURES_ENABLED', False),
                'blockchain_verification': getattr(settings, 'SERVICES_BLOCKCHAIN_VERIFICATION_ENABLED', False),
                'custom_templates': getattr(settings, 'SERVICES_CUSTOM_CERTIFICATE_TEMPLATES', True),
            },
            'notifications': {
                'real_time': getattr(settings, 'SERVICES_REAL_TIME_NOTIFICATIONS', False),
                'push_notifications': getattr(settings, 'SERVICES_PUSH_NOTIFICATIONS', False),
                'sms_notifications': getattr(settings, 'SERVICES_SMS_NOTIFICATIONS', False),
                'webhook_notifications': getattr(settings, 'SERVICES_WEBHOOK_NOTIFICATIONS', False),
            },
        }
    
    def get_integration_config(self) -> Dict[str, Any]:
        """Get integration configuration"""
        return {
            'payment_gateways': getattr(settings, 'SERVICES_PAYMENT_GATEWAYS', {}),
            'email_providers': getattr(settings, 'SERVICES_EMAIL_PROVIDERS', {}),
            'file_storage': getattr(settings, 'SERVICES_FILE_STORAGE', {
                'backend': 'django.core.files.storage.FileSystemStorage',
                'location': 'uploads/',
                'base_url': '/uploads/',
            }),
            'analytics': getattr(settings, 'SERVICES_ANALYTICS', {}),
            'webhooks': getattr(settings, 'SERVICES_WEBHOOKS', {}),
            'third_party_apis': getattr(settings, 'SERVICES_THIRD_PARTY_APIS', {}),
        }
    
    def get_config(self, category: str, key: str = None, default: Any = None) -> Any:
        """Get configuration value"""
        if category not in self.config_cache:
            raise ValueError(f"Configuration category '{category}' not found")
        
        config = self.config_cache[category]
        
        if key is None:
            return config
        
        return config.get(key, default)
    
    def set_config(self, category: str, key: str, value: Any) -> None:
        """Set configuration value"""
        if category not in self.config_cache:
            self.config_cache[category] = {}
        
        self.config_cache[category][key] = value
    
    def get_service_config(self, service_name: str, key: str = None, default: Any = None) -> Any:
        """Get service-specific configuration"""
        service_configs = getattr(settings, 'SERVICES', {})
        service_config = service_configs.get(service_name, {})
        
        if key is None:
            return service_config
        
        return service_config.get(key, default)
    
    def is_feature_enabled(self, feature_path: str) -> bool:
        """Check if feature is enabled"""
        try:
            parts = feature_path.split('.')
            config = self.get_config('features')
            
            for part in parts:
                config = config.get(part, {})
            
            return config.get('enabled', False)
            
        except Exception:
            return False
    
    def get_environment_config(self) -> Dict[str, Any]:
        """Get environment-specific configuration"""
        return {
            'name': self.environment,
            'debug': getattr(settings, 'DEBUG', False),
            'allowed_hosts': getattr(settings, 'ALLOWED_HOSTS', []),
            'database': {
                'name': getattr(settings, 'DATABASES', {}).get('default', {}).get('NAME', ''),
                'engine': getattr(settings, 'DATABASES', {}).get('default', {}).get('ENGINE', ''),
            },
            'cache': {
                'backend': getattr(settings, 'CACHES', {}).get('default', {}).get('BACKEND', ''),
            },
            'media': {
                'url': getattr(settings, 'MEDIA_URL', ''),
                'root': getattr(settings, 'MEDIA_ROOT', ''),
            },
            'static': {
                'url': getattr(settings, 'STATIC_URL', ''),
                'root': getattr(settings, 'STATIC_ROOT', ''),
            },
        }
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate configuration"""
        issues = []
        
        # Validate cache configuration
        cache_config = self.get_config('cache')
        if cache_config['enabled'] and not cache_config['default_timeout']:
            issues.append('Cache enabled but no default timeout set')
        
        # Validate security configuration
        security_config = self.get_config('security')
        if security_config['encryption_enabled'] and not security_config['encryption_key']:
            issues.append('Encryption enabled but no encryption key set')
        
        # Validate notification configuration
        notification_config = self.get_config('notifications')
        if notification_config['email_enabled'] and not notification_config['email_from']:
            issues.append('Email notifications enabled but no from address set')
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'environment': self.environment,
        }


class ServiceSettings:
    """
    Service-specific settings with defaults and validation
    """
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.config_manager = ServiceConfigManager()
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get service-specific setting"""
        return self.config_manager.get_service_config(self.service_name, key, default)
    
    def get_cache_timeout(self, operation: str = 'default') -> int:
        """Get cache timeout for operation"""
        cache_config = self.config_manager.get_config('cache')
        timeouts = cache_config['timeout_overrides']
        
        service_key = f"{self.service_name}_{operation}"
        return timeouts.get(service_key, cache_config['default_timeout'])
    
    def is_enabled(self) -> bool:
        """Check if service is enabled"""
        return self.get_setting('enabled', True)
    
    def get_pagination_size(self) -> int:
        """Get pagination size"""
        default_size = self.config_manager.get_config('performance')['pagination_default_size']
        return self.get_setting('pagination_size', default_size)
    
    def get_rate_limit(self, operation: str = 'default') -> int:
        """Get rate limit for operation"""
        security_config = self.config_manager.get_config('security')
        rate_limits = security_config['rate_limits']
        
        return rate_limits.get(operation, 1000)  # Default to 1000 per hour
    
    def get_feature_setting(self, feature_path: str, default: Any = None) -> Any:
        """Get feature setting"""
        try:
            parts = feature_path.split('.')
            config = self.config_manager.get_config('features')
            
            for part in parts:
                config = config.get(part, {})
            
            return config if config != {} else default
            
        except Exception:
            return default
    
    def validate_service_config(self) -> Dict[str, Any]:
        """Validate service-specific configuration"""
        issues = []
        
        # Check if service is enabled
        if not self.is_enabled():
            issues.append(f'Service {self.service_name} is disabled')
        
        # Validate required settings based on service type
        if self.service_name == 'user':
            if self.get_feature_setting('user_management.profile_enabled', True):
                # Check if avatar upload is configured
                if self.get_feature_setting('user_management.avatar_upload', True):
                    media_config = self.config_manager.get_config('integrations')['file_storage']
                    if not media_config.get('location'):
                        issues.append('Avatar upload enabled but no file storage location set')
        
        elif self.service_name == 'course':
            if self.get_feature_setting('course_management.video_streaming', False):
                # Check video streaming configuration
                video_config = self.get_setting('video_streaming', {})
                if not video_config.get('provider'):
                    issues.append('Video streaming enabled but no provider configured')
        
        elif self.service_name == 'certificates':
            if self.get_feature_setting('certificates.pdf_generation', True):
                # Check PDF generation configuration
                pdf_config = self.get_setting('pdf_generation', {})
                if not pdf_config.get('engine'):
                    issues.append('PDF generation enabled but no engine configured')
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'service': self.service_name,
        }


# Global configuration manager instance
config_manager = ServiceConfigManager()

# Service settings factory
def get_service_settings(service_name: str) -> ServiceSettings:
    """Get service settings instance"""
    return ServiceSettings(service_name)

# Configuration validation
def validate_all_configurations() -> Dict[str, Any]:
    """Validate all configurations"""
    return {
        'general': config_manager.validate_config(),
        'services': {
            'user': get_service_settings('user').validate_service_config(),
            'organization': get_service_settings('organization').validate_service_config(),
            'course': get_service_settings('course').validate_service_config(),
            'enrollment': get_service_settings('enrollment').validate_service_config(),
            'assignment': get_service_settings('assignment').validate_service_config(),
            'certificate': get_service_settings('certificate').validate_service_config(),
        }
    }
