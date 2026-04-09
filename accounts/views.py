from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.contrib import messages
from django.urls import reverse
from django_filters.rest_framework import DjangoFilterBackend
from django.http import JsonResponse
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
import logging

from .models import User, RoleRequest
from .serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer,
    RoleRequestSerializer, RoleRequestCreateSerializer, RoleRequestActionSerializer,
    LoginSerializer, PasswordChangeSerializer, UserStatisticsSerializer
)
from .permissions import (
    IsSuperAdmin, IsAdmin, IsAdminOrAbove, IsManager, IsManagerOrAbove,
    IsOwnerOrReadOnly, CanManageUser, CanAccessUserData, IsSameOrganization,
    RoleBasedPermission
)
from .services import UserService, RoleRequestService
from .forms import SignUpForm, LoginForm, ProfileEditForm

logger = logging.getLogger(__name__)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for User model with role-based access control
    """
    queryset = User.objects.filter(is_deleted=False)
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['role', 'organization', 'managed_by']
    search_fields = ['email', 'first_name', 'last_name']
    ordering_fields = ['created_at', 'last_active_at', 'email']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Filter queryset based on user role and permissions
        """
        user = self.request.user
        if not user.is_authenticated:
            return User.objects.none()
        
        return user.get_accessible_users_queryset()
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action
        """
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer
    
    def get_permissions(self):
        """
        Return permissions based on action
        """
        if self.action == 'create':
            permission_classes = [IsAdminOrAbove]  # Only admins can create users
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [CanManageUser]  # Only managers can manage users
        elif self.action == 'retrieve':
            permission_classes = [CanAccessUserData]  # Can access based on hierarchy
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def perform_destroy(self, instance):
        """
        Soft delete user instead of hard delete
        """
        instance.soft_delete()
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def login(self, request):
        """
        User login endpoint
        """
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        user.increment_login_count()
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        })
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def logout(self, request):
        """
        User logout endpoint
        """
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'message': 'Successfully logged out'})
        except Exception:
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def change_password(self, request):
        """
        Change user password
        """
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({'message': 'Password changed successfully'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrAbove])
    def update_role(self, request, pk=None):
        """
        Update user role (admin/manager only)
        """
        user = self.get_object()
        new_role = request.data.get('role')
        
        if not new_role:
            return Response(
                {'error': 'Role is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            updated_user = UserService.update_user_role(user, new_role, request.user)
            return Response({
                'message': 'Role updated successfully',
                'user': UserSerializer(updated_user).data
            })
        except PermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def statistics(self, request):
        """
        Get user statistics based on role
        """
        user = request.user
        stats = UserService.get_user_statistics(user)
        
        serializer = UserStatisticsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAdminOrAbove])
    def bulk_activate(self, request):
        """
        Bulk activate users
        """
        user_ids = request.data.get('user_ids', [])
        count = User.objects.filter(
            id__in=user_ids,
            is_deleted=False
        ).update(is_active=True)
        
        return Response({
            'message': f'Activated {count} users',
            'count': count
        })
    
    @action(detail=False, methods=['post'], permission_classes=[IsAdminOrAbove])
    def bulk_deactivate(self, request):
        """
        Bulk deactivate users
        """
        user_ids = request.data.get('user_ids', [])
        count = User.objects.filter(
            id__in=user_ids,
            is_deleted=False
        ).update(is_active=False)
        
        return Response({
            'message': f'Deactivated {count} users',
            'count': count
        })


class RoleRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for RoleRequest model
    """
    queryset = RoleRequest.objects.all()
    serializer_class = RoleRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'requested_role', 'user']
    search_fields = ['user__email', 'reason']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Filter queryset based on user role
        """
        user = self.request.user
        if not user.is_authenticated:
            return RoleRequest.objects.none()
        
        if user.is_superadmin():
            return RoleRequest.objects.all()
        
        return RoleRequestService.get_pending_requests(user)
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action
        """
        if self.action == 'create':
            return RoleRequestCreateSerializer
        return RoleRequestSerializer
    
    def get_permissions(self):
        """
        Return permissions based on action
        """
        if self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['approve', 'reject']:
            permission_classes = [IsAdminOrAbove]  # Only admins can approve/reject
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrAbove])
    def approve(self, request, pk=None):
        """
        Approve role request
        """
        role_request = self.get_object()
        serializer = RoleRequestActionSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        if serializer.validated_data['action'] != 'approve':
            return Response(
                {'error': 'Invalid action for this endpoint'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            RoleRequestService.approve_role_request(
                role_request, reviewer=request.user,
                comments=serializer.validated_data.get('comments', '')
            )
            return Response({
                'message': 'Role request approved',
                'role_request': RoleRequestSerializer(role_request).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrAbove])
    def reject(self, request, pk=None):
        """
        Reject role request
        """
        role_request = self.get_object()
        serializer = RoleRequestActionSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        if serializer.validated_data['action'] != 'reject':
            return Response(
                {'error': 'Invalid action for this endpoint'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            RoleRequestService.reject_role_request(
                role_request, reviewer=request.user,
                comments=serializer.validated_data.get('comments', '')
            )
            return Response({
                'message': 'Role request rejected',
                'role_request': RoleRequestSerializer(role_request).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'], permission_classes=[IsAdminOrAbove])
    def bulk_approve(self, request):
        """
        Bulk approve role requests
        """
        request_ids = request.data.get('request_ids', [])
        approved_count = RoleRequestService.bulk_approve_requests(
            request_ids, request.user,
            comments=request.data.get('comments', '')
        )
        
        return Response({
            'message': f'Approved {approved_count} role requests',
            'count': approved_count
        })


class LoginView(TemplateView):
    """
    Custom login view that handles GET parameters
    """
    template_name = 'auth/login.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['session_expired'] = self.request.GET.get('session_expired') == 'true'
        context['logout_success'] = self.request.GET.get('logout') == 'success'
        context['form'] = LoginForm()
        return context
    
    def post(self, request, *args, **kwargs):
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.user
            login(request, user)
            
            # Redirect to dashboard or intended URL
            next_url = request.GET.get('next', reverse('dashboard'))
            return redirect(next_url)
        else:
            context = self.get_context_data(**kwargs)
            context['form'] = form
            return self.render_to_response(context)


def login_view(request):
    """
    User login view
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        from django.contrib.auth import authenticate
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            from django.contrib.auth import login
            login(request, user)
            
            # Update last login
            user.last_active_at = timezone.now()
            user.login_count += 1
            user.save(update_fields=['last_active_at', 'login_count'])
            
            messages.success(request, f'Welcome back, {user.first_name}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid email or password.')
    
    return render(request, 'auth/login.html')


def signup_view(request):
    """
    User signup view
    """
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=True)  # Role is set in form's save method
            
            # Log user in automatically
            login(request, user)
            
            messages.success(request, 'Account created successfully! Welcome to AgoraProf.')
            return redirect('dashboard')
        else:
            # Pass form errors to template
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SignUpForm()
    
    return render(request, 'auth/signup.html', {'form': form})


@login_required
def dashboard_view(request):
    """
    Main dashboard view that redirects to role-specific dashboard
    """
    user = request.user
    
    # Redirect to appropriate dashboard based on role
    if user.is_superadmin():
        return redirect('superadmin_dashboard')
    elif user.is_admin():
        return redirect('admin_dashboard')
    elif user.is_manager():
        return redirect('manager_dashboard')
    elif user.is_student():
        return redirect('student_dashboard')
    else:
        # Fallback to generic dashboard
        return render(request, 'dashboard.html', {'user': user})


def logout_view(request):
    """
    User logout view
    """
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_stats(request):
    """
    API endpoint to get dashboard statistics
    """
    user = request.user
    
    # Get basic stats
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    total_organizations = User.objects.values('organization').exclude(organization=None).distinct().count()
    
    # Get user-specific stats from actual models
    try:
        from courses.models import Course, Enrollment
        from certificates.models import Certificate
        from assignments.models import Assignment, AssignmentSubmission
        
        # User's actual stats
        user_enrollments = Enrollment.objects.filter(user=user).count()
        user_certificates = Certificate.objects.filter(user=user).count()
        user_assignments = AssignmentSubmission.objects.filter(student=user).values('assignment_id').distinct().count()
        
        # Get role distribution
        role_stats = User.objects.values('role').annotate(count=Count('id'))
        
        # Organization-specific stats for non-superadmins
        if user.role != 'SUPERADMIN' and user.organization:
            org_users = User.objects.filter(organization=user.organization).count()
            org_courses = Course.objects.filter(organization=user.organization).count()
        else:
            org_users = total_users
            org_courses = Course.objects.count()
        
    except ImportError:
        # Fallback if models don't exist yet
        user_enrollments = 0
        user_certificates = 0
        user_assignments = 0
        org_users = total_users
        org_courses = 0
        role_stats = User.objects.values('role').annotate(count=Count('id'))
    
    stats = {
        'total_users': total_users,
        'active_users': active_users,
        'total_organizations': total_organizations,
        'user_stats': {
            'enrollments': user_enrollments,
            'certificates': user_certificates,
            'assignments': user_assignments,
        },
        'organization_stats': {
            'users': org_users,
            'courses': org_courses,
        },
        'role_distribution': list(role_stats),
        'user_role': user.role,
        'user_organization': user.organization.name if user.organization else None,
    }
    
    return Response(stats)


@login_required
def superadmin_dashboard(request):
    """
    SuperAdmin dashboard with system-wide metrics
    """
    if not request.user.is_superadmin():
        return redirect('dashboard')  # Redirect to appropriate dashboard
    
    # Get real organization data
    try:
        from organizations.models import Organization
        organizations = Organization.objects.all()
        
        # Calculate organization statistics
        total_organizations = organizations.count()
        active_organizations = organizations.filter(is_active=True).count()
        inactive_organizations = organizations.filter(is_active=False).count()
        
        # Get organization details for dashboard
        org_details = []
        for org in organizations.order_by('-created_at')[:5]:  # Recent 5 organizations
            user_count = User.objects.filter(organization=org).count()
            active_user_count = User.objects.filter(organization=org, is_active=True).count()
            
            # Get course count if available
            course_count = 0
            try:
                from courses.models import Course
                course_count = Course.objects.filter(organization=org).count()
            except ImportError:
                pass
            
            org_details.append({
                'id': org.id,
                'name': org.name,
                'email': org.email,
                'subscription_tier': org.subscription_tier,
                'is_active': org.is_active,
                'created_at': org.created_at,
                'user_count': user_count,
                'active_user_count': active_user_count,
                'course_count': course_count,
            })
    except ImportError:
        organizations = []
        total_organizations = 0
        active_organizations = 0
        inactive_organizations = 0
        org_details = []
    
    # Get system-wide stats with real-time data
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    
    # Get real course, enrollment, and certificate statistics
    total_courses = 0
    total_enrollments = 0
    total_certificates = 0
    completed_courses = 0
    pending_enrollments = 0
    completed_today = 0
    completion_rate = 0
    top_performer_name = '-'
    
    try:
        from courses.models import Course
        from enrollments.models import Enrollment
        from certificates.models import Certificate
        from django.utils import timezone
        from datetime import timedelta
        
        total_courses = Course.objects.count()
        total_enrollments = Enrollment.objects.count()
        total_certificates = Certificate.objects.count()
        completed_courses = Enrollment.objects.filter(status='COMPLETED').count()
        
        if total_enrollments > 0:
            completion_rate = round((completed_courses / total_enrollments) * 100, 1)
        
        # Calculate growth percentages
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        new_users = User.objects.filter(date_joined__gte=thirty_days_ago).count()
        user_growth = round((new_users / max(total_users, 1)) * 100, 1) if total_users > 0 else 0
        
        new_courses = Course.objects.filter(created_at__gte=thirty_days_ago).count()
        course_growth = round((new_courses / max(total_courses, 1)) * 100, 1) if total_courses > 0 else 0
        
        new_enrollments = Enrollment.objects.filter(created_at__gte=thirty_days_ago).count()
        enrollment_growth = round((new_enrollments / max(total_enrollments, 1)) * 100, 1) if total_enrollments > 0 else 0
        
        new_certificates = Certificate.objects.filter(created_at__gte=thirty_days_ago).count()
        certificate_growth = round((new_certificates / max(total_certificates, 1)) * 100, 1) if total_certificates > 0 else 0
        
        completed_recent = Enrollment.objects.filter(status='COMPLETED', updated_at__gte=thirty_days_ago).count()
        completion_growth = round((completed_recent / max(completed_courses, 1)) * 100, 1) if completed_courses > 0 else 0
        
    except ImportError:
        # Fallback growth values
        user_growth = 0
        course_growth = 0
        enrollment_growth = 0
        certificate_growth = 0
        completion_growth = 0
    
    # Role distribution
    role_stats = User.objects.values('role').annotate(count=Count('id'))
    
    # Recent activity
    recent_users = User.objects.order_by('-created_at')[:10]
    
    context = {
        'user': request.user,
        'total_organizations': total_organizations,
        'active_organizations': active_organizations,
        'inactive_organizations': inactive_organizations,
        'total_users': total_users,
        'active_users': active_users,
        'total_courses': total_courses,
        'total_enrollments': total_enrollments,
        'total_certificates': total_certificates,
        'completed_courses': completed_courses,
        'certificates_issued': total_certificates,
        'user_growth': user_growth,
        'course_growth': course_growth,
        'enrollment_growth': enrollment_growth,
        'certificate_growth': certificate_growth,
        'completion_growth': completion_growth,
        'role_stats': role_stats,
        'recent_users': recent_users,
        'organizations': org_details,  # Add organization details to context
    }
    
    return render(request, 'dashboard/superadmin.html', context)


@login_required
def admin_dashboard(request):
    """
    Admin dashboard with organization-specific metrics
    """
    if not request.user.is_manager_or_above():
        return redirect('dashboard')  # Redirect to appropriate dashboard
    
    if not request.user.organization:
        messages.error(request, 'You must belong to an organization to access this dashboard.')
        return redirect('dashboard')
    
    org = request.user.organization
    
    # Organization-specific stats with real-time data
    org_users = User.objects.filter(organization=org).count()
    org_active_users = User.objects.filter(organization=org, is_active=True).count()
    
    # Get real course, enrollment, and certificate statistics for this organization
    total_courses = 0
    total_enrollments = 0
    total_certificates = 0
    completed_courses = 0
    
    try:
        from courses.models import Course
        from enrollments.models import Enrollment
        from certificates.models import Certificate
        from django.utils import timezone
        from datetime import timedelta
        
        total_courses = Course.objects.filter(organization=org).count()
        total_enrollments = Enrollment.objects.filter(course__organization=org).count()
        total_certificates = Certificate.objects.filter(course__organization=org).count()
        completed_courses = Enrollment.objects.filter(course__organization=org, status='COMPLETED').count()
        
        if total_enrollments > 0:
            completion_rate = round((completed_courses / total_enrollments) * 100, 1)
        else:
            completion_rate = 0
        
        # Calculate growth percentages
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        new_users = User.objects.filter(organization=org, date_joined__gte=thirty_days_ago).count()
        user_growth = round((new_users / max(org_users, 1)) * 100, 1) if org_users > 0 else 0
        
        new_courses = Course.objects.filter(organization=org, created_at__gte=thirty_days_ago).count()
        course_growth = round((new_courses / max(total_courses, 1)) * 100, 1) if total_courses > 0 else 0
        
        new_enrollments = Enrollment.objects.filter(course__organization=org, created_at__gte=thirty_days_ago).count()
        enrollment_growth = round((new_enrollments / max(total_enrollments, 1)) * 100, 1) if total_enrollments > 0 else 0
        
        new_certificates = Certificate.objects.filter(course__organization=org, created_at__gte=thirty_days_ago).count()
        certificate_growth = round((new_certificates / max(total_certificates, 1)) * 100, 1) if total_certificates > 0 else 0
        
        completed_recent = Enrollment.objects.filter(course__organization=org, status='COMPLETED', updated_at__gte=thirty_days_ago).count()
        completion_growth = round((completed_recent / max(completed_courses, 1)) * 100, 1) if completed_courses > 0 else 0
        
    except ImportError:
        # Fallback growth values
        user_growth = 0
        course_growth = 0
        enrollment_growth = 0
        certificate_growth = 0
        completion_growth = 0
        completion_rate = 0
    
    # Department stats using existing Department model
    try:
        from organizations.models import Department
        org_departments = Department.objects.filter(organization=org).count()
        
        # Get team count through Team model
        from organizations.models import Team
        org_teams = Team.objects.filter(organization=org).count()
    except ImportError:
        org_departments = 0
        org_teams = 0
    
    # Recent organization users
    recent_org_users = User.objects.filter(organization=org).order_by('-created_at')[:10]
    
    context = {
        'user': request.user,
        'organization': org,
        'total_users': org_users,  # Alias for template compatibility
        'org_users': org_users,
        'org_active_users': org_active_users,
        'total_courses': total_courses,
        'org_courses': total_courses,
        'total_enrollments': total_enrollments,
        'total_certificates': total_certificates,
        'completed_courses': completed_courses,
        'certificates_issued': total_certificates,
        'user_growth': user_growth,
        'course_growth': course_growth,
        'enrollment_growth': enrollment_growth,
        'certificate_growth': certificate_growth,
        'completion_growth': completion_growth,
        'completion_rate': completion_rate,
        'org_departments': org_departments,
        'org_teams': org_teams,
        'recent_org_users': recent_org_users,
    }
    
    return render(request, 'dashboard/admin.html', context)


@login_required
def manager_dashboard(request):
    """
    Enhanced manager dashboard with team-specific metrics and course visibility
    """
    if not request.user.is_manager_or_above():
        return redirect('dashboard')  # Redirect to appropriate dashboard
    
    # Get team members with real-time statistics
    team_members = User.objects.filter(managed_by=request.user).order_by('-last_active_at')
    
    # Team stats
    total_team_members = team_members.count()
    active_team_members = team_members.filter(is_active=True).count()
    
    # Get real course, enrollment, and certificate statistics for team members
    total_courses = 0
    total_enrollments = 0
    total_certificates = 0
    completed_courses = 0
    
    # Initialize growth variables
    user_growth = 0
    enrollment_growth = 0
    certificate_growth = 0
    completion_growth = 0
    
    # Get organization courses for visibility
    organization_courses = []
    try:
        from courses.models import Course
        from enrollments.models import Enrollment
        from certificates.models import Certificate
        from django.utils import timezone
        from datetime import timedelta
        
        # Get all visible courses for the organization with documents
        if request.user.organization:
            organization_courses = Course.objects.prefetch_related('documents').filter(
                organization=request.user.organization,
                is_active=True
            ).order_by('-created_at')
            
            total_courses = organization_courses.count()
        
        # Get courses for team members' enrollments
        team_user_ids = team_members.values_list('id', flat=True)
        total_enrollments = Enrollment.objects.filter(user_id__in=team_user_ids).count()
        completed_courses = Enrollment.objects.filter(user_id__in=team_user_ids, status='COMPLETED').count()
        pending_enrollments = Enrollment.objects.filter(
            user_id__in=team_user_ids,
            status__in=['PENDING', 'ACTIVE', 'SUSPENDED']
        ).count()
        total_certificates = Certificate.objects.filter(user_id__in=team_user_ids).count()

        if total_enrollments > 0:
            completion_rate = round((completed_courses / total_enrollments) * 100, 1)
        else:
            completion_rate = 0

        completed_today = Enrollment.objects.filter(
            user_id__in=team_user_ids,
            status='COMPLETED',
            completion_date__date=timezone.now().date()
        ).count()

        top_performer_name = '-'
        top_performer = team_members.annotate(
            completed_count=Count('enrollments', filter=Q(enrollments__status='COMPLETED'))
        ).order_by('-completed_count', 'first_name').first()
        if top_performer and top_performer.completed_count > 0:
            top_performer_name = top_performer.get_full_name() or top_performer.email
        
        # Calculate growth percentages
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        new_team_members = team_members.filter(date_joined__gte=thirty_days_ago).count()
        user_growth = round((new_team_members / max(total_team_members, 1)) * 100, 1) if total_team_members > 0 else 0
        
        new_enrollments = Enrollment.objects.filter(
            user_id__in=team_user_ids, 
            created_at__gte=thirty_days_ago
        ).count()
        enrollment_growth = round((new_enrollments / max(total_enrollments, 1)) * 100, 1) if total_enrollments > 0 else 0
        
        new_certificates = Certificate.objects.filter(
            user_id__in=team_user_ids, 
            created_at__gte=thirty_days_ago
        ).count()
        certificate_growth = round((new_certificates / max(total_certificates, 1)) * 100, 1) if total_certificates > 0 else 0
        
        completed_recent = Enrollment.objects.filter(
            user_id__in=team_user_ids, 
            status='COMPLETED', 
            updated_at__gte=thirty_days_ago
        ).count()
        completion_growth = round((completed_recent / max(completed_courses, 1)) * 100, 1) if completed_courses > 0 else 0
        
    except ImportError:
        # Fallback growth values
        user_growth = 0
        enrollment_growth = 0
        certificate_growth = 0
        completion_growth = 0
    
    # Department info if available (through DepartmentMembership)
    department_info = None
    try:
        from organizations.models import DepartmentMembership
        dept_membership = DepartmentMembership.objects.filter(
            user=request.user,
            role='LEAD'
        ).first()
        
        if dept_membership:
            department_info = {
                'name': dept_membership.department.name,
                'total_employees': dept_membership.department.total_users,
                'total_teams': dept_membership.department.total_subdepartments,
            }
    except ImportError:
        pass
    
    context = {
        'user': request.user,
        'team_members': team_members,
        'total_users': total_team_members,  # Alias for template compatibility
        'total_team_members': total_team_members,
        'active_team_members': active_team_members,
        'total_courses': total_courses,
        'total_enrollments': total_enrollments,
        'total_certificates': total_certificates,
        'completed_courses': completed_courses,
        'pending_enrollments': pending_enrollments,
        'completed_today': completed_today,
        'completion_rate': completion_rate,
        'top_performer_name': top_performer_name,
        'user_growth': user_growth,
        'enrollment_growth': enrollment_growth,
        'certificate_growth': certificate_growth,
        'completion_growth': completion_growth,
        'organization_courses': organization_courses,  # Add organization courses
        'department_info': department_info,
        'page_title': 'Manager Dashboard',
    }
    
    return render(request, 'dashboard/manager.html', context)


@login_required
def student_dashboard(request):
    """
    Student dashboard with learning-focused metrics
    """
    if not request.user.is_student():
        return redirect('dashboard')  # Redirect to appropriate dashboard
    
    # Get student's learning data with real-time statistics
    try:
        from courses.models import Course
        from enrollments.models import Enrollment
        from certificates.models import Certificate
        from assignments.models import Assignment, AssignmentSubmission
        from django.utils import timezone
        from datetime import timedelta
        
        # Student's enrollments
        enrollments = Enrollment.objects.filter(user=request.user).order_by('-created_at')
        total_enrollments = enrollments.count()
        active_enrollments = enrollments.filter(is_active=True).count()
        completed_courses = enrollments.filter(status='COMPLETED').count()
        
        # Certificates
        certificates = Certificate.objects.filter(user=request.user).order_by('-created_at')
        total_certificates = certificates.count()
        
        # Assignments available to the student from enrolled courses
        enrolled_course_ids = enrollments.values_list('course_id', flat=True)
        assignments = Assignment.objects.filter(
            course_id__in=enrolled_course_ids,
            is_active=True,
            is_published=True,
        ).order_by('-created_at').distinct()
        total_assignments = assignments.count()

        completed_assignments = AssignmentSubmission.objects.filter(
            student=request.user,
            assignment__in=assignments,
            status__in=['SUBMITTED', 'GRADED']
        ).values('assignment_id').distinct().count()
        certificates_this_month = certificates.filter(created_at__month=timezone.now().month, created_at__year=timezone.now().year).count()

        learning_hours = enrollments.aggregate(total=Sum('course__duration_hours'))['total'] or 0

        activity_days = set(
            enrollments.exclude(last_accessed_at__isnull=True)
            .values_list('last_accessed_at__date', flat=True)
        )
        day_streak = 0
        current_day = timezone.now().date()
        while current_day in activity_days:
            day_streak += 1
            current_day = current_day - timedelta(days=1)

        achievements = []
        if completed_courses > 0:
            achievements.append('First Course Completed')
        if day_streak >= 7:
            achievements.append('7-Day Learning Streak')
        if total_certificates >= 1:
            achievements.append('Certified Learner')
        if completed_assignments >= 1:
            achievements.append('Assignment Finisher')

        # Get available courses for enrollment (strictly organization-based)
        if request.user.organization:
            org_courses = Course.objects.prefetch_related('documents').filter(
                organization=request.user.organization
            )
            available_courses = org_courses.exclude(
                id__in=enrollments.values_list('course_id', flat=True)
            ).order_by('-created_at')
            logger.debug(
                "student_dashboard: user=%s organization_id=%s org_courses=%s available_courses=%s",
                request.user.id,
                request.user.organization_id,
                org_courses.count(),
                available_courses.count(),
            )
        else:
            available_courses = Course.objects.none()
            logger.debug(
                "student_dashboard: user=%s has no organization, available_courses=0",
                request.user.id,
            )

        recommended_courses = list(available_courses[:3])
        
        # Calculate growth percentages
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        new_enrollments = enrollments.filter(created_at__gte=thirty_days_ago).count()
        enrollment_growth = round((new_enrollments / max(total_enrollments, 1)) * 100, 1) if total_enrollments > 0 else 0
        
        new_certificates = certificates.filter(created_at__gte=thirty_days_ago).count()
        certificate_growth = round((new_certificates / max(total_certificates, 1)) * 100, 1) if total_certificates > 0 else 0
        
        new_assignments = assignments.filter(created_at__gte=thirty_days_ago).count()
        assignment_growth = round((new_assignments / max(total_assignments, 1)) * 100, 1) if total_assignments > 0 else 0
        
        completed_recent = AssignmentSubmission.objects.filter(
            student=request.user,
            assignment__in=assignments,
            status__in=['SUBMITTED', 'GRADED'],
            updated_at__gte=thirty_days_ago,
        ).values('assignment_id').distinct().count()
        completion_growth = round((completed_recent / max(completed_assignments, 1)) * 100, 1) if completed_assignments > 0 else 0
        
    except ImportError:
        enrollments = []
        total_enrollments = 0
        active_enrollments = 0
        completed_courses = 0
        certificates = []
        total_certificates = 0
        assignments = []
        total_assignments = 0
        completed_assignments = 0
        available_courses = []
        certificates_this_month = 0
        learning_hours = 0
        day_streak = 0
        achievements = []
        recommended_courses = []
        # Fallback growth values
        enrollment_growth = 0
        certificate_growth = 0
        assignment_growth = 0
        completion_growth = 0
    
    context = {
        'user': request.user,
        'enrollments': enrollments,
        'total_enrollments': total_enrollments,
        'active_enrollments': active_enrollments,
        'total_courses': completed_courses,  # For template compatibility
        'completed_courses': completed_courses,
        'certificates': certificates,
        'total_certificates': total_certificates,
        'certificates_issued': total_certificates,  # For template compatibility
        'assignments': assignments,
        'total_assignments': total_assignments,
        'completed_assignments': completed_assignments,
        'certificates_this_month': certificates_this_month,
        'learning_hours': learning_hours,
        'day_streak': day_streak,
        'achievements': achievements,
        'recommended_courses': recommended_courses,
        'enrollment_growth': enrollment_growth,
        'certificate_growth': certificate_growth,
        'assignment_growth': assignment_growth,
        'completion_growth': completion_growth,
        'available_courses': available_courses,
    }
    
    return render(request, 'dashboard/student.html', context)


# Profile Management Functions
@login_required
def profile_view(request):
    """
    User profile view with profile picture management
    """
    user = request.user
    
    # Check if viewing another user's profile
    user_id = request.GET.get('user_id')
    if user_id:
        # Only admins and above can view other users' profiles
        if not (user.is_admin_or_above()):
            messages.error(request, 'You do not have permission to view other users\' profiles.')
            return redirect('profile')
        
        try:
            from accounts.models import User
            profile_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
            return redirect('profile')
    else:
        profile_user = user
    
    total_enrollments = 0
    completed_courses = 0
    total_certificates = 0
    total_assignments = 0
    completed_assignments = 0

    try:
        from enrollments.models import Enrollment
        from certificates.models import Certificate
        from assignments.models import Assignment, AssignmentSubmission

        enrollments_qs = Enrollment.objects.filter(user=profile_user, is_active=True)
        total_enrollments = enrollments_qs.count()
        completed_courses = enrollments_qs.filter(status='COMPLETED').count()

        total_certificates = Certificate.objects.filter(user=profile_user).count()

        enrolled_ids = enrollments_qs.values_list('course_id', flat=True)
        assignments_qs = Assignment.objects.filter(
            course_id__in=enrolled_ids, is_active=True, is_published=True
        )
        total_assignments = assignments_qs.count()
        completed_assignments = AssignmentSubmission.objects.filter(
            student=profile_user,
            assignment__in=assignments_qs,
            status__in=['SUBMITTED', 'GRADED']
        ).values('assignment_id').distinct().count()
    except Exception:
        pass

    context = {
        'user': profile_user,
        'page_title': f'Profile - {profile_user.get_full_name()}',
        'total_enrollments': total_enrollments,
        'completed_courses': completed_courses,
        'total_certificates': total_certificates,
        'total_assignments': total_assignments,
        'completed_assignments': completed_assignments,
        'is_own_profile': profile_user == user,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_edit_view(request):
    """
    Profile edit view – allows all authenticated users to update their details.
    """
    user = request.user
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProfileEditForm(instance=user)

    context = {
        'user': user,
        'form': form,
        'page_title': 'Edit Profile',
    }
    return render(request, 'accounts/profile_edit.html', context)


@login_required
def upload_avatar(request):
    """
    Handle avatar upload via AJAX
    """
    if request.method == 'POST' and request.FILES.get('avatar'):
        avatar = request.FILES['avatar']
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if avatar.content_type not in allowed_types:
            return JsonResponse({
                'success': False,
                'error': 'Invalid file type. Please upload JPG, PNG, GIF, or WebP images.'
            }, status=400)
        
        # Validate file size (max 5MB)
        if avatar.size > 5 * 1024 * 1024:
            return JsonResponse({
                'success': False,
                'error': 'File too large. Maximum size is 5MB.'
            }, status=400)
        
        try:
            # Delete old avatar if exists
            if request.user.avatar:
                request.user.avatar.delete(save=False)
            
            # Save new avatar
            request.user.avatar = avatar
            request.user.save()

            # Build cache-busted URL so browsers don't serve stale 304
            raw_url = request.user.avatar.url if request.user.avatar else None
            if raw_url:
                import time as _time
                ts = int(request.user.updated_at.timestamp()) if request.user.updated_at else int(_time.time())
                avatar_url_busted = f'{raw_url}?v={ts}'
            else:
                avatar_url_busted = None

            return JsonResponse({
                'success': True,
                'avatar_url': avatar_url_busted,
                'message': 'Profile picture updated successfully!'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error uploading avatar: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    }, status=405)


@login_required
def remove_avatar(request):
    """
    Remove user's profile picture
    """
    if request.method == 'POST':
        try:
            if request.user.avatar:
                request.user.avatar.delete(save=False)
                request.user.avatar = None
                request.user.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Profile picture removed successfully!'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error removing avatar: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    }, status=405)


@login_required
def change_password(request):
    """
    Change user password
    """
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            messages.success(request, 'Password changed successfully!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(request.user)
    
    context = {
        'form': form,
        'page_title': 'Change Password',
    }
    return render(request, 'accounts/change_password.html', context)
