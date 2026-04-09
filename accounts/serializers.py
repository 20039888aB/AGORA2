from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, UserProfile, RoleRequest


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for UserProfile model
    """
    class Meta:
        model = UserProfile
        fields = [
            'employee_id', 'department', 'team', 'job_title',
            'location', 'timezone', 'language', 'notification_preferences',
            'last_login_ip'
        ]
        read_only_fields = ['last_login_ip']


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model with profile information
    """
    profile = UserProfileSerializer(read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    full_name = serializers.CharField(read_only=True)
    is_active_user = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'role', 'role_display',
            'organization', 'managed_by', 'login_count', 'last_active_at',
            'role_update_count', 'phone', 'avatar', 'date_of_birth', 'bio',
            'is_verified', 'original_email', 'created_at', 'updated_at', 'profile',
            'full_name', 'is_active_user'
        ]
        read_only_fields = [
            'login_count', 'last_active_at', 'role_update_count',
            'created_at', 'updated_at', 'is_active_user'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'organization': {'required': False},
            'managed_by': {'required': False},
        }


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new users
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    profile = UserProfileSerializer(required=False)
    
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'password', 'password_confirm',
            'role', 'organization', 'managed_by', 'phone', 'avatar',
            'date_of_birth', 'bio', 'profile'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        
        # Validate role-based creation permissions
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            creator = request.user
            role = attrs.get('role', 'STUDENT')
            from .services import UserService
            if not UserService.can_create_user_with_role(creator, role):
                raise serializers.ValidationError(
                    f"Insufficient permissions to create user with role {role}"
                )
        
        return attrs
    
    def create(self, validated_data):
        # Remove password_confirm from validated_data
        validated_data.pop('password_confirm')
        
        # Extract profile data
        profile_data = validated_data.pop('profile', {})
        
        # Create user
        from .services import UserService
        user = UserService.create_user(validated_data, creator=self.context.get('request').user)
        
        # Update profile with additional data
        if profile_data:
            for key, value in profile_data.items():
                setattr(user.profile, key, value)
            user.profile.save()
        
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user information
    """
    profile = UserProfileSerializer(required=False)
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone', 'avatar', 'date_of_birth',
            'bio', 'profile'
        ]
    
    def update(self, instance, validated_data):
        # Extract profile data
        profile_data = validated_data.pop('profile', {})
        
        # Update user
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update profile
        if profile_data:
            for attr, value in profile_data.items():
                setattr(instance.profile, attr, value)
            instance.profile.save()
        
        return instance


class RoleRequestSerializer(serializers.ModelSerializer):
    """
    Serializer for RoleRequest model
    """
    user_info = UserSerializer(source='user', read_only=True)
    requested_role_display = serializers.CharField(source='get_requested_role_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    reviewed_by_info = UserSerializer(source='reviewed_by', read_only=True)
    
    class Meta:
        model = RoleRequest
        fields = [
            'id', 'user', 'user_info', 'requested_role', 'requested_role_display',
            'reason', 'status', 'status_display', 'reviewed_by',
            'reviewed_by_info', 'reviewed_at', 'review_comments',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'user', 'status', 'reviewed_by', 'reviewed_at', 'reviewed_comments',
            'created_at', 'updated_at'
        ]


class RoleRequestCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating role requests
    """
    class Meta:
        model = RoleRequest
        fields = ['requested_role', 'reason']
    
    def validate(self, attrs):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required")
        
        user = request.user
        requested_role = attrs.get('requested_role')
        
        # Validate role request
        from .services import RoleRequestService
        if not RoleRequestService.can_request_role(user, requested_role):
            raise serializers.ValidationError(
                f"Cannot request role {requested_role}"
            )
        
        return attrs
    
    def create(self, validated_data):
        from .services import RoleRequestService
        return RoleRequestService.create_role_request(
            user=self.context['request'].user,
            requested_role=validated_data['requested_role'],
            reason=validated_data['reason']
        )


class RoleRequestActionSerializer(serializers.Serializer):
    """
    Serializer for approving/rejecting role requests
    """
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    comments = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required")
        
        return attrs


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(
                request=self.context.get('request'),
                username=email,
                password=password
            )
            
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            
            if not user.is_active_user:
                raise serializers.ValidationError('Account is inactive or deleted')
            
            attrs['user'] = user
            return attrs
        
        raise serializers.ValidationError('Both email and password are required')


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for password change
    """
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        
        user = self.context['request'].user
        if not user.check_password(attrs['old_password']):
            raise serializers.ValidationError("Old password is incorrect")
        
        return attrs


class UserStatisticsSerializer(serializers.Serializer):
    """
    Serializer for user statistics
    """
    total_users = serializers.IntegerField(read_only=True)
    org_users = serializers.IntegerField(read_only=True)
    managed_users = serializers.IntegerField(read_only=True)
    enrolled_courses = serializers.IntegerField(read_only=True)
    completed_courses = serializers.IntegerField(read_only=True)
    total_progress = serializers.FloatField(read_only=True)
    active_users = serializers.IntegerField(read_only=True)
    total_organizations = serializers.IntegerField(read_only=True)
    org_departments = serializers.IntegerField(read_only=True)
    org_teams = serializers.IntegerField(read_only=True)
    team_users = serializers.IntegerField(read_only=True)
