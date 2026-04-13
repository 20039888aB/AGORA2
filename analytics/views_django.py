from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg, F
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@login_required
def analytics_team(request):
    """
    Team analytics page for managers with real team analytics data
    """
    user = request.user
    
    # Check permissions - only managers and admins can access team analytics
    if not user.is_manager_or_above():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')

    try:
        from accounts.models import User
        from courses.models import Course
        from enrollments.models import Enrollment
        from certificates.models import Certificate
        from organizations.models import Organization
        
        # Get team members managed by this manager
        team_members = User.objects.active().filter(
            organization=user.organization,
            managed_by=user
        ).select_related('profile', 'profile__team', 'profile__department')
        
        # Get time period for analytics
        days = int(request.GET.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # Team overview statistics
        total_team_members = team_members.count()
        active_team_members = team_members.filter(
            last_active_at__gte=start_date
        ).count()
        new_team_members = team_members.filter(
            created_at__gte=start_date
        ).count()
        
        # Learning analytics for team
        team_enrollments = Enrollment.objects.filter(
            user__in=team_members,
            created_at__gte=start_date
        ).select_related('user', 'course')
        
        total_enrollments = team_enrollments.count()
        completed_enrollments = team_enrollments.filter(status='COMPLETED').count()
        active_enrollments = team_enrollments.filter(status='ACTIVE').count()
        
        # Calculate completion rate
        completion_rate = (completed_enrollments / total_enrollments * 100) if total_enrollments > 0 else 0
        
        # Course performance analytics
        course_performance = []
        team_courses = Course.objects.filter(
            organization=user.organization,
            is_active=True
        ).annotate(
            enrollment_count=Count('enrollment', filter=Q(enrollment__user__in=team_members)),
            completion_count=Count('enrollment', filter=Q(enrollment__user__in=team_members, enrollment__status='COMPLETED')),
            avg_progress=Avg('enrollment__progress_percentage', filter=Q(enrollment__user__in=team_members))
        ).order_by('-enrollment_count')[:10]
        
        for course in team_courses:
            if course.enrollment_count > 0:
                course_completion_rate = (course.completion_count / course.enrollment_count) * 100
                course_performance.append({
                    'course': course,
                    'enrollment_count': course.enrollment_count,
                    'completion_count': course.completion_count,
                    'completion_rate': round(course_completion_rate, 1),
                    'avg_progress': round(course.avg_progress or 0, 1)
                })
        
        # Individual member performance
        member_performance = []
        for member in team_members:
            # Get member's enrollments
            member_enrollments = Enrollment.objects.filter(
                user=member,
                created_at__gte=start_date
            ).select_related('course')
            
            # Calculate member metrics
            total_member_enrollments = member_enrollments.count()
            completed_member_enrollments = member_enrollments.filter(status='COMPLETED').count()
            active_member_enrollments = member_enrollments.filter(status='ACTIVE').count()
            
            # Calculate average progress
            avg_progress = member_enrollments.aggregate(
                avg_progress=Avg('progress_percentage')
            )['avg_progress'] or 0
            
            # Get certificates
            certificates_count = Certificate.objects.filter(
                user=member,
                awarded_at__gte=start_date
            ).count()
            
            # Calculate learning hours (sum of course durations for completed courses)
            learning_hours = member_enrollments.filter(status='COMPLETED').aggregate(
                total_hours=Sum('course__duration_hours')
            )['total_hours'] or 0
            
            # Get last activity
            last_enrollment = member_enrollments.order_by('-created_at').first()
            last_activity = last_enrollment.created_at if last_enrollment else member.last_active_at
            
            performance_data = {
                'member': member,
                'total_enrollments': total_member_enrollments,
                'completed_enrollments': completed_member_enrollments,
                'active_enrollments': active_member_enrollments,
                'avg_progress': round(avg_progress, 1),
                'certificates_count': certificates_count,
                'learning_hours': learning_hours,
                'last_activity': last_activity,
                'completion_rate': round((completed_member_enrollments / total_member_enrollments * 100) if total_member_enrollments > 0 else 0, 1)
            }
            
            member_performance.append(performance_data)
        
        # Sort members by completion rate
        member_performance.sort(key=lambda x: x['completion_rate'], reverse=True)
        
        # Time-based analytics (progress over time)
        time_series_data = []
        for i in range(days):
            date = timezone.now() - timedelta(days=i)
            date_enrollments = team_enrollments.filter(created_at__date=date.date()).count()
            date_completions = team_enrollments.filter(
                status='COMPLETED',
                completed_at__date=date.date()
            ).count()
            
            time_series_data.append({
                'date': date.date(),
                'enrollments': date_enrollments,
                'completions': date_completions
            })
        
        # Department/Team breakdown
        department_stats = {}
        for member in team_members:
            dept_name = member.profile.department.name if member.profile.department else 'Unassigned'
            if dept_name not in department_stats:
                department_stats[dept_name] = {
                    'members': 0,
                    'enrollments': 0,
                    'completions': 0,
                    'avg_progress': 0
                }
            
            department_stats[dept_name]['members'] += 1
            
            # Add department enrollment stats
            dept_enrollments = Enrollment.objects.filter(
                user=member,
                created_at__gte=start_date
            )
            department_stats[dept_name]['enrollments'] += dept_enrollments.count()
            department_stats[dept_name]['completions'] += dept_enrollments.filter(status='COMPLETED').count()
        
        # Calculate department averages
        for dept_name, stats in department_stats.items():
            if stats['enrollments'] > 0:
                dept_progress = Enrollment.objects.filter(
                    user__profile__department__name=dept_name,
                    created_at__gte=start_date
                ).aggregate(avg_progress=Avg('progress_percentage'))['avg_progress'] or 0
                stats['avg_progress'] = round(dept_progress, 1)
                stats['completion_rate'] = round((stats['completions'] / stats['enrollments']) * 100, 1)
            else:
                stats['completion_rate'] = 0
        
        # Get top performer
        top_performer = member_performance[0] if member_performance else None
        
        # Get learning trends
        learning_trends = {
            'daily_enrollments': time_series_data[:7],  # Last 7 days
            'weekly_progress': [],  # Can be implemented for weekly data
            'monthly_summary': {
                'total_enrollments': total_enrollments,
                'total_completions': completed_enrollments,
                'total_hours': sum(perf['learning_hours'] for perf in member_performance),
                'avg_team_progress': round(sum(perf['avg_progress'] for perf in member_performance) / len(member_performance), 1) if member_performance else 0
            }
        }
        
        context = {
            'user': user,
            'page_title': 'Team Analytics',
            'team_members': team_members,
            'member_performance': member_performance,
            'course_performance': course_performance,
            'department_stats': department_stats,
            'top_performer': top_performer,
            'learning_trends': learning_trends,
            'time_series_data': list(reversed(time_series_data)),  # Show oldest to newest
            'team_overview': {
                'total_members': total_team_members,
                'active_members': active_team_members,
                'new_members': new_team_members,
                'total_enrollments': total_enrollments,
                'completed_enrollments': completed_enrollments,
                'active_enrollments': active_enrollments,
                'completion_rate': round(completion_rate, 1),
                'avg_team_progress': round(sum(perf['avg_progress'] for perf in member_performance) / len(member_performance), 1) if member_performance else 0
            },
            'period': {
                'days': days,
                'start_date': start_date,
                'end_date': timezone.now()
            }
        }
        
    except ImportError as e:
        messages.error(request, 'Analytics features are not available. Please contact administrator.')
        context = {
            'user': user,
            'page_title': 'Team Analytics',
            'team_members': [],
            'member_performance': [],
            'course_performance': [],
            'department_stats': {},
            'top_performer': None,
            'learning_trends': {},
            'time_series_data': [],
            'team_overview': {},
            'period': {}
        }

    return render(request, 'analytics/team.html', context)


@login_required
def analytics_reports(request):
    """
    Analytics reports page with report generation functionality
    """
    user = request.user
    
    # Check permissions - only managers and admins can access reports
    if not user.is_manager_or_above():
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')

    try:
        from accounts.models import User
        from courses.models import Course
        from enrollments.models import Enrollment
        from certificates.models import Certificate
        from organizations.models import Organization
        
        # Get organizations (for superadmins) or use user's organization
        if user.is_superadmin():
            organizations = Organization.objects.filter(is_active=True)
        else:
            organizations = Organization.objects.filter(id=user.organization.id)
        
        # Get reports data
        days = int(request.GET.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # Generate different types of reports
        reports_data = []
        
        # User Activity Report
        if user.is_superadmin():
            user_activity = User.objects.filter(
                created_at__gte=start_date
            ).values('role').annotate(
                count=Count('id'),
                active_count=Count('id', filter=Q(is_active=True))
            )
            
            reports_data.append({
                'type': 'user_activity',
                'title': 'User Activity Report',
                'data': list(user_activity),
                'generated_at': timezone.now()
            })
        else:
            # Organization-specific user activity
            org_users = User.objects.filter(
                organization=user.organization,
                created_at__gte=start_date
            ).values('role').annotate(
                count=Count('id'),
                active_count=Count('id', filter=Q(is_active=True))
            )
            
            reports_data.append({
                'type': 'user_activity',
                'title': 'Organization User Activity',
                'data': list(org_users),
                'generated_at': timezone.now()
            })
        
        # Course Performance Report
        if user.is_superadmin():
            course_performance = Course.objects.filter(
                created_at__gte=start_date
            ).values('organization__name').annotate(
                course_count=Count('id'),
                enrollment_count=Count('enrollment'),
                completion_count=Count('enrollment', filter=Q(enrollment__status='COMPLETED'))
            )
        else:
            course_performance = Course.objects.filter(
                organization=user.organization,
                created_at__gte=start_date
            ).values('title').annotate(
                enrollment_count=Count('enrollment'),
                completion_count=Count('enrollment', filter=Q(enrollment__status='COMPLETED'))
            )
        
        reports_data.append({
            'type': 'course_performance',
            'title': 'Course Performance Report',
            'data': list(course_performance),
            'generated_at': timezone.now()
        })
        
        # Learning Progress Report
        if user.is_superadmin():
            learning_progress = Enrollment.objects.filter(
                created_at__gte=start_date
            ).values('user__organization__name').annotate(
                total_enrollments=Count('id'),
                completed_enrollments=Count('id', filter=Q(status='COMPLETED')),
                avg_progress=Avg('progress_percentage')
            )
        else:
            learning_progress = Enrollment.objects.filter(
                user__organization=user.organization,
                created_at__gte=start_date
            ).values('user__profile__department__name').annotate(
                total_enrollments=Count('id'),
                completed_enrollments=Count('id', filter=Q(status='COMPLETED')),
                avg_progress=Avg('progress_percentage')
            )
        
        reports_data.append({
            'type': 'learning_progress',
            'title': 'Learning Progress Report',
            'data': list(learning_progress),
            'generated_at': timezone.now()
        })
        
        # Handle report generation requests
        if request.method == 'POST':
            action = request.POST.get('action')
            
            if action == 'generate_report':
                report_type = request.POST.get('report_type')
                organization_id = request.POST.get('organization')
                date_range = request.POST.get('date_range', '30d')
                format_type = request.POST.get('format', 'json')
                
                # Convert date range to days
                if date_range == '7d':
                    report_days = 7
                elif date_range == '30d':
                    report_days = 30
                elif date_range == '90d':
                    report_days = 90
                elif date_range == '1y':
                    report_days = 365
                else:
                    report_days = 30
                
                report_start_date = timezone.now() - timedelta(days=report_days)
                
                # Generate report based on type
                if report_type == 'user_activity':
                    if user.is_superadmin() and organization_id:
                        report_data = User.objects.filter(
                            organization_id=organization_id,
                            created_at__gte=report_start_date
                        ).values('role').annotate(
                            count=Count('id'),
                            active_count=Count('id', filter=Q(is_active=True))
                        )
                    else:
                        report_data = User.objects.filter(
                            organization=user.organization,
                            created_at__gte=report_start_date
                        ).values('role').annotate(
                            count=Count('id'),
                            active_count=Count('id', filter=Q(is_active=True))
                        )
                
                elif report_type == 'course_performance':
                    if user.is_superadmin() and organization_id:
                        report_data = Course.objects.filter(
                            organization_id=organization_id,
                            created_at__gte=report_start_date
                        ).values('title').annotate(
                            enrollment_count=Count('enrollment'),
                            completion_count=Count('enrollment', filter=Q(enrollment__status='COMPLETED'))
                        )
                    else:
                        report_data = Course.objects.filter(
                            organization=user.organization,
                            created_at__gte=report_start_date
                        ).values('title').annotate(
                            enrollment_count=Count('enrollment'),
                            completion_count=Count('enrollment', filter=Q(enrollment__status='COMPLETED'))
                        )
                
                elif report_type == 'learning_progress':
                    if user.is_superadmin() and organization_id:
                        report_data = Enrollment.objects.filter(
                            user__organization_id=organization_id,
                            created_at__gte=report_start_date
                        ).values('user__email').annotate(
                            total_enrollments=Count('id'),
                            completed_enrollments=Count('id', filter=Q(status='COMPLETED')),
                            avg_progress=Avg('progress_percentage')
                        )
                    else:
                        report_data = Enrollment.objects.filter(
                            user__organization=user.organization,
                            created_at__gte=report_start_date
                        ).values('user__email').annotate(
                            total_enrollments=Count('id'),
                            completed_enrollments=Count('id', filter=Q(status='COMPLETED')),
                            avg_progress=Avg('progress_percentage')
                        )
                
                else:
                    messages.error(request, 'Invalid report type.')
                    return redirect('analytics:reports')
                
                # Create report record
                from analytics.models import GeneratedReport
                report = GeneratedReport.objects.create(
                    title=f"{report_type.replace('_', ' ').title()} - {timezone.now().strftime('%Y-%m-%d')}",
                    report_type=report_type,
                    organization=user.organization if not user.is_superadmin() else None,
                    generated_by=user,
                    data=list(report_data),
                    format_type=format_type,
                    date_range=date_range
                )
                
                messages.success(request, f'Report generated successfully. Report ID: {report.id}')
            
            elif action == 'delete_report':
                report_id = request.POST.get('report_id')
                try:
                    from analytics.models import GeneratedReport
                    report = GeneratedReport.objects.get(id=report_id, generated_by=user)
                    report.delete()
                    messages.success(request, 'Report deleted successfully.')
                except GeneratedReport.DoesNotExist:
                    messages.error(request, 'Report not found.')
        
        # Get generated reports
        try:
            from analytics.models import GeneratedReport
            if user.is_superadmin():
                generated_reports = GeneratedReport.objects.all().order_by('-generated_at')[:20]
            else:
                generated_reports = GeneratedReport.objects.filter(
                    organization=user.organization
                ).order_by('-generated_at')[:20]
        except ImportError:
            generated_reports = []
        
        context = {
            'user': user,
            'page_title': 'Analytics Reports',
            'reports_data': reports_data,
            'generated_reports': generated_reports,
            'organizations': organizations,
            'period': {
                'days': days,
                'start_date': start_date,
                'end_date': timezone.now()
            }
        }
        
    except ImportError as e:
        messages.error(request, 'Reports features are not available. Please contact administrator.')
        context = {
            'user': user,
            'page_title': 'Analytics Reports',
            'reports_data': [],
            'generated_reports': [],
            'organizations': [],
            'period': {}
        }

    return render(request, 'analytics/reports.html', context)
