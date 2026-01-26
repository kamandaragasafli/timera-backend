from rest_framework import serializers
from rest_framework.fields import JSONField as DRFJSONField
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from .models import User, BrandVoice, CompanyProfile


class FlexibleJSONField(DRFJSONField):
    """JSONField that accepts both JSON strings and already-parsed dict/list"""
    
    def to_internal_value(self, data):
        """Accept dict/list directly without requiring JSON string"""
        # If data is already a dict/list, return it directly (no validation needed)
        if isinstance(data, (dict, list)):
            return data
        # If data is None, return None (allow_null=True handles this)
        if data is None:
            return None
        # If data is empty string, return empty list/dict based on default
        if isinstance(data, str) and not data.strip():
            # Return default if set, otherwise empty list
            from rest_framework.fields import empty
            if hasattr(self, 'default') and self.default is not empty:
                return self.default() if callable(self.default) else self.default
            return []  # Default to empty list
        
        # For strings, parse as JSON
        if isinstance(data, str):
            import json
            try:
                parsed = json.loads(data)
                return parsed
            except (json.JSONDecodeError, ValueError) as e:
                raise serializers.ValidationError(f"Invalid JSON format: {str(e)}")
        
        # For other types, use parent's validation
        return super().to_internal_value(data)


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name', 
            'company_name', 'timezone', 'subscription_plan', 
            'is_email_verified', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CompanyProfileSerializer(serializers.ModelSerializer):
    """Serializer for CompanyProfile model"""
    
    logo_url = serializers.SerializerMethodField()
    # Explicitly define JSON fields to handle dict/list input properly
    brand_analysis = FlexibleJSONField(required=False, allow_null=True)
    content_topics = FlexibleJSONField(required=False, allow_null=True)
    keywords = FlexibleJSONField(required=False, allow_null=True)
    avoid_topics = FlexibleJSONField(required=False, allow_null=True)
    
    class Meta:
        model = CompanyProfile
        fields = [
            'id', 'company_name', 'industry', 'company_size', 'website', 'location',
            'logo', 'logo_url', 'brand_analysis',
            'business_description', 'target_audience', 'unique_selling_points',
            'social_media_goals', 'preferred_tone', 'content_topics', 'keywords',
            'avoid_topics', 'primary_language', 'posts_to_generate',
            # Branding fields
            'slogan', 'slogan_size_percent', 'branding_enabled', 'branding_mode', 
            'logo_position', 'slogan_position', 'logo_size_percent',
            'gradient_enabled', 'gradient_color', 'gradient_height_percent', 'gradient_position',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'logo_url', 'created_at', 'updated_at']
    
    def get_logo_url(self, obj):
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
        return None
    
    def create(self, validated_data):
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"[DEBUG] CompanyProfileSerializer.create() called")
        logger.info(f"[DEBUG] validated_data keys: {list(validated_data.keys())}")
        if 'logo' in validated_data:
            logo = validated_data['logo']
            logger.info(f"[DEBUG] Logo in validated_data: name={logo.name if hasattr(logo, 'name') else 'N/A'}, size={logo.size if hasattr(logo, 'size') else 'N/A'}")
        
        validated_data['user'] = self.context['request'].user
        instance = super().create(validated_data)
        
        logger.info(f"[DEBUG] ✅ CompanyProfile created with ID: {instance.id}")
        if instance.logo:
            logger.info(f"[DEBUG] Logo saved: {instance.logo.name}")
        
        return instance
    
    def update(self, instance, validated_data):
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"[DEBUG] CompanyProfileSerializer.update() called")
        logger.info(f"[DEBUG] Instance ID: {instance.id}")
        logger.info(f"[DEBUG] Current logo: {instance.logo.name if instance.logo else 'None'}")
        logger.info(f"[DEBUG] validated_data keys: {list(validated_data.keys())}")
        
        if 'logo' in validated_data:
            logo = validated_data['logo']
            logger.info(f"[DEBUG] ✅ Logo in validated_data:")
            logger.info(f"[DEBUG]    - name: {logo.name if hasattr(logo, 'name') else 'N/A'}")
            logger.info(f"[DEBUG]    - size: {logo.size if hasattr(logo, 'size') else 'N/A'} bytes")
            logger.info(f"[DEBUG]    - content_type: {logo.content_type if hasattr(logo, 'content_type') else 'N/A'}")
            logger.info(f"[DEBUG]    - type: {type(logo)}")
        else:
            logger.warning(f"[DEBUG] ⚠️ No 'logo' in validated_data")
            logger.warning(f"[DEBUG]    - request.FILES: {bool(self.context.get('request', {}).FILES)}")
            if self.context.get('request'):
                logger.warning(f"[DEBUG]    - request.FILES keys: {list(self.context['request'].FILES.keys()) if self.context['request'].FILES else 'None'}")
        
        instance = super().update(instance, validated_data)
        
        logger.info(f"[DEBUG] ✅ CompanyProfile updated")
        logger.info(f"[DEBUG] New logo: {instance.logo.name if instance.logo else 'None'}")
        if instance.logo:
            logger.info(f"[DEBUG] Logo URL: {instance.logo.url}")
            logger.info(f"[DEBUG] Logo file exists: {instance.logo.storage.exists(instance.logo.name)}")
        
        return instance


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'email', 'username', 'password', 'confirm_password',
            'first_name', 'last_name', 'company_name'
        ]
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value
    
    def create(self, validated_data):
        # Remove confirm_password from validated_data
        validated_data.pop('confirm_password')
        
        # Create user
        user = User.objects.create_user(**validated_data)
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer that returns user data with tokens"""
    
    username_field = 'email'
    
    def validate(self, attrs):
        # Use email instead of username
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(request=self.context.get('request'),
                              email=email, password=password)
            
            if not user:
                raise serializers.ValidationError('Invalid email or password.')
            
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
            
            # Get tokens
            refresh = self.get_token(user)
            
            return {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data
            }
        else:
            raise serializers.ValidationError('Must include email and password.')


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(email=email, password=password)
            
            if not user:
                raise serializers.ValidationError('Invalid email or password.')
            
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include email and password.')


class BrandVoiceSerializer(serializers.ModelSerializer):
    """Serializer for BrandVoice model"""
    
    class Meta:
        model = BrandVoice
        fields = [
            'id', 'name', 'tone', 'industry', 'target_audience',
            'custom_instructions', 'is_default', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        # Set the user from the request context
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change"""
    
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value
    
    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user