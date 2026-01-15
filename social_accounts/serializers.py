from rest_framework import serializers
from .models import SocialAccount


class SocialAccountSerializer(serializers.ModelSerializer):
    """Serializer for social media accounts"""
    
    class Meta:
        model = SocialAccount
        fields = [
            'id', 'platform', 'platform_user_id', 'platform_username',
            'display_name', 'profile_picture_url', 'is_active',
            'last_used', 'settings', 'expires_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def to_representation(self, instance):
        """Hide sensitive token data"""
        data = super().to_representation(instance)
        # Don't expose tokens in API responses
        return data



