from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Count, Avg, Sum, F
from django.utils import timezone
from datetime import timedelta, date
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth

from .models import (
    LearningMetric, OrganizationMetric, PlatformMetric,
    LearningPath, UserLearningPath, Achievement, UserAchievement
)
from accounts.models import User
from accounts.permissions import IsSuperAdmin, IsAdmin, IsManager, IsAdminOrAbove, IsManagerOrAbove


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def platform_analytics(request):
    """
    Comprehensive platform analytics for SuperAdmin
    """
    # Time filters
    period = request.GET.get('period', 'monthly')
    days = request.GET.get('days', 30)
    start_date = timezone.now() - timedelta(days=int(days))
    
    # User growth metrics
    user_growth = User.objects.filter(created_at__gte=start_date)
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    new_users = user_growth.count()
    
    # Organization metrics
    total_orgs = User.objects.values('organization').exclude(organization=None).distinct().count()
    active_orgs = User.objects.filter(
        organization__isnull=False,
        is_active=True
    ).values('organization').distinct().count()
    
    # Role distribution
    role_stats = User.objects.values('role').annotate(count=Count('id'))
    
    # Platform metrics from database
    platform_metrics = PlatformMetric.objects.filter(
        period_end__gte=start_date
    ).order_by('-period_end')
    
    # Recent metrics summary
    recent_metrics = {}
    for metric in platform_metrics[:10]:
        metric_key = metric.metric_type.lower()
        recent_metrics[metric_key] = {
            'value': float(metric.metric_value),
            'change': float(metric.change_percentage),
            'period': metric.period_end.strftime('%Y-%m-%d')
        }
    
    analytics = {
        'summary': {
            'total_users': total_users,
            'active_users': active_users,
            'new_users_this_period': new_users,
            'total_organizations': total_orgs,
            'active_organizations': active_orgs,
        },
        'role_distribution': list(role_stats),
        'recent_metrics': recent_metrics,
        'period': {
            'type': period,
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
    Organization-specific analytics
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
    department_stats = []
    try:
        from organizations.models_extended import Department
        departments = Department.objects.filter(organization=org)
        
        for dept in departments:
            dept_users = User.objects.filter(department=dept)
            department_stats.append({
                'id': str(dept.id),
                'name': dept.name,
                'total_users': dept_users.count(),
                'active_users': dept_users.filter(is_active=True).count(),
                'manager': dept.manager.get_full_name() if dept.manager else None,
                'teams_count': dept.teams.filter(is_active=True).count(),
            })
    except ImportError:
        departments = []
    
    # Organization metrics from database
    org_metrics = OrganizationMetric.objects.filter(
        organization=org,
        period_end__gte=start_date
    ).order_by('-period_end')
    
    recent_metrics = {}
    for metric in org_metrics[:10]:
        metric_key = metric.metric_type.lower()
        recent_metrics[metric_key] = {
            'value': float(metric.metric_value),
            'change': float(metric.change_percentage),
            'period': metric.period_end.strftime('%Y-%m-%d')
        }
    
    analytics = {
        'organization': {
            'id': str(org.id),
            'name': org.name,
        },
        'summary': {
            'total_users': total_org_users,
            'active_users': active_org_users,
            'new_users_this_period': new_org_users,
            'departments_count': len(department_stats),
        },
        'department_stats': department_stats,
        'recent_metrics': recent_metrics,
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
    Team-specific analytics for managers
    """
    # Get team members
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
    
    # Individual performance
    member_performance = []
    for member in team_members:
        # Learning metrics
        learning_metrics = LearningMetric.objects.filter(
            user=member,
            recorded_at__gte=start_date
        )
        
        total_enrollments = learning_metrics.values('course').distinct().count()
        avg_progress = learning_metrics.aggregate(
            avg_progress=Avg('progress_percentage')
        )['avg_progress'] or 0
        
        # Achievement metrics
        achievements = UserAchievement.objects.filter(
            user=member,
            awarded_at__gte=start_date
        ).count()
        
        performance = {
            'user_id': str(member.id),
            'name': member.get_full_name(),
            'email': member.email,
            'role': member.role,
            'is_active': member.is_active,
            'enrollments_count': total_enrollments,
            'average_progress': round(avg_progress, 2),
            'achievements_count': achievements,
            'last_active': member.last_active_at.isoformat() if member.last_active_at else None,
        }
        
        member_performance.append(performance)
    
    analytics = {
        'team_summary': {
            'total_members': total_team_members,
            'active_members': active_team_members,
            'new_members_this_period': new_team_members,
        },
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
    Student-specific analytics and progress tracking
    """
    user = request.user
    
    if not user.is_student():
        return Response(
            {'error': 'This endpoint is for students only'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    days = request.GET.get('days', 30)
    start_date = timezone.now() - timedelta(days=int(days))
    
    # Learning metrics
    learning_metrics = LearningMetric.objects.filter(
        user=user,
        recorded_at__gte=start_date
    ).order_by('-recorded_at')
    
    # Current enrollments
    current_enrollments = learning_metrics.values('course').distinct().count()
    avg_progress = learning_metrics.aggregate(
        avg_progress=Avg('progress_percentage')
    )['avg_progress'] or 0
    
    # Total learning time
    total_time = learning_metrics.aggregate(
        total_time=Sum('time_spent_minutes')
    )['total_time'] or 0
    
    # Achievement tracking
    achievements = UserAchievement.objects.filter(
        user=user,
        awarded_at__gte=start_date
    ).order_by('-awarded_at')
    
    total_achievements = achievements.count()
    
    # Learning paths
    learning_paths = UserLearningPath.objects.filter(user=user)
    active_paths = learning_paths.filter(status='IN_PROGRESS').count()
    completed_paths = learning_paths.filter(status='COMPLETED').count()
    
    # Recent activity
    recent_metrics = learning_metrics[:5]
    recent_achievements = achievements[:3]
    
    analytics = {
        'learning_summary': {
            'current_enrollments': current_enrollments,
            'average_progress': round(avg_progress, 2),
            'total_learning_time_minutes': total_time,
            'learning_streak_days': user.learning_streak if hasattr(user, 'learning_streak') else 0,
        },
        'achievement_summary': {
            'total_achievements': total_achievements,
            'achievements_this_period': total_achievements,
        },
        'learning_paths': {
            'active_paths': active_paths,
            'completed_paths': completed_paths,
            'total_paths': learning_paths.count(),
        },
        'recent_activity': {
            'recent_learning': [
                {
                    'course_id': str(metric.course.id),
                    'course_title': metric.course.title,
                    'progress': float(metric.progress_percentage),
                    'time_spent': metric.time_spent_minutes,
                    'recorded_at': metric.recorded_at.isoformat(),
                }
                for metric in recent_metrics
            ],
            'recent_achievements': [
                {
                    'achievement_id': str(achievement.achievement.id),
                    'achievement_name': achievement.achievement.name,
                    'achievement_icon': achievement.achievement.icon,
                    'awarded_at': achievement.awarded_at.isoformat(),
                }
                for achievement in recent_achievements
            ],
        },
        'period': {
            'days': days,
            'start_date': start_date.isoformat(),
            'end_date': timezone.now().isoformat(),
        }
    }
    
    return Response(analytics)


@api_view(['GET'])
@permission_classes([IsAdminOrAbove])
def learning_paths(request):
    """
    Manage learning paths
    """
    if not request.user.organization:
        return Response(
            {'error': 'User must belong to an organization'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    org = request.user.organization
    
    # Get learning paths
    paths = LearningPath.objects.filter(
        Q(organization=org) | Q(is_public=True)
    ).order_by('name')
    
    # Filter by difficulty
    difficulty = request.GET.get('difficulty')
    if difficulty:
        paths = paths.filter(difficulty_level=difficulty)
    
    # Pagination
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(paths, request)
    
    # Serialize paths
    paths_data = []
    for path in page:
        path_data = {
            'id': str(path.id),
            'name': path.name,
            'description': path.description,
            'difficulty_level': path.difficulty_level,
            'estimated_hours': path.estimated_hours,
            'is_public': path.is_public,
            'is_active': path.is_active,
            'created_by': path.created_by.get_full_name() if path.created_by else None,
            'created_at': path.created_at.isoformat(),
        }
        
        # Add step count
        path_data['steps_count'] = path.steps.count()
        
        # Add user progress if student
        if request.user.is_student():
            user_path = UserLearningPath.objects.filter(
                user=request.user,
                learning_path=path
            ).first()
            
            if user_path:
                path_data['user_progress'] = {
                    'status': user_path.status,
                    'progress_percentage': float(user_path.progress_percentage),
                    'completed_steps': user_path.completed_steps,
                    'total_steps': user_path.total_steps,
                    'started_at': user_path.started_at.isoformat() if user_path.started_at else None,
                }
        
        paths_data.append(path_data)
    
    return paginator.get_paginated_response(paths_data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def enroll_learning_path(request, path_id):
    """
    Enroll user in a learning path
    """
    try:
        path = LearningPath.objects.get(id=path_id)
        
        # Check if user can access this path
        if not path.is_public and path.organization != request.user.organization:
            return Response(
                {'error': 'Learning path not accessible'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Create or get user learning path
        user_path, created = UserLearningPath.objects.get_or_create(
            user=request.user,
            learning_path=path,
            defaults={
                'status': 'IN_PROGRESS',
                'started_at': timezone.now(),
                'total_steps': path.steps.count(),
            }
        )
        
        if not created:
            return Response(
                {'error': 'Already enrolled in this learning path'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({
            'message': 'Successfully enrolled in learning path',
            'user_path_id': str(user_path.id),
            'status': user_path.status,
        })
        
    except LearningPath.DoesNotExist:
        return Response(
            {'error': 'Learning path not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_achievements(request):
    """
    Get user achievements and badges
    """
    user = request.user
    
    # Get user achievements
    achievements = UserAchievement.objects.filter(user=user).order_by('-awarded_at')
    
    # Get available achievements (for organization users)
    available_achievements = Achievement.objects.filter(is_active=True)
    
    if user.organization:
        available_achievements = available_achievements.filter(
            Q(organization=user.organization) | Q(organization__isnull=True)
        )
    
    # Serialize achievements
    user_achievements_data = []
    for user_achievement in achievements:
        user_achievements_data.append({
            'id': str(user_achievement.id),
            'achievement_id': str(user_achievement.achievement.id),
            'name': user_achievement.achievement.name,
            'description': user_achievement.achievement.description,
            'icon': user_achievement.achievement.icon,
            'achievement_type': user_achievement.achievement.achievement_type,
            'points': user_achievement.achievement.points,
            'awarded_at': user_achievement.awarded_at.isoformat(),
            'progress_value': user_achievement.progress_value,
            'progress_max': user_achievement.progress_max,
        })
    
    # Serialize available achievements
    available_achievements_data = []
    for achievement in available_achievements:
        # Check if user already has this achievement
        has_achievement = achievements.filter(achievement=achievement).exists()
        
        achievement_data = {
            'id': str(achievement.id),
            'name': achievement.name,
            'description': achievement.description,
            'icon': achievement.icon,
            'achievement_type': achievement.achievement_type,
            'points': achievement.points,
            'criteria': achievement.criteria,
            'is_unlocked': has_achievement,
        }
        
        available_achievements_data.append(achievement_data)
    
    return Response({
        'user_achievements': user_achievements_data,
        'available_achievements': available_achievements_data,
        'total_points': sum(a.achievement.points for a in achievements),
        'achievements_count': achievements.count(),
    })


@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def system_metrics(request):
    """
    Get system health and performance metrics
    """
    from django.db import connection
    from django.core.cache import cache
    from django.conf import settings
    
    metrics = {
        'timestamp': timezone.now().isoformat(),
        'status': 'healthy',
        'checks': {}
    }
    
    # Database health
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Get database size (PostgreSQL specific)
        try:
            cursor.execute("""
                SELECT pg_size_pretty(pg_database_size(current_database())) as size
            """)
            db_size = cursor.fetchone()[0]
        except:
            db_size = "Unknown"
        
        metrics['checks']['database'] = {
            'status': 'healthy',
            'size': db_size,
            'connection': 'successful'
        }
    except Exception as e:
        metrics['checks']['database'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        metrics['status'] = 'degraded'
    
    # Cache health
    try:
        cache.set('health_check', 'ok', 10)
        cache_result = cache.get('health_check')
        if cache_result == 'ok':
            metrics['checks']['cache'] = {
                'status': 'healthy',
                'connection': 'successful'
            }
        else:
            raise Exception('Cache not working')
    except Exception as e:
        metrics['checks']['cache'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        metrics['status'] = 'degraded'
    
    # User metrics
    try:
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        recent_logins = User.objects.filter(
            last_active_at__gte=timezone.now() - timedelta(hours=24)
        ).count()
        
        metrics['checks']['users'] = {
            'status': 'healthy',
            'total_users': total_users,
            'active_users': active_users,
            'recent_logins_24h': recent_logins
        }
    except Exception as e:
        metrics['checks']['users'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        metrics['status'] = 'degraded'
    
    # Platform metrics
    try:
        platform_metrics = PlatformMetric.objects.filter(
            period_end__gte=timezone.now() - timedelta(days=7)
        ).order_by('-period_end')[:10]
        
        metrics['checks']['platform_metrics'] = {
            'status': 'healthy',
            'recent_metrics_count': platform_metrics.count(),
            'last_updated': platform_metrics.first().recorded_at.isoformat() if platform_metrics.exists() else None
        }
    except Exception as e:
        metrics['checks']['platform_metrics'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        metrics['status'] = 'degraded'
    
    return Response(metrics)
