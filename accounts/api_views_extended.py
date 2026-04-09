from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from datetime import timedelta

from .models import User
from .permissions import IsSuperAdmin, IsAdmin, IsManager, IsAdminOrAbove, IsManagerOrAbove
from .serializers import UserSerializer, UserCreateSerializer, UserUpdateSerializer


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def platform_analytics(request):
    """
    Platform-wide analytics for SuperAdmin
    """
    # Time filters
    days = request.GET.get('days', 30)
    start_date = timezone.now() - timedelta(days=int(days))
    
    # User metrics
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    new_users = User.objects.filter(created_at__gte=start_date).count()
    
    # Role distribution
    role_stats = User.objects.values('role').annotate(count=Count('id'))
    
    # Organization metrics
    total_orgs = User.objects.values('organization').exclude(organization=None).distinct().count()
    active_orgs = User.objects.filter(
        organization__isnull=False,
        is_active=True
    ).values('organization').distinct().count()
    
    # Growth metrics
    monthly_growth = User.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=30)
    ).count()
    
    analytics = {
        'user_metrics': {
            'total_users': total_users,
            'active_users': active_users,
            'new_users_this_period': new_users,
            'monthly_growth_rate': monthly_growth,
        },
        'organization_metrics': {
            'total_organizations': total_orgs,
            'active_organizations': active_orgs,
        },
        'role_distribution': list(role_stats),
        'period': {
            'days': days,
            'start_date': start_date.isoformat(),
            'end_date': timezone.now().isoformat(),
        }
    }
    
    return Response(analytics)


@api_view(['GET'])
@permission_classes([IsAdminOrAbove])
def organization_analytics(request):
    """
    Organization-specific analytics for Admin and above
    """
    if not request.user.organization:
        return Response(
            {'error': 'User must belong to an organization'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    org = request.user.organization
    days = request.GET.get('days', 30)
    start_date = timezone.now() - timedelta(days=int(days))
    
    # Organization user metrics
    org_users = User.objects.filter(organization=org)
    total_org_users = org_users.count()
    active_org_users = org_users.filter(is_active=True).count()
    new_org_users = org_users.filter(created_at__gte=start_date).count()
    
    # Department metrics
    try:
        from organizations.models import Department, Team
        org_departments = Department.objects.filter(organization=org)
        org_teams = Team.objects.filter(organization=org)
        
        department_stats = []
        for dept in org_departments:
            dept_users = User.objects.filter(organization=org)
            # Count users through DepartmentMembership
            dept_user_count = dept.members.count()
            dept_active_count = dept.members.filter(user__is_active=True).count()
            
            department_stats.append({
                'name': dept.name,
                'total_users': dept_user_count,
                'active_users': dept_active_count,
                'teams_count': dept.teams.filter(is_active=True).count(),
            })
    except ImportError:
        department_stats = []
    
    # Role distribution within organization
    org_role_stats = org_users.values('role').annotate(count=Count('id'))
    
    analytics = {
        'organization': {
            'id': str(org.id),
            'name': org.name,
        },
        'user_metrics': {
            'total_users': total_org_users,
            'active_users': active_org_users,
            'new_users_this_period': new_org_users,
        },
        'department_metrics': department_stats,
        'role_distribution': list(org_role_stats),
        'period': {
            'days': days,
            'start_date': start_date.isoformat(),
            'end_date': timezone.now().isoformat(),
        }
    }
    
    return Response(analytics)


@api_view(['GET'])
@permission_classes([IsManagerOrAbove])
def team_analytics(request):
    """
    Team-specific analytics for Manager and above
    """
    # Get team members managed by this user
    team_members = User.objects.filter(managed_by=request.user)
    
    if not team_members.exists():
        return Response(
            {'error': 'No team members found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    days = request.GET.get('days', 30)
    start_date = timezone.now() - timedelta(days=int(days))
    
    # Team metrics
    total_team_members = team_members.count()
    active_team_members = team_members.filter(is_active=True).count()
    new_team_members = team_members.filter(created_at__gte=start_date).count()
    
    # Department info
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
                'total_employees': dept_membership.department.members.count(),
                'manager': dept_membership.department.head.get_full_name() if dept_membership.department.head else None,
            }
    except ImportError:
        pass
    
    # Team role distribution
    team_role_stats = team_members.values('role').annotate(count=Count('id'))
    
    # Individual member performance
    member_performance = []
    for member in team_members:
        try:
            from courses.models import Enrollment
            from assignments.models import Assignment, AssignmentSubmission
            
            enrollments = Enrollment.objects.filter(user=member)
            enrolled_course_ids = enrollments.values_list('course_id', flat=True)
            assignments = Assignment.objects.filter(
                course_id__in=enrolled_course_ids,
                is_active=True,
                is_published=True,
            ).distinct()
            completed_assignments = AssignmentSubmission.objects.filter(
                student=member,
                assignment__in=assignments,
                status__in=['SUBMITTED', 'GRADED']
            ).values('assignment_id').distinct().count()
            
            performance = {
                'user_id': str(member.id),
                'name': member.get_full_name(),
                'email': member.email,
                'role': member.role,
                'enrollments_count': enrollments.count(),
                'completed_courses': enrollments.filter(status='COMPLETED').count(),
                'assignments_count': assignments.count(),
                'completed_assignments': completed_assignments,
                'last_active': member.last_active_at.isoformat() if member.last_active_at else None,
            }
        except ImportError:
            performance = {
                'user_id': str(member.id),
                'name': member.get_full_name(),
                'email': member.email,
                'role': member.role,
                'enrollments_count': 0,
                'completed_courses': 0,
                'assignments_count': 0,
                'completed_assignments': 0,
                'last_active': member.last_active_at.isoformat() if member.last_active_at else None,
            }
        
        member_performance.append(performance)
    
    analytics = {
        'team_metrics': {
            'total_members': total_team_members,
            'active_members': active_team_members,
            'new_members_this_period': new_team_members,
        },
        'department_info': department_info,
        'role_distribution': list(team_role_stats),
        'member_performance': member_performance,
        'period': {
            'days': days,
            'start_date': start_date.isoformat(),
            'end_date': timezone.now().isoformat(),
        }
    }
    
    return Response(analytics)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def student_analytics(request):
    """
    Student-specific analytics
    """
    user = request.user
    
    if not user.is_student():
        return Response(
            {'error': 'This endpoint is for students only'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        from courses.models import Enrollment
        from certificates.models import Certificate
        from assignments.models import Assignment, AssignmentSubmission
        
        # Student's learning data
        enrollments = Enrollment.objects.filter(user=user)
        certificates = Certificate.objects.filter(user=user)
        enrolled_course_ids = enrollments.values_list('course_id', flat=True)
        assignments = Assignment.objects.filter(
            course_id__in=enrolled_course_ids,
            is_active=True,
            is_published=True,
        ).distinct()
        
        # Learning metrics
        total_enrollments = enrollments.count()
        active_enrollments = enrollments.filter(is_active=True).count()
        completed_enrollments = enrollments.filter(status='COMPLETED').count()
        
        # Certificate metrics
        total_certificates = certificates.count()
        certificates_this_month = certificates.filter(
            issued_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        # Assignment metrics
        total_assignments = assignments.count()
        completed_assignments = AssignmentSubmission.objects.filter(
            student=user,
            assignment__in=assignments,
            status__in=['SUBMITTED', 'GRADED']
        ).values('assignment_id').distinct().count()
        pending_assignments = max(total_assignments - completed_assignments, 0)
        
        # Progress tracking
        avg_progress = enrollments.aggregate(
            avg_progress=Avg('progress_percentage')
        )['avg_progress'] or 0
        
        # Learning streak (simplified)
        learning_streak = 7  # This would be calculated from actual activity logs
        
        # Recent activity
        recent_enrollments = enrollments.order_by('-created_at')[:5]
        recent_certificates = certificates.order_by('-issued_at')[:3]
        
        analytics = {
            'learning_metrics': {
                'total_enrollments': total_enrollments,
                'active_enrollments': active_enrollments,
                'completed_enrollments': completed_enrollments,
                'average_progress': round(avg_progress, 2),
                'learning_streak_days': learning_streak,
            },
            'certificate_metrics': {
                'total_certificates': total_certificates,
                'certificates_this_month': certificates_this_month,
            },
            'assignment_metrics': {
                'total_assignments': total_assignments,
                'completed_assignments': completed_assignments,
                'pending_assignments': pending_assignments,
                'completion_rate': round(
                    (completed_assignments / total_assignments * 100) if total_assignments > 0 else 0, 2
                ),
            },
            'recent_activity': {
                'recent_enrollments': [
                    {
                        'course_id': str(enrollment.course.id),
                        'course_title': enrollment.course.title,
                        'enrolled_at': enrollment.created_at.isoformat(),
                        'progress': enrollment.progress_percentage or 0,
                    }
                    for enrollment in recent_enrollments
                ],
                'recent_certificates': [
                    {
                        'course_id': str(certificate.course.id),
                        'course_title': certificate.course.title,
                        'issued_at': certificate.issued_at.isoformat(),
                    }
                    for certificate in recent_certificates
                ],
            }
        }
        
    except ImportError:
        # Fallback if models don't exist
        analytics = {
            'learning_metrics': {
                'total_enrollments': 0,
                'active_enrollments': 0,
                'completed_enrollments': 0,
                'average_progress': 0,
                'learning_streak_days': 0,
            },
            'certificate_metrics': {
                'total_certificates': 0,
                'certificates_this_month': 0,
            },
            'assignment_metrics': {
                'total_assignments': 0,
                'completed_assignments': 0,
                'pending_assignments': 0,
                'completion_rate': 0,
            },
            'recent_activity': {
                'recent_enrollments': [],
                'recent_certificates': [],
            }
        }
    
    return Response(analytics)


@api_view(['GET', 'POST'])
@permission_classes([IsAdminOrAbove])
def organization_users(request):
    """
    Manage organization users (Admin and above)
    """
    if not request.user.organization:
        return Response(
            {'error': 'User must belong to an organization'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    org = request.user.organization
    
    if request.method == 'GET':
        # List organization users
        users = User.objects.filter(organization=org)
        
        # Filtering
        role_filter = request.GET.get('role')
        if role_filter:
            users = users.filter(role=role_filter)
        
        department_filter = request.GET.get('department')
        if department_filter:
            users = users.filter(department_id=department_filter)
        
        # Pagination
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(users, request)
        
        serializer = UserSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    elif request.method == 'POST':
        # Create new user in organization
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save(organization=org)
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
@permission_classes([IsManagerOrAbove])
def team_members(request):
    """
    Manage team members (Manager and above)
    """
    if request.method == 'GET':
        # List team members
        team_members = User.objects.filter(managed_by=request.user)
        
        # Pagination
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(team_members, request)
        
        serializer = UserSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    elif request.method == 'POST':
        # Add team member
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save(
                organization=request.user.organization,
                managed_by=request.user
            )
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsManagerOrAbove])
def assign_training(request):
    """
    Assign training to team members
    """
    user_ids = request.data.get('user_ids', [])
    course_ids = request.data.get('course_ids', [])
    
    if not user_ids or not course_ids:
        return Response(
            {'error': 'user_ids and course_ids are required'}, 
            status=status.HTTP_400_BAD_BAD_REQUEST
        )
    
    try:
        from courses.models import Course, Enrollment
        
        # Verify manager can manage these users
        team_members = User.objects.filter(
            id__in=user_ids,
            managed_by=request.user
        )
        
        if team_members.count() != len(user_ids):
            return Response(
                {'error': 'Some users are not in your team'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Verify courses belong to organization
        courses = Course.objects.filter(
            id__in=course_ids,
            organization=request.user.organization
        )
        
        if courses.count() != len(course_ids):
            return Response(
                {'error': 'Some courses are not available'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create enrollments
        enrollments_created = []
        for user in team_members:
            for course in courses:
                enrollment, created = Enrollment.objects.get_or_create(
                    user=user,
                    course=course,
                    defaults={'assigned_by': request.user}
                )
                if created:
                    enrollments_created.append({
                        'user_id': str(user.id),
                        'course_id': str(course.id),
                        'enrollment_id': str(enrollment.id)
                    })
        
        return Response({
            'message': f'Training assigned to {len(team_members)} team members',
            'enrollments_created': enrollments_created
        })
        
    except ImportError:
        return Response(
            {'error': 'Course enrollment system not available'}, 
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_permissions(request):
    """
    Get current user permissions and accessible data
    """
    user = request.user
    
    # Basic permissions
    permissions = {
        'role': user.role,
        'is_superadmin': user.is_superadmin(),
        'is_admin': user.is_admin(),
        'is_manager': user.is_manager(),
        'is_student': user.is_student(),
        'organization_id': str(user.organization.id) if user.organization else None,
        'department_id': str(user.department.id) if user.department else None,
        'team_id': str(user.team.id) if user.team else None,
    }
    
    # Accessible data based on role
    if user.is_superadmin():
        permissions['accessible_data'] = {
            'all_users': True,
            'all_organizations': True,
            'system_settings': True,
            'platform_analytics': True,
        }
    elif user.is_admin():
        permissions['accessible_data'] = {
            'organization_users': True,
            'organization_courses': True,
            'organization_analytics': True,
            'department_management': True,
        }
    elif user.is_manager():
        permissions['accessible_data'] = {
            'team_members': True,
            'team_analytics': True,
            'training_assignment': True,
            'performance_review': True,
        }
    else:  # Student
        permissions['accessible_data'] = {
            'own_courses': True,
            'own_certificates': True,
            'own_assignments': True,
            'own_progress': True,
        }
    
    return Response(permissions)


@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def system_health(request):
    """
    System health check for SuperAdmin
    """
    from django.db import connection
    from django.core.cache import cache
    
    health_status = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'checks': {}
    }
    
    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status['checks']['database'] = {
            'status': 'healthy',
            'message': 'Database connection successful'
        }
    except Exception as e:
        health_status['checks']['database'] = {
            'status': 'unhealthy',
            'message': str(e)
        }
        health_status['status'] = 'degraded'
    
    # Cache check
    try:
        cache.set('health_check', 'ok', 10)
        cache_result = cache.get('health_check')
        if cache_result == 'ok':
            health_status['checks']['cache'] = {
                'status': 'healthy',
                'message': 'Cache working properly'
            }
        else:
            raise Exception('Cache not working')
    except Exception as e:
        health_status['checks']['cache'] = {
            'status': 'unhealthy',
            'message': str(e)
        }
        health_status['status'] = 'degraded'
    
    # User metrics
    try:
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        health_status['checks']['user_metrics'] = {
            'status': 'healthy',
            'total_users': total_users,
            'active_users': active_users
        }
    except Exception as e:
        health_status['checks']['user_metrics'] = {
            'status': 'unhealthy',
            'message': str(e)
        }
        health_status['status'] = 'degraded'
    
    return Response(health_status)
