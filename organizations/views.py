from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg

from .models import Organization, Department, Team, DepartmentMembership, TeamMembership
from .serializers import (
    OrganizationSerializer, OrganizationCreateSerializer, DepartmentSerializer,
    DepartmentCreateSerializer, TeamSerializer, TeamCreateSerializer,
    DepartmentMembershipSerializer, TeamMembershipSerializer,
    TeamMemberAddSerializer
)
from .permissions import (
    IsOrganizationAdmin, IsOrganizationMember, CanManageDepartment,
    CanManageTeam, IsDepartmentMember, IsTeamMember,
    OrganizationBasedPermission
)
from .services import OrganizationService, DepartmentService, TeamService


class OrganizationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Organization model with multi-tenant access control
    """
    queryset = Organization.objects.filter(is_active=True)
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['subscription_tier', 'is_active']
    search_fields = ['name', 'description', 'email']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        """Filter organizations based on user role"""
        user = self.request.user
        
        if user.is_superadmin():
            return self.queryset
        
        elif user.is_admin():
            return self.queryset.filter(id=user.organization.id)
        
        return self.queryset.none()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return OrganizationCreateSerializer
        return OrganizationSerializer
    
    def get_permissions(self):
        """Return permissions based on action"""
        if self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]  # Anyone authenticated can create
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsOrganizationAdmin]
        else:
            permission_classes = [IsOrganizationMember]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=True, methods=['post'], permission_classes=[IsOrganizationAdmin])
    def upgrade_subscription(self, request, pk=None):
        """Upgrade organization subscription"""
        organization = self.get_object()
        new_tier = request.data.get('subscription_tier')
        
        if not new_tier:
            return Response(
                {'error': 'Subscription tier is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            OrganizationService.upgrade_subscription(organization, new_tier, request.user)
            return Response({
                'message': 'Subscription upgraded successfully',
                'organization': OrganizationSerializer(organization).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'], permission_classes=[IsOrganizationAdmin])
    def statistics(self, request, pk=None):
        """Get organization statistics"""
        organization = self.get_object()
        stats = OrganizationService.get_organization_statistics(organization)
        
        return Response(stats)
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_organizations(self, request):
        """Get organizations accessible to current user"""
        user = request.user
        
        if user.is_superadmin():
            orgs = Organization.objects.all()
        elif user.is_admin():
            orgs = Organization.objects.filter(id=user.organization.id)
        else:
            orgs = Organization.objects.none()
        
        serializer = self.get_serializer(orgs, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsOrganizationAdmin])
    def toggle_status(self, request, pk=None):
        """Toggle organization active/inactive status"""
        organization = self.get_object()
        is_active = request.data.get('is_active', True)
        
        try:
            organization.is_active = is_active
            organization.save()
            
            action = 'activated' if is_active else 'suspended'
            return Response({
                'success': True,
                'message': f'Organization {organization.name} has been {action}',
                'is_active': organization.is_active
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error updating organization: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['delete'], permission_classes=[IsOrganizationAdmin])
    def delete(self, request, pk=None):
        """Delete an organization (soft delete)"""
        organization = self.get_object()
        
        try:
            # Soft delete by marking as inactive
            organization.is_active = False
            organization.save()
            
            return Response({
                'success': True,
                'message': f'Organization {organization.name} has been deleted successfully'
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error deleting organization: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


class DepartmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Department model with hierarchical access control
    """
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['organization', 'parent', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['organization', 'name']
    
    def get_queryset(self):
        """Filter departments based on user role and organization"""
        user = self.request.user
        
        if user.is_superadmin():
            return Department.objects.filter(is_active=True)
        
        elif user.is_admin():
            return Department.objects.filter(
                is_active=True,
                organization=user.organization
            )
        
        elif user.is_manager():
            return Department.objects.filter(
                is_active=True,
                organization=user.organization,
                id__in=user.profile.department.get_descendants(include_self=True) if user.profile.department else []
            )
        
        return Department.objects.none()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return DepartmentCreateSerializer
        return DepartmentSerializer
    
    def get_permissions(self):
        """Return permissions based on action"""
        if self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]  # Anyone authenticated can create
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [CanManageDepartment]
        else:
            permission_classes = [IsDepartmentMember]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageDepartment])
    def assign_head(self, request, pk=None):
        """Assign department head"""
        department = self.get_object()
        new_head_id = request.data.get('head')
        
        if not new_head_id:
            return Response(
                {'error': 'Head ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from accounts.models import User
            new_head = User.objects.active().get(id=new_head_id)
            DepartmentService.assign_head(department, new_head, request.user)
            
            return Response({
                'message': 'Department head assigned successfully',
                'department': DepartmentSerializer(department).data
            })
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageDepartment])
    def move_department(self, request, pk=None):
        """Move department in hierarchy"""
        department = self.get_object()
        new_parent_id = request.data.get('parent')
        
        if new_parent_id is None:
            return Response(
                {'error': 'Parent ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            if new_parent_id == 'root':
                new_parent = None
            else:
                new_parent = Department.objects.get(id=new_parent_id)
            
            DepartmentService.move_department(department, new_parent, request.user)
            
            return Response({
                'message': 'Department moved successfully',
                'department': DepartmentSerializer(department).data
            })
        except Department.DoesNotExist:
            return Response(
                {'error': 'Parent department not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'], permission_classes=[CanManageDepartment])
    def hierarchy(self, request, pk=None):
        """Get department hierarchy"""
        department = self.get_object()
        hierarchy = DepartmentService.get_department_hierarchy(department)
        
        return Response(hierarchy)


class TeamViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Team model with department-level access control
    """
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['organization', 'department', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['organization', 'department', 'name']
    
    def get_queryset(self):
        """Filter teams based on user role and organization"""
        user = self.request.user
        
        if user.is_superadmin():
            return Team.objects.filter(is_active=True)
        
        elif user.is_admin():
            return Team.objects.filter(
                is_active=True,
                organization=user.organization
            )
        
        elif user.is_manager():
            return Team.objects.filter(
                is_active=True,
                organization=user.organization,
                department=user.profile.department
            )
        
        return Team.objects.none()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return TeamCreateSerializer
        return TeamSerializer
    
    def get_permissions(self):
        """Return permissions based on action"""
        if self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]  # Anyone authenticated can create
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [CanManageTeam]
        else:
            permission_classes = [IsTeamMember]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageTeam])
    def assign_lead(self, request, pk=None):
        """Assign team lead"""
        team = self.get_object()
        new_lead_id = request.data.get('lead')
        
        if not new_lead_id:
            return Response(
                {'error': 'Lead ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from accounts.models import User
            new_lead = User.objects.active().get(id=new_lead_id)
            TeamService.assign_lead(team, new_lead, request.user)
            
            return Response({
                'message': 'Team lead assigned successfully',
                'team': TeamSerializer(team).data
            })
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageTeam])
    def add_member(self, request, pk=None):
        """Add member to team"""
        team = self.get_object()
        serializer = TeamMemberAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            from accounts.models import User
            user = User.objects.active().get(id=serializer.validated_data['user_id'])
            membership = TeamService.add_team_member(
                team, user, 
                serializer.validated_data['role'],
                request.user
            )
            
            return Response({
                'message': 'Team member added successfully',
                'membership': TeamMembershipSerializer(membership).data
            })
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[CanManageTeam])
    def remove_member(self, request, pk=None):
        """Remove member from team"""
        team = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'User ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from accounts.models import User
            user = User.objects.active().get(id=user_id)
            TeamService.remove_team_member(team, user, request.user)
            
            return Response({
                'message': 'Team member removed successfully'
            })
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'], permission_classes=[CanManageTeam])
    def members(self, request, pk=None):
        """Get team members"""
        team = self.get_object()
        memberships = TeamMembership.objects.filter(team=team)
        
        return Response({
            'count': memberships.count(),
            'results': TeamMembershipSerializer(memberships, many=True).data
        })


class DepartmentMembershipViewSet(viewsets.ModelViewSet):
    """
    ViewSet for DepartmentMembership model
    """
    queryset = DepartmentMembership.objects.all()
    serializer_class = DepartmentMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['department', 'role']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    ordering = ['-joined_at']
    
    def get_queryset(self):
        """Filter memberships based on user role"""
        user = self.request.user
        
        if user.is_superadmin():
            return self.queryset
        
        elif user.is_admin():
            return self.queryset.filter(department__organization=user.organization)
        
        elif user.is_manager():
            return self.queryset.filter(
                department__in=user.profile.department.get_descendants(include_self=True) if user.profile.department else []
            )
        
        return self.queryset.filter(user=user)


class TeamMembershipViewSet(viewsets.ModelViewSet):
    """
    ViewSet for TeamMembership model
    """
    queryset = TeamMembership.objects.all()
    serializer_class = TeamMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['team', 'role']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    ordering = ['-joined_at']
    
    def get_queryset(self):
        """Filter memberships based on user role"""
        user = self.request.user
        
        if user.is_superadmin():
            return self.queryset
        
        elif user.is_admin():
            return self.queryset.filter(team__organization=user.organization)
        
        elif user.is_manager():
            return self.queryset.filter(
                team__department=user.profile.department
            )
        
        return self.queryset.filter(user=user)
