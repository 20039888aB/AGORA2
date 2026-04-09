# AgoraProf LMS - Services Layer Architecture

## 🏗️ **Enterprise Services Layer Design**

This document describes the comprehensive services layer architecture for the AgoraProf LMS, providing centralized business logic, dependency injection, and enterprise-grade patterns.

---

## 📋 **Table of Contents**

1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)
3. [Service Patterns](#service-patterns)
4. [Configuration Management](#configuration-management)
5. [Monitoring & Metrics](#monitoring--metrics)
6. [Testing Strategy](#testing-strategy)
7. [Best Practices](#best-practices)
8. [Examples](#examples)

---

## 🏛️ **Architecture Overview**

### **Layer Structure**
```
┌─────────────────────────────────────────────────┐
│                API Layer (Views)                │
├─────────────────────────────────────────────────┤
│              Services Layer (Business Logic)      │
├─────────────────────────────────────────────────┤
│                Data Layer (Models)               │
└─────────────────────────────────────────────────┘
```

### **Key Principles**
- **Single Responsibility**: Each service handles one domain
- **Dependency Injection**: Services are injected with dependencies
- **Interface Segregation**: Services implement clear interfaces
- **Configuration Management**: Centralized configuration
- **Monitoring**: Comprehensive logging and metrics
- **Testing**: Unit and integration tests for all services

---

## 🔧 **Core Components**

### **1. Base Service (`base.py`)**
```python
class BaseService(ABC):
    """Abstract base class for all service classes"""
    
    def set_context(self, user: User = None, organization: Any = None)
    def validate_permissions(self, user: User, action: str, resource: Any = None) -> bool
    def log_action(self, action: str, details: Dict[str, Any], user: User = None)
    @staticmethod
    def transaction_wrapper(func)
    @staticmethod
    def permission_required(permission_class: str)
```

### **2. Service Registry (`registry.py`)**
```python
class ServiceRegistry:
    """Centralized service registry for dependency injection"""
    
    @classmethod
    def register(cls, name: str, service_class: Type[Any]) -> None
    @classmethod
    def get_service(cls, name: str) -> Any
    @classmethod
    def list_services(cls) -> List[str]
```

### **3. Service Manager (`manager.py`)**
```python
class ServiceManager:
    """Advanced service manager with caching, monitoring, and orchestration"""
    
    def get_service(self, service_name: str, user: User = None, use_cache: bool = True) -> Any
    def execute_service_method(self, service_name: str, method_name: str, ...) -> ServiceResponse
    def batch_execute(self, operations: List[Dict[str, Any]], ...) -> List[ServiceResponse]
```

### **4. Service Orchestrator (`manager.py`)**
```python
class ServiceOrchestrator:
    """Service orchestrator for complex workflows"""
    
    def create_user_workflow(self, user_data: Dict[str, Any], created_by: User = None) -> ServiceResponse
    def create_course_workflow(self, course_data: Dict[str, Any], created_by: User = None) -> ServiceResponse
    def enrollment_workflow(self, enrollment_data: Dict[str, Any], user: User = None) -> ServiceResponse
```

### **5. Service Interfaces (`interfaces.py`)**
```python
class IUserService(IService):
    """User service interface"""
    
    @abstractmethod
    def create_user(self, data: Dict[str, Any], created_by: User = None) -> User
    @abstractmethod
    def update_user(self, user: User, data: Dict[str, Any], updated_by: User = None) -> User
    # ... other methods
```

---

## 🎯 **Service Patterns**

### **1. Service Factory Pattern**
```python
class ServiceFactory:
    """Factory pattern for creating service instances"""
    
    @staticmethod
    def create_service(service_name: str, user: User = None, **kwargs) -> Any
    @staticmethod
    def create_user_service(user: User = None, **kwargs) -> Any
    @staticmethod
    def create_course_service(user: User = None, **kwargs) -> Any
```

### **2. Service Locator Pattern**
```python
class ServiceLocator:
    """Service locator pattern for dependency resolution"""
    
    @staticmethod
    def get_user_service(user: User = None) -> Any
    @staticmethod
    def get_course_service(user: User = None) -> Any
    @staticmethod
    def get_enrollment_service(user: User = None) -> Any
```

### **3. Repository Pattern**
```python
class UserRepository:
    """Repository pattern for data access"""
    
    def get_by_id(self, user_id: str) -> Optional[User]
    def get_by_email(self, email: str) -> Optional[User]
    def get_active_users(self, organization: Any = None) -> QuerySet[User]
    def search_users(self, query: str, filters: Dict[str, Any] = None) -> QuerySet[User]
```

### **4. Command Pattern**
```python
class CreateUserCommand:
    """Command pattern for user creation"""
    
    def __init__(self, user_data: Dict[str, Any], created_by: User = None)
    def execute(self) -> ServiceResponse
    def undo(self) -> ServiceResponse
```

### **5. Observer Pattern**
```python
class UserEventObserver:
    """Observer pattern for user events"""
    
    def on_user_created(self, user: User) -> None
    def on_user_updated(self, user: User, old_data: Dict[str, Any]) -> None
    def on_user_deleted(self, user: User) -> None
```

---

## ⚙️ **Configuration Management**

### **1. Service Configuration (`config.py`)**
```python
class ServiceConfigManager:
    """Centralized service configuration manager"""
    
    def get_cache_config(self) -> Dict[str, Any]
    def get_monitoring_config(self) -> Dict[str, Any]
    def get_notification_config(self) -> Dict[str, Any]
    def get_security_config(self) -> Dict[str, Any]
    def get_performance_config(self) -> Dict[str, Any]
```

### **2. Environment-Specific Settings**
```python
# Development
SERVICES_CACHE_ENABLED = False
SERVICES_MONITORING_ENABLED = True
SERVICES_LOG_LEVEL = 'DEBUG'

# Production
SERVICES_CACHE_ENABLED = True
SERVICES_MONITORING_ENABLED = True
SERVICES_LOG_LEVEL = 'INFO'

# Testing
SERVICES_CACHE_ENABLED = False
SERVICES_MONITORING_ENABLED = False
SERVICES_LOG_LEVEL = 'ERROR'
```

### **3. Service-Specific Settings**
```python
SERVICES = {
    'user': {
        'enabled': True,
        'cache_timeout': 300,
        'rate_limit': 1000,
        'features': {
            'profile_enabled': True,
            'avatar_upload': True,
            'mfa_enabled': False,
        }
    },
    'course': {
        'enabled': True,
        'cache_timeout': 600,
        'rate_limit': 500,
        'features': {
            'video_streaming': False,
            'auto_grading': True,
            'advanced_analytics': True,
        }
    }
}
```

---

## 📊 **Monitoring & Metrics**

### **1. Service Metrics**
```python
class ServiceMetrics:
    """Service metrics and monitoring"""
    
    @staticmethod
    def log_service_call(service_name: str, method: str, user: User = None, duration: float = None) -> None
    @staticmethod
    def log_performance(service_name: str, operation: str, metrics: Dict[str, Any]) -> None
    @staticmethod
    def log_error(service_name: str, error: Exception, context: Dict[str, Any] = None) -> None
```

### **2. Health Checking**
```python
class ServiceHealthChecker:
    """Health checking for services"""
    
    @staticmethod
    def check_service_health(service_name: str) -> Dict[str, Any]
    @staticmethod
    def check_all_services() -> Dict[str, Any]
```

### **3. Performance Monitoring**
```python
class ServiceMonitor:
    """Service performance monitoring"""
    
    def start_timing(self, operation_id: str) -> None
    def end_timing(self, operation_id: str, service_name: str, method: str) -> float
    def record_metric(self, service_name: str, method: str, duration: float) -> None
    def get_performance_summary(self, service_name: str, method: str = None) -> Dict[str, Any]
```

---

## 🧪 **Testing Strategy**

### **1. Unit Tests**
```python
class TestUserService(TestCase):
    """Unit tests for user service"""
    
    def setUp(self):
        self.service = ServiceFactory.create_user_service()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='test123'
        )
    
    def test_create_user(self):
        """Test user creation"""
        data = {
            'email': 'newuser@example.com',
            'password': 'password123',
            'first_name': 'John',
            'last_name': 'Doe',
            'role': 'STUDENT'
        }
        
        result = self.service.create_user(data)
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.data['user'])
        self.assertEqual(result.data['user'].email, data['email'])
    
    def test_create_user_duplicate_email(self):
        """Test user creation with duplicate email"""
        data = {
            'email': self.user.email,
            'password': 'password123',
            'first_name': 'Jane',
            'last_name': 'Doe',
            'role': 'STUDENT'
        }
        
        result = self.service.create_user(data)
        
        self.assertFalse(result.success)
        self.assertIn('already exists', result.message)
```

### **2. Integration Tests**
```python
class TestUserIntegration(TestCase):
    """Integration tests for user service"""
    
    def test_user_enrollment_workflow(self):
        """Test complete user enrollment workflow"""
        # Create user
        user_service = ServiceFactory.create_user_service()
        user_data = {
            'email': 'student@example.com',
            'password': 'password123',
            'first_name': 'Student',
            'last_name': 'User',
            'role': 'STUDENT'
        }
        user = user_service.create_user(user_data)
        
        # Create course
        course_service = ServiceFactory.create_course_service()
        course_data = {
            'title': 'Test Course',
            'description': 'Test Description',
            'organization': self.organization,
            'instructor': self.instructor
        }
        course = course_service.create_course(course_data)
        
        # Create enrollment
        enrollment_service = ServiceFactory.create_enrollment_service()
        enrollment = enrollment_service.create_enrollment(user, course)
        
        # Verify workflow completed
        self.assertIsNotNone(enrollment)
        self.assertEqual(enrollment.user, user)
        self.assertEqual(enrollment.course, course)
```

### **3. Performance Tests**
```python
class TestServicePerformance(TestCase):
    """Performance tests for services"""
    
    def test_user_service_performance(self):
        """Test user service performance"""
        service = ServiceFactory.create_user_service()
        
        # Measure performance
        start_time = time.time()
        
        for i in range(1000):
            data = {
                'email': f'user{i}@example.com',
                'password': 'password123',
                'first_name': f'User {i}',
                'last_name': f'Test {i}',
                'role': 'STUDENT'
            }
            service.create_user(data)
        
        duration = time.time() - start_time
        
        # Performance assertion
        self.assertLess(duration, 5.0, "User creation took too long")
        
        # Average time per operation
        avg_time = duration / 1000
        self.assertLess(avg_time, 0.01, "Average time per user creation too high")
```

---

## 📋 **Best Practices**

### **1. Service Design**
- **Single Responsibility**: Each service handles one domain
- **Interface Segregation**: Services implement clear interfaces
- **Dependency Injection**: Dependencies are injected, not hardcoded
- **Configuration**: All configuration is externalized
- **Error Handling**: Consistent error handling across services
- **Logging**: Comprehensive logging for debugging and monitoring

### **2. Code Organization**
- **Base Classes**: Use base classes for common functionality
- **Mixins**: Use mixins for reusable functionality
- **Factories**: Use factories for service creation
- **Locators**: Use locators for dependency resolution
- **Registry**: Use registry for service management

### **3. Performance**
- **Caching**: Cache frequently accessed data
- **Database Optimization**: Use select_related and prefetch_related
- **Batch Operations**: Use bulk operations for large datasets
- **Connection Pooling**: Use connection pooling for database access
- **Lazy Loading**: Load data only when needed

### **4. Security**
- **Permission Checking**: Check permissions at service level
- **Input Validation**: Validate all inputs at service level
- **SQL Injection**: Use parameterized queries
- **Data Encryption**: Encrypt sensitive data
- **Audit Logging**: Log all important actions

### **5. Testing**
- **Unit Tests**: Test individual service methods
- **Integration Tests**: Test service interactions
- **Performance Tests**: Test service performance
- **Mock Testing**: Use mocks for external dependencies
- **Test Coverage**: Maintain high test coverage

---

## 💡 **Examples**

### **1. Creating a New Service**
```python
# 1. Create service class
class NotificationService(BaseService):
    """Notification service implementation"""
    
    def send_email(self, subject: str, message: str, recipients: List[str]) -> ServiceResponse:
        try:
            # Business logic
            from django.core.mail import send_mail
            send_mail(subject, message, 'noreply@agoraprof.com', recipients)
            
            # Log action
            self.log_action('EMAIL_SENT', {
                'subject': subject,
                'recipients': recipients
            })
            
            return ServiceResponse.success_response(
                message='Email sent successfully'
            )
            
        except Exception as e:
            return ServiceResponse.error_response(
                message=f'Failed to send email: {str(e)}',
                errors=[str(e)]
            )

# 2. Register service
ServiceRegistry.register('notification', NotificationService)

# 3. Use service
notification_service = ServiceLocator.get_notification_service()
result = notification_service.send_email(
    'Test Subject',
    'Test Message',
    ['user@example.com']
)
```

### **2. Using Service Manager**
```python
# Execute service method with monitoring
result = service_manager.execute_service_method(
    service_name='user',
    method_name='create_user',
    user=admin_user,
    kwargs={
        'data': {
            'email': 'newuser@example.com',
            'password': 'password123',
            'first_name': 'John',
            'last_name': 'Doe',
            'role': 'STUDENT'
        }
    }
)

if result.success:
    print(f"User created with ID: {result.data['user'].id}")
else:
    print(f"Error: {result.message}")
```

### **3. Using Service Orchestrator**
```python
# Execute complete workflow
result = service_orchestrator.create_user_workflow(
    user_data={
        'email': 'newuser@example.com',
        'password': 'password123',
        'first_name': 'John',
        'last_name': 'Doe',
        'role': 'STUDENT',
        'profile': {
            'phone': '+1234567890',
            'address': '123 Main St'
        }
    },
    created_by=admin_user
)

if result.success:
    print(f"User workflow completed: {result.message}")
else:
    print(f"Workflow failed: {result.message}")
```

### **4. Configuration Usage**
```python
# Get service settings
user_settings = get_service_settings('user')

# Check if feature is enabled
if user_settings.get_feature_setting('user_management.avatar_upload', True):
    # Enable avatar upload
    pass

# Get cache timeout
cache_timeout = user_settings.get_cache_timeout('user_profile')

# Get rate limit
rate_limit = user_settings.get_rate_limit('user_creation')
```

---

## 🚀 **Getting Started**

### **1. Import Services**
```python
from services.manager import service_manager, service_orchestrator
from services.registry import ServiceLocator
from services.config import config_manager
```

### **2. Create Service Instance**
```python
# Using factory
user_service = ServiceFactory.create_user_service(user=request.user)

# Using locator
user_service = ServiceLocator.get_user_service(user=request.user)

# Using manager
user_service = service_manager.get_service('user', user=request.user)
```

### **3. Execute Service Method**
```python
# Direct execution
result = user_service.create_user(user_data, created_by=request.user)

# Using manager (with monitoring)
result = service_manager.execute_service_method(
    service_name='user',
    method_name='create_user',
    user=request.user,
    kwargs={'data': user_data, 'created_by': request.user}
)
```

### **4. Handle Response**
```python
if result.success:
    print(f"Success: {result.message}")
    user = result.data['user']
else:
    print(f"Error: {result.message}")
    for error in result.errors:
        print(f"Error detail: {error}")
```

---

## 📚 **Additional Resources**

- [Django Best Practices](https://django-best-practices.readthedocs.io/)
- [Enterprise Architecture Patterns](https://www.enterpriseintegrationpatterns.com/)
- [Service Layer Architecture](https://martinfowler.com/eaaCatalog/serviceLayer.html)
- [Dependency Injection](https://en.wikipedia.org/wiki/Dependency_injection)
- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)

---

## 🎯 **Next Steps**

1. **Review Services**: Review all existing services for compliance
2. **Add Tests**: Add comprehensive tests for all services
3. **Monitor Performance**: Set up monitoring and alerting
4. **Document**: Document service-specific patterns and conventions
5. **Refactor**: Refactor existing code to use services where appropriate

---

## 📞 **Support**

For questions or issues with the services layer:
- Check the service documentation
- Review the test cases
- Look at the configuration examples
- Contact the development team

---

*This services layer provides a robust, scalable foundation for the AgoraProf LMS with enterprise-grade patterns and comprehensive monitoring.*
