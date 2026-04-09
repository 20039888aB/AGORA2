from rest_framework import permissions
from .models import CertificateTemplate, Certificate, CertificateBatch


class IsTemplateOwner(permissions.BasePermission):
    """
    Allows access only to template owner (organization admin)
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if isinstance(obj, CertificateTemplate):
            return obj.organization == request.user.organization and request.user.is_admin_or_above()
        
        return False


class CanManageTemplate(permissions.BasePermission):
    """
    Allows access only to users who can manage templates
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if not isinstance(obj, CertificateTemplate):
            return False
        
        # Superadmin can manage all templates
        if request.user.is_superadmin():
            return True
        
        # Admin can manage templates in their organization
        if request.user.is_admin() and obj.organization == request.user.organization:
            return True
        
        return False


class IsCertificateOwner(permissions.BasePermission):
    """
    Allows access only to certificate owner
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if isinstance(obj, Certificate):
            return obj.user == request.user
        
        return False


class CanManageCertificate(permissions.BasePermission):
    """
    Allows access only to users who can manage certificates
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if not isinstance(obj, Certificate):
            return False
        
        # Superadmin can manage all certificates
        if request.user.is_superadmin():
            return True
        
        # Admin can manage certificates in their organization
        if request.user.is_admin() and obj.template.organization == request.user.organization:
            return True
        
        # Certificate owner can manage their own certificate
        if obj.user == request.user:
            return True
        
        return False


class CanViewCertificate(permissions.BasePermission):
    """
    Allows access to view certificate details
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if not isinstance(obj, Certificate):
            return False
        
        # Superadmin can view all certificates
        if request.user.is_superadmin():
            return True
        
        # Admin can view certificates in their organization
        if request.user.is_admin() and obj.template.organization == request.user.organization:
            return True
        
        # Certificate owner can view their own certificate
        if obj.user == request.user:
            return True
        
        return False


class CanVerifyCertificate(permissions.BasePermission):
    """
    Allows access to verify certificates
    """
    
    def has_permission(self, request, view):
        # Anyone can verify certificates
        return True


class IsBatchOwner(permissions.BasePermission):
    """
    Allows access only to batch owner (organization admin)
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if isinstance(obj, CertificateBatch):
            return obj.organization == request.user.organization and request.user.is_admin_or_above()
        
        return False


class CanManageBatch(permissions.BasePermission):
    """
    Allows access only to users who can manage batches
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if not isinstance(obj, CertificateBatch):
            return False
        
        # Superadmin can manage all batches
        if request.user.is_superadmin():
            return True
        
        # Admin can manage batches in their organization
        if request.user.is_admin() and obj.organization == request.user.organization:
            return True
        
        return False


class CanViewBatch(permissions.BasePermission):
    """
    Allows access to view batch details
    """
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if not isinstance(obj, CertificateBatch):
            return False
        
        # Superadmin can view all batches
        if request.user.is_superadmin():
            return True
        
        # Admin can view batches in their organization
        if request.user.is_admin() and obj.organization == request.user.organization:
            return True
        
        return False


class CanViewCertificateStatistics(permissions.BasePermission):
    """
    Allows access only to users who can view certificate statistics
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Superadmin can view all statistics
        if request.user.is_superadmin():
            return True
        
        # Admin can view organization statistics
        if request.user.is_admin():
            return True
        
        return False


class CanIssueCertificate(permissions.BasePermission):
    """
    Allows access only to users who can issue certificates
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Superadmin can issue certificates
        if request.user.is_superadmin():
            return True
        
        # Admin can issue certificates in their organization
        if request.user.is_admin():
            return True
        
        return False


class CanCreateBatch(permissions.BasePermission):
    """
    Allows access only to users who can create batches
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Superadmin can create batches
        if request.user.is_superadmin():
            return True
        
        # Admin can create batches in their organization
        if request.user.is_admin():
            return True
        
        return False
