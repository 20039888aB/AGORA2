from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Permission, RolePermission, UserPermission, PermissionTemplate
from .serializers import (
    PermissionSerializer, RolePermissionSerializer, UserPermissionSerializer,
    PermissionTemplateSerializer, PermissionGrantSerializer, PermissionRevokeSerializer,
    PermissionTemplateApplySerializer, UserPermissionCheckSerializer
)
from .services import PermissionService


class PermissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Permission model
    """
    queryset = Permission.objects.filter(is_active=True)
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['resource_type', 'action_type', 'scope_type']
    search_fields = ['name', 'description', 'code']
    ordering_fields = ['resource_type', 'action_type', 'name']
    ordering = ['resource_type', 'action_type', 'name']
    
    def get_permissions(self):
        """Only superadmins can manage permissions"""
        if self.request.user.is_superadmin():
            return [permissions.IsAuthenticated]
        return [permissions.IsAdminUser]
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def create_permission(self, request):
        """Create new permission"""
        serializer = PermissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            permission = PermissionService.create_permission(
                serializer.validated_data,
                creator=request.user
            )
            return Response({
                'message': 'Permission created successfully',
                'permission': PermissionSerializer(permission).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class RolePermissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for RolePermission model
    """
    queryset = RolePermission.objects.filter(is_active=True)
    serializer_class = RolePermissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['role', 'is_active']
    search_fields = ['role', 'description']
    ordering_fields = ['role', 'created_at']
    ordering = ['role', 'created_at']
    
    def get_permissions(self):
        """Only superadmins can manage role permissions"""
        if self.request.user.is_superadmin():
            return [permissions.IsAuthenticated]
        return [permissions.IsAdminUser]
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def create_role_permission(self, request):
        """Create role-based permission"""
        serializer = RolePermissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            role_permission = PermissionService.create_role_permission(
                serializer.validated_data,
                creator=request.user
            )
            return Response({
                'message': 'Role permission created successfully',
                'role_permission': RolePermissionSerializer(role_permission).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class UserPermissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for UserPermission model
    """
    queryset = UserPermission.objects.filter(is_active=True)
    serializer_class = UserPermissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user', 'permission', 'is_active']
    search_fields = ['user__email', 'permission__name']
    ordering_fields = ['granted_at', 'expires_at']
    ordering = ['-granted_at']
    
    def get_queryset(self):
        """Filter based on user role"""
        user = self.request.user
        
        if user.is_superadmin():
            return self.queryset
        
        # Admin can see permissions for their organization
        elif user.is_admin():
            return self.queryset.filter(
                user__organization=user.organization
            )
        
        # Manager can see permissions for their team
        elif user.is_manager():
            return self.queryset.filter(
                user__profile__team=user.profile.team
            )
        
        # Users can see only their own permissions
        else:
            return self.queryset.filter(user=user)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def grant_permission(self, request):
        """Grant permission to user"""
        serializer = PermissionGrantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            from accounts.models import User
            target_user = User.objects.active().get(id=serializer.validated_data['user_id'])
            permission = Permission.objects.get(id=serializer.validated_data['permission_id'])
            
            PermissionService.grant_user_permission(
                user=target_user,
                permission=permission,
                scope_object_id=serializer.validated_data.get('scope_object_id'),
                scope_object_type=serializer.validated_data.get('scope_object_type'),
                granted_by=request.user
            )
            
            return Response({
                'message': 'Permission granted successfully',
                'user_permission': UserPermissionSerializer(
                    UserPermission.objects.filter(
                        user=target_user,
                        permission=permission,
                        is_active=True
                    ).first()
                ).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def revoke_permission(self, request, pk=None):
        """Revoke user permission"""
        user_permission = self.get_object()
        
        try:
            PermissionService.revoke_user_permission(user_permission, revoked_by=request.user)
            return Response({
                'message': 'Permission revoked successfully'
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def check_permissions(self, request):
        """Check user permissions"""
        serializer = UserPermissionCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            from accounts.models import User
            user = User.objects.active().get(id=request.user.id)
            
            has_permission = PermissionService.check_user_permission(
                user=user,
                resource_type=serializer.validated_data.get('resource_type'),
                action_type=serializer.validated_data.get('action_type'),
                scope_object_id=serializer.validated_data.get('scope_object_id'),
                scope_object_type=serializer.validated_data.get('scope_object_type')
            )
            
            return Response({
                'has_permission': has_permission,
                'resource_type': serializer.validated_data.get('resource_type'),
                'action_type': serializer.validated_data.get('action_type'),
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_permissions(self, request):
        """Get current user's permissions"""
        from accounts.models import User
        user = User.objects.active().get(id=request.user.id)
        permissions = PermissionService.get_user_permissions(user)
        
        return Response({
            'count': len(permissions),
            'results': permissions
        })


class PermissionTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for PermissionTemplate model
    """
    queryset = PermissionTemplate.objects.filter(is_active=True)
    serializer_class = PermissionTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['resource_type', 'action_type']
    search_fields = ['name', 'description', 'code']
    ordering_fields = ['resource_type', 'action_type', 'name']
    ordering = ['resource_type', 'action_type', 'name']
    
    def get_permissions(self):
        """Only superadmins can manage permission templates"""
        if self.request.user.is_superadmin():
            return [permissions.IsAuthenticated]
        return [permissions.IsAdminUser]
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def create_template(self, request):
        """Create permission template"""
        serializer = PermissionTemplateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            template = PermissionService.create_permission_template(
                serializer.validated_data,
                creator=request.user
            )
            return Response({
                'message': 'Permission template created successfully',
                'template': PermissionTemplateSerializer(template).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def apply_template(self, request, pk=None):
        """Apply permission template to users"""
        template = self.get_object()
        serializer = PermissionTemplateApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            from accounts.models import User
            users = User.objects.active().filter(id__in=serializer.validated_data['user_ids'])
            
            permissions_created = PermissionService.apply_permission_template(
                template=template,
                users=users,
                granted_by=request.user
            )
            
            return Response({
                'message': 'Permission template applied successfully',
                'permissions_created': len(permissions_created),
                'template_id': str(template.id)
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def cleanup_expired(self, request):
        """Clean up expired permissions"""
        try:
            count = PermissionService.cleanup_expired_permissions()
            return Response({
                'message': f'Cleaned up {count} expired permissions',
                'count': count
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
