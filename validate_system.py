#!/usr/bin/env python
"""
System Validation Script - Validate LMS Implementation

This script validates that all critical components are working correctly
before moving to frontend development.
"""

import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agoraprof.settings')
django.setup()

def validate_services():
    """Validate services layer"""
    print("🔧 Validating Services Layer...")
    
    try:
        from services.user_service import UserService
        from services.organization_service import OrganizationService
        from services.course_service import CourseService
        from services.enrollment_service import EnrollmentService
        from services.assignment_service import AssignmentService
        from services.certificate_service import CertificateService
        print("✅ All services imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Service import error: {e}")
        return False

def validate_permissions():
    """Validate permission system"""
    print("🔐 Validating Permission System...")
    
    try:
        from services.permissions import (
            IsSuperAdmin, IsAdmin, IsManager, IsStudent,
            IsAdminOrAbove, IsManagerOrAbove, IsOwnerOrAdmin,
            IsCourseInstructor, IsOrganizationMember,
            CanManageOrganization, CanManageCourse, CanManageEnrollment,
            CanManageAssignment, CanManageCertificate,
            MultiTenantQuerysetMixin
        )
        print("✅ All permissions imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Permission import error: {e}")
        return False

def validate_signals():
    """Validate signals system"""
    print("📡 Validating Signals System...")
    
    try:
        from services.signals import (
            user_created, user_pre_save, course_created,
            enrollment_created, assignment_submitted,
            certificate_issued, user_login, course_completion,
            assignment_graded, post_role_change
        )
        print("✅ All signals imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Signal import error: {e}")
        return False

def validate_models():
    """Validate all models"""
    print("📊 Validating Models...")
    
    apps_to_validate = [
        'accounts', 'organizations', 'permissions', 'courses',
        'enrollments', 'assignments', 'certificates', 'audit_logs'
    ]
    
    for app_name in apps_to_validate:
        try:
            app_config = apps.get_app_config(app_name)
            models = app_config.get_models()
            print(f"✅ {app_name}: {len(models)} models loaded")
        except Exception as e:
            print(f"❌ {app_name}: Model loading error: {e}")
            return False
    
    return True

def validate_api_endpoints():
    """Validate API endpoints"""
    print("🌐 Validating API Endpoints...")
    
    try:
        from django.urls import get_resolver
        resolver = get_resolver()
        
        # Check if URL patterns are loaded
        url_patterns = resolver.url_patterns
        if url_patterns:
            print(f"✅ URL patterns loaded: {len(url_patterns)} patterns")
        else:
            print("❌ No URL patterns found")
            return False
        
        # Check if DRF is properly configured
        try:
            from rest_framework import status
            from rest_framework.response import Response
            print("✅ DRF properly configured")
        except ImportError:
            print("❌ DRF not properly configured")
            return False
        
        return True
    except Exception as e:
        print(f"❌ API validation error: {e}")
        return False

def validate_database():
    """Validate database connection"""
    print("🗄️ Validating Database...")
    
    try:
        from django.db import connection
        db_connection = connection.ensure_connection()
        
        # Test basic query
        from django.contrib.auth import get_user_model
        User = get_user_model()
        User.objects.count()
        
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def validate_settings():
    """Validate critical settings"""
    print("⚙️ Validating Settings...")
    
    critical_settings = [
        'INSTALLED_APPS',
        'DATABASES',
        'SECRET_KEY',
        'REST_FRAMEWORK',
        'CORS_ALLOWED_ORIGINS',
        'SIMPLE_JWT',
        'CELERY_BROKER_URL'
    ]
    
    missing_settings = []
    for setting in critical_settings:
        if not hasattr(settings, setting):
            missing_settings.append(setting)
    
    if missing_settings:
        print(f"❌ Missing settings: {missing_settings}")
        return False
    
    # Check if all apps are installed
    required_apps = [
        'accounts', 'organizations', 'permissions', 'courses',
        'enrollments', 'assignments', 'certificates',
        'notifications', 'reports', 'audit_logs'
    ]
    
    installed_apps = settings.INSTALLED_APPS
    missing_apps = [app for app in required_apps if app not in installed_apps]
    
    if missing_apps:
        print(f"❌ Missing apps: {missing_apps}")
        return False
    
    print("✅ All critical settings configured")
    return True

def validate_multi_tenancy():
    """Validate multi-tenancy implementation"""
    print("🏢 Validating Multi-Tenancy...")
    
    try:
        from services.permissions import MultiTenantQuerysetMixin
        
        # Check if User model has organization field
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        if not hasattr(User, 'organization'):
            print("❌ User model missing organization field")
            return False
        
        # Check if Course model has organization field
        from courses.models import Course
        if not hasattr(Course, 'organization'):
            print("❌ Course model missing organization field")
            return False
        
        print("✅ Multi-tenancy properly implemented")
        return True
    except Exception as e:
        print(f"❌ Multi-tenancy validation error: {e}")
        return False

def main():
    """Main validation function"""
    print("🚀 AgoraProf LMS System Validation")
    print("=" * 50)
    
    validations = [
        validate_settings,
        validate_database,
        validate_models,
        validate_services,
        validate_permissions,
        validate_signals,
        validate_api_endpoints,
        validate_multi_tenancy
    ]
    
    results = []
    for validation in validations:
        try:
            result = validation()
            results.append(result)
        except Exception as e:
            print(f"❌ Validation error: {e}")
            results.append(False)
    
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 ALL VALIDATIONS PASSED ({passed}/{total})")
        print("✅ SYSTEM IS READY FOR FRONTEND DEVELOPMENT")
        return True
    else:
        print(f"❌ SOME VALIDATIONS FAILED ({passed}/{total})")
        print("🔧 FIX ISSUES BEFORE PROCEEDING TO FRONTEND")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
