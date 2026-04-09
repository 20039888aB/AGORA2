from rest_framework import serializers
from .models import Organization, Department, Team, DepartmentMembership, TeamMembership


class OrganizationSerializer(serializers.ModelSerializer):
    """
    Serializer for Organization model
    """
    subscription_tier_display = serializers.CharField(source='get_subscription_tier_display', read_only=True)
    approval_workflow_display = serializers.CharField(source='get_approval_workflow_display', read_only=True)
    total_users = serializers.ReadOnlyField()
    total_departments = serializers.ReadOnlyField()
    is_at_user_limit = serializers.ReadOnlyField()
    
    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'slug', 'description', 'logo', 'website', 'email',
            'phone', 'address', 'subscription_tier', 'subscription_tier_display',
            'user_limit', 'approval_workflow', 'approval_workflow_display',
            'is_active', 'created_at', 'updated_at', 'total_users',
            'total_departments', 'is_at_user_limit'
        ]
        read_only_fields = ['created_at', 'updated_at', 'total_users', 'total_departments', 'is_at_user_limit']
    
    def validate_subscription_tier(self, value):
        """Validate subscription tier and user limit"""
        if value == 'FREE' and self.initial_data.get('user_limit', 10) > 10:
            raise serializers.ValidationError("Free tier cannot have more than 10 users")
        return value
    
    def validate_user_limit(self, value):
        """Validate user limit"""
        if value <= 0:
            raise serializers.ValidationError("User limit must be greater than 0")
        return value


class DepartmentSerializer(serializers.ModelSerializer):
    """
    Serializer for Department model
    """
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    head_info = serializers.SerializerMethodField()
    full_path = serializers.ReadOnlyField()
    level = serializers.ReadOnlyField()
    total_users = serializers.ReadOnlyField()
    total_subdepartments = serializers.ReadOnlyField()
    
    class Meta:
        model = Department
        fields = [
            'id', 'organization', 'parent', 'name', 'slug', 'description',
            'head', 'organization_name', 'head_info', 'is_active',
            'created_at', 'updated_at', 'full_path', 'level',
            'total_users', 'total_subdepartments'
        ]
        read_only_fields = ['created_at', 'updated_at', 'organization_name', 'full_path', 'level', 'total_users', 'total_subdepartments']
    
    def get_head_info(self, obj):
        """Get head information"""
        if obj.head:
            return {
                'id': str(obj.head.id),
                'email': obj.head.email,
                'full_name': obj.head.full_name,
            }
        return None
    
    def validate_parent(self, value):
        """Validate parent department"""
        if value and self.instance and value.id == self.instance.id:
            raise serializers.ValidationError("Department cannot be its own parent")
        return value


class TeamSerializer(serializers.ModelSerializer):
    """
    Serializer for Team model
    """
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    lead_info = serializers.SerializerMethodField()
    full_name = serializers.ReadOnlyField()
    total_members = serializers.ReadOnlyField()
    
    class Meta:
        model = Team
        fields = [
            'id', 'organization', 'department', 'name', 'slug', 'description',
            'lead', 'organization_name', 'department_name', 'lead_info',
            'is_active', 'created_at', 'updated_at', 'full_name',
            'total_members'
        ]
        read_only_fields = ['created_at', 'updated_at', 'organization_name', 'department_name', 'full_name', 'total_members']
    
    def get_lead_info(self, obj):
        """Get lead information"""
        if obj.lead:
            return {
                'id': str(obj.lead.id),
                'email': obj.lead.email,
                'full_name': obj.lead.full_name,
            }
        return None


class DepartmentMembershipSerializer(serializers.ModelSerializer):
    """
    Serializer for DepartmentMembership model
    """
    user_info = serializers.SerializerMethodField()
    department_name = serializers.CharField(source='department.name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = DepartmentMembership
        fields = [
            'id', 'user', 'user_info', 'department', 'department_name',
            'role', 'role_display', 'joined_at', 'updated_at'
        ]
        read_only_fields = ['joined_at', 'updated_at']
    
    def get_user_info(self, obj):
        """Get user information"""
        return {
            'id': str(obj.user.id),
            'email': obj.user.email,
            'full_name': obj.user.full_name,
            'role': obj.user.role,
        }


class TeamMembershipSerializer(serializers.ModelSerializer):
    """
    Serializer for TeamMembership model
    """
    user_info = serializers.SerializerMethodField()
    team_name = serializers.CharField(source='team.name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = TeamMembership
        fields = [
            'id', 'user', 'user_info', 'team', 'team_name',
            'role', 'role_display', 'joined_at', 'updated_at'
        ]
        read_only_fields = ['joined_at', 'updated_at']
    
    def get_user_info(self, obj):
        """Get user information"""
        return {
            'id': str(obj.user.id),
            'email': obj.user.email,
            'full_name': obj.user.full_name,
            'role': obj.user.role,
        }


class OrganizationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating organizations
    """
    class Meta:
        model = Organization
        fields = [
            'name', 'slug', 'description', 'website', 'email', 'phone',
            'address', 'subscription_tier', 'user_limit', 'approval_workflow'
        ]
    
    def validate_subscription_tier(self, value):
        if value == 'FREE' and self.initial_data.get('user_limit', 10) > 10:
            raise serializers.ValidationError("Free tier cannot have more than 10 users")
        return value


class DepartmentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating departments
    """
    class Meta:
        model = Department
        fields = [
            'organization', 'parent', 'name', 'slug', 'description', 'head'
        ]


class TeamCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating teams
    """
    class Meta:
        model = Team
        fields = [
            'organization', 'department', 'name', 'slug', 'description', 'lead'
        ]


class TeamMemberAddSerializer(serializers.Serializer):
    """
    Serializer for adding members to teams
    """
    user_id = serializers.UUIDField(write_only=True)
    role = serializers.ChoiceField(
        choices=TeamMembership.ROLE_CHOICES,
        default='MEMBER'
    )
    
    def validate_user_id(self, value):
        """Validate user exists and belongs to organization"""
        from accounts.models import User
        try:
            user = User.objects.active().get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")
        return value
