from django.db import models
from django.utils import timezone
from .models import User, UserProfile, RoleRequest


class UserService:
    """
    Service layer for User business logic
    """
    
    @staticmethod
    def get_accessible_users_queryset(user):
        """
        Get queryset of users that current user can access
        based on role-based access control
        """
        if user.is_superadmin():
            return User.objects.active()
        
        elif user.is_admin():
            return User.objects.active().by_organization(user.organization)
        
        elif user.is_manager():
            return User.objects.active().managed_by(user)
        
        elif user.is_student():
            return User.objects.active().filter(id=user.id)
        
        return User.objects.active().none()
    
    @staticmethod
    def create_user(data, creator=None):
        """
        Create a new user with validation
        """
        email = data.get('email')
        
        # Check if email already exists
        if User.objects.active().filter(email=email).exists():
            raise ValueError(f"User with email {email} already exists")
        
        # Validate role-based creation permissions
        role = data.get('role', 'STUDENT')
        if creator and not UserService.can_create_user_with_role(creator, role):
            raise ValueError(f"Insufficient permissions to create user with role {role}")
        
        # Create user
        user = User.objects.create_user(
            email=email,
            password=data.get('password'),
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            role=role,
            organization=data.get('organization'),
            managed_by=data.get('managed_by'),
            phone=data.get('phone', ''),
            bio=data.get('bio', ''),
            date_of_birth=data.get('date_of_birth'),
        )
        
        # Create profile
        UserProfile.objects.create(
            user=user,
            employee_id=data.get('employee_id', ''),
            department=data.get('department'),
            team=data.get('team'),
            job_title=data.get('job_title', ''),
            location=data.get('location', ''),
            timezone=data.get('timezone', 'UTC'),
            language=data.get('language', 'en'),
        )
        
        return user
    
    @staticmethod
    def can_create_user_with_role(creator, role):
        """
        Check if creator can create user with specific role
        """
        if creator.is_superadmin():
            return True  # Can create any role
        
        elif creator.is_admin_or_above():
            # Admin can create admin, manager, student
            return role in ['ADMIN', 'MANAGER', 'STUDENT']
        
        elif creator.is_manager():
            # Manager can only create students
            return role == 'STUDENT'
        
        elif creator.is_student():
            # Student cannot create users
            return False
        
        return False
    
    @staticmethod
    def update_user_role(user, new_role, updated_by):
        """
        Update user role with proper validation and logging
        """
        if not updated_by.can_manage_user(user):
            raise PermissionError("Insufficient permissions to update user role")
        
        old_role = user.role
        user.role = new_role
        user.increment_role_update_count()
        user.save(update_fields=['role'])
        
        # Log the role change
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=updated_by,
            action='ROLE_CHANGE',
            target_user=user,
            details={
                'old_role': old_role,
                'new_role': new_role,
                'updated_via': 'direct_update'
            },
            ip_address=updated_by.last_login_ip
        )
        
        return user
    
    @staticmethod
    def bulk_update_last_active(users):
        """
        Bulk update last_active_at for multiple users
        """
        User.objects.filter(
            id__in=[user.id for user in users]
        ).update(last_active_at=timezone.now())
    
    @staticmethod
    def get_user_statistics(user):
        """
        Get statistics based on user role
        """
        if user.is_superadmin():
            return {
                'total_users': User.objects.active().count(),
                'total_organizations': user.organizations.count(),
                'active_users': User.objects.active().filter(
                    last_active_at__gte=timezone.now() - timezone.timedelta(days=30)
                ).count(),
            }
        
        elif user.is_admin():
            return {
                'org_users': User.objects.active().by_organization(user.organization).count(),
                'org_departments': user.organization.departments.count(),
                'org_teams': user.organization.teams.count(),
            }
        
        elif user.is_manager():
            return {
                'managed_users': User.objects.active().managed_by(user).count(),
                'team_users': User.objects.active().filter(
                    profile__team__in=user.profile.team.organization.teams.all() if user.profile.team else []
                ).count(),
            }
        
        elif user.is_student():
            return {
                'enrolled_courses': user.enrollments.filter(is_active=True).count(),
                'completed_courses': user.enrollments.filter(
                    is_active=True,
                    completed_at__isnull=False
                ).count(),
                'total_progress': user.enrollments.aggregate(
                    total=models.Avg('progress_percentage')
                )['total'] or 0,
            }
        
        return {}


class RoleRequestService:
    """
    Service layer for Role Request business logic
    """
    
    @staticmethod
    def approve_role_request(role_request, reviewer, comments=''):
        """Approve role request"""
        old_role = role_request.user.role
        role_request.status = 'APPROVED'
        role_request.reviewed_by = reviewer
        role_request.reviewed_at = timezone.now()
        role_request.review_comments = comments
        
        # Update user role
        role_request.user.role = role_request.requested_role
        role_request.user.increment_role_update_count()
        role_request.user.save(update_fields=['role'])
        
        role_request.save()
        
        # Log the role change
        from audit_logs.models import AuditLog
        AuditLog.objects.create(
            user=reviewer,
            action='ROLE_CHANGE',
            target_user=role_request.user,
            details={
                'old_role': old_role,
                'new_role': role_request.requested_role,
                'approved_via': 'role_request'
            },
            ip_address=reviewer.last_login_ip
        )
    
    @staticmethod
    def reject_role_request(role_request, reviewer, comments=''):
        """Reject role request"""
        role_request.status = 'REJECTED'
        role_request.reviewed_by = reviewer
        role_request.reviewed_at = timezone.now()
        role_request.review_comments = comments
        role_request.save()
    
    @staticmethod
    def create_role_request(user, requested_role, reason):
        """
        Create a new role request
        """
        # Check if user already has pending request
        if RoleRequest.objects.filter(
            user=user,
            status='PENDING'
        ).exists():
            raise ValueError("You already have a pending role request")
        
        # Validate role escalation
        if not UserService.can_request_role(user, requested_role):
            raise ValueError(f"Cannot request role {requested_role}")
        
        return RoleRequest.objects.create(
            user=user,
            requested_role=requested_role,
            reason=reason
        )
    
    @staticmethod
    def can_request_role(user, requested_role):
        """
        Check if user can request the specified role
        """
        current_role = user.role
        
        # Define role hierarchy
        role_hierarchy = {
            'STUDENT': 1,
            'MANAGER': 2,
            'ADMIN': 3,
            'SUPERADMIN': 4,
        }
        
        current_level = role_hierarchy.get(current_role, 0)
        requested_level = role_hierarchy.get(requested_role, 0)
        
        # Can only request higher roles (not same level)
        return requested_level > current_level
    
    @staticmethod
    def get_pending_requests(approver):
        """
        Get pending requests that approver can review
        """
        base_queryset = RoleRequest.objects.filter(status='PENDING')
        
        if approver.is_superadmin():
            return base_queryset
        
        elif approver.is_admin():
            return base_queryset.filter(
                user__organization=approver.organization
            )
        
        elif approver.is_manager():
            return base_queryset.filter(
                user__managed_by=approver
            )
        
        return base_queryset.none()
    
    @staticmethod
    def bulk_approve_requests(request_ids, approver, comments=''):
        """
        Bulk approve multiple role requests
        """
        requests = RoleRequest.objects.filter(
            id__in=request_ids,
            status='PENDING'
        )
        
        approved_count = 0
        for request in requests:
            if approver.can_manage_user(request.user):
                request.approve(approver, comments)
                approved_count += 1
        
        return approved_count
