from rest_framework import serializers
from .models import Post, AIGeneratedContent, PostPlatform, ContentTemplate, PostPerformance


class AIGeneratedContentSerializer(serializers.ModelSerializer):
    """Serializer for AI Generated Content batches"""
    
    class Meta:
        model = AIGeneratedContent
        fields = [
            'id', 'company_info', 'generation_prompt', 'language',
            'status', 'total_posts', 'approved_posts', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PostSerializer(serializers.ModelSerializer):
    """Serializer for Post model"""
    
    platforms_count = serializers.SerializerMethodField()
    character_count = serializers.SerializerMethodField()
    custom_image_url = serializers.SerializerMethodField()
    design_url_absolute = serializers.SerializerMethodField()
    design_thumbnail_absolute = serializers.SerializerMethodField()
    image_url_absolute = serializers.SerializerMethodField()
    post_platforms = serializers.SerializerMethodField()
    
    class Meta:
        model = Post
        fields = [
            'id', 'title', 'content', 'description', 'hashtags',
            'design_url', 'design_thumbnail', 'canva_design_id', 'custom_image',
            'image_url', 'image_url_absolute', 'custom_image_url', 'design_url_absolute', 'design_thumbnail_absolute',
            'design_specs', 'imgly_scene',
            'ai_generated', 'ai_content_batch', 'brand_voice', 'ai_prompt',
            'requires_approval', 'approved_by', 'approved_at',
            'scheduled_time', 'status', 'platforms_count', 'character_count',
            'post_platforms', 'created_at', 'updated_at', 'published_at'
        ]
        read_only_fields = [
            'id', 'ai_generated', 'ai_content_batch', 'approved_by', 'approved_at',
            'platforms_count', 'character_count', 'custom_image_url', 
            'design_url_absolute', 'design_thumbnail_absolute', 'image_url_absolute',
            'created_at', 'updated_at', 'published_at'
        ]
    
    def create(self, validated_data):
        """Override create to add extensive logging"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"[DEBUG] PostSerializer.create() called")
        logger.info(f"[DEBUG] validated_data keys: {list(validated_data.keys())}")
        
        # Log all validated data
        for key, value in validated_data.items():
            if isinstance(value, str) and len(value) > 200:
                logger.info(f"[DEBUG]   validated_data.{key}: {value[:200]}... (length: {len(value)})")
            elif isinstance(value, (dict, list)):
                logger.info(f"[DEBUG]   validated_data.{key}: {type(value).__name__} with {len(value)} items")
                if isinstance(value, dict) and len(value) > 0:
                    logger.info(f"[DEBUG]     dict keys: {list(value.keys())[:10]}")
            elif hasattr(value, 'name'):  # FileField
                logger.info(f"[DEBUG]   validated_data.{key}: File({value.name}, {value.size if hasattr(value, 'size') else 'N/A'} bytes)")
            else:
                logger.info(f"[DEBUG]   validated_data.{key}: {value}")
        
        # Check for image fields
        image_fields = ['custom_image', 'image_url', 'design_url']
        for field in image_fields:
            if field in validated_data:
                logger.info(f"[DEBUG]   ✅ {field} present: {validated_data[field]}")
        
        # Check for FILES in context
        request = self.context.get('request')
        if request and request.FILES:
            logger.info(f"[DEBUG]   FILES in request: {list(request.FILES.keys())}")
            for key, file in request.FILES.items():
                logger.info(f"[DEBUG]     - {key}: {file.name}, {file.size} bytes, {file.content_type}")
        
        # Get user from context
        user = self.context.get('request').user if self.context.get('request') else None
        if user:
            logger.info(f"[DEBUG]   User from context: {user.email} (ID: {user.id})")
        else:
            logger.warning(f"[DEBUG]   ⚠️ No user in context!")
        
        # Create instance
        logger.info(f"[DEBUG] Creating Post instance...")
        try:
            instance = super().create(validated_data)
            logger.info(f"[DEBUG] ✅ Post instance created successfully")
            logger.info(f"[DEBUG]   - ID: {instance.id}")
            logger.info(f"[DEBUG]   - Title: {instance.title}")
            logger.info(f"[DEBUG]   - Status: {instance.status}")
            logger.info(f"[DEBUG]   - User: {instance.user.email}")
            logger.info(f"[DEBUG]   - Has image_url: {bool(instance.image_url)}")
            logger.info(f"[DEBUG]   - Has custom_image: {bool(instance.custom_image)}")
            logger.info(f"[DEBUG]   - Has design_url: {bool(instance.design_url)}")
            if instance.image_url:
                logger.info(f"[DEBUG]   - image_url: {instance.image_url}")
            if instance.custom_image:
                logger.info(f"[DEBUG]   - custom_image: {instance.custom_image.name}")
            if instance.design_url:
                logger.info(f"[DEBUG]   - design_url: {instance.design_url}")
            return instance
        except Exception as e:
            logger.error(f"[ERROR] ❌ Failed to create Post instance: {e}", exc_info=True)
            logger.error(f"[ERROR] Exception type: {type(e).__name__}")
            raise
    
    def update(self, instance, validated_data):
        """Override update to add extensive logging"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"[DEBUG] PostSerializer.update() called")
        logger.info(f"[DEBUG] Instance ID: {instance.id}")
        logger.info(f"[DEBUG] Current instance status: {instance.status}")
        logger.info(f"[DEBUG] validated_data keys: {list(validated_data.keys())}")
        
        # Log changes
        for key, new_value in validated_data.items():
            old_value = getattr(instance, key, None)
            if old_value != new_value:
                logger.info(f"[DEBUG]   {key} changed:")
                logger.info(f"[DEBUG]     old: {str(old_value)[:100]}")
                logger.info(f"[DEBUG]     new: {str(new_value)[:100]}")
        
        try:
            instance = super().update(instance, validated_data)
            logger.info(f"[DEBUG] ✅ Post instance updated successfully")
            logger.info(f"[DEBUG]   - ID: {instance.id}")
            logger.info(f"[DEBUG]   - Status: {instance.status}")
            return instance
        except Exception as e:
            logger.error(f"[ERROR] ❌ Failed to update Post instance: {e}", exc_info=True)
            raise
    
    def get_platforms_count(self, obj):
        return obj.platforms.count()
    
    def get_character_count(self, obj):
        return len(obj.content) if obj.content else 0
    
    def get_post_platforms(self, obj):
        """Return PostPlatform data for this post"""
        post_platforms = obj.postplatform_set.all().select_related('social_account')
        return [
            {
                'id': str(pp.id),
                'social_account': str(pp.social_account.id),
                'social_account_name': pp.social_account.platform,
                'social_account_username': pp.social_account.platform_username,
                'social_account_display_name': pp.social_account.display_name,
                'status': pp.status,
                'platform_post_id': pp.platform_post_id,
                'platform_post_url': pp.platform_post_url,
            }
            for pp in post_platforms
        ]
    
    def get_custom_image_url(self, obj):
        """Return absolute URL for custom image"""
        if obj.custom_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.custom_image.url)
        return None
    
    def get_design_url_absolute(self, obj):
        """Return absolute URL for design_url if it's a local file"""
        if obj.design_url:
            # Check if it's already an absolute URL (starts with http)
            if obj.design_url.startswith('http'):
                return obj.design_url
            # Otherwise, build absolute URL for local file
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.design_url)
        return None
    
    def get_design_thumbnail_absolute(self, obj):
        """Return absolute URL for design_thumbnail if it's a local file"""
        if obj.design_thumbnail:
            # Check if it's already an absolute URL (starts with http)
            if obj.design_thumbnail.startswith('http'):
                return obj.design_thumbnail
            # Otherwise, build absolute URL for local file
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.design_thumbnail)
        return None
    
    def get_image_url_absolute(self, obj):
        """Return absolute URL for image_url if it's a local file"""
        if obj.image_url:
            # Check if it's already an absolute URL (starts with http)
            if obj.image_url.startswith('http'):
                return obj.image_url
            # Otherwise, build absolute URL for local file
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image_url)
        return None


class PostUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating posts"""
    
    class Meta:
        model = Post
        fields = [
            'title', 'content', 'description', 'hashtags',
            'scheduled_time', 'status', 'imgly_scene'
        ]
    
    def validate_status(self, value):
        # Only allow certain status transitions
        if self.instance:
            current_status = self.instance.status
            allowed_transitions = {
                'pending_approval': ['approved', 'cancelled', 'draft'],
                'approved': ['scheduled', 'draft'],
                'draft': ['scheduled', 'approved'],
                'scheduled': ['published', 'cancelled'],
            }
            
            if current_status in allowed_transitions:
                if value not in allowed_transitions[current_status]:
                    raise serializers.ValidationError(
                        f"Cannot change status from {current_status} to {value}"
                    )
        
        return value


class PostApprovalSerializer(serializers.Serializer):
    """Serializer for post approval actions"""
    
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    post_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False
    )


class PostGenerationRequestSerializer(serializers.Serializer):
    """Serializer for requesting AI post generation"""
    
    generate_images = serializers.BooleanField(default=True)
    custom_prompt = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    def validate(self, attrs):
        # Check if user has company profile
        user = self.context['request'].user
        try:
            user.company_profile
        except:
            raise serializers.ValidationError(
                "Company profile required. Please complete your company information first."
            )
        
        return attrs


class ContentTemplateSerializer(serializers.ModelSerializer):
    """Serializer for Content Template model"""
    
    class Meta:
        model = ContentTemplate
        fields = [
            'id', 'name', 'category', 'template_content', 'description',
            'variables', 'usage_count', 'last_used', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'usage_count', 'last_used', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class PostPlatformSerializer(serializers.ModelSerializer):
    """Serializer for PostPlatform model"""
    
    social_account_name = serializers.CharField(source='social_account.platform', read_only=True)
    social_account_username = serializers.CharField(source='social_account.platform_username', read_only=True)
    social_account_display_name = serializers.CharField(source='social_account.display_name', read_only=True)
    
    class Meta:
        model = PostPlatform
        fields = [
            'id', 'social_account', 'social_account_name', 'social_account_username', 'social_account_display_name',
            'platform_content', 'platform_specific_data', 'status', 'platform_post_id', 'platform_post_url',
            'error_message', 'retry_count', 'last_retry_at', 'published_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'social_account_name', 'social_account_username', 'social_account_display_name',
            'platform_post_id', 'platform_post_url',
            'error_message', 'retry_count', 'last_retry_at', 'published_at',
            'created_at', 'updated_at'
        ]


class PostPerformanceSerializer(serializers.ModelSerializer):
    """Serializer for Post Performance metrics"""
    
    platform = serializers.SerializerMethodField()
    post_title = serializers.SerializerMethodField()
    
    class Meta:
        model = PostPerformance
        fields = [
            'id', 'post_platform', 'platform', 'post_title',
            'likes', 'comments', 'shares', 'saves',
            'reach', 'impressions', 'engagement_rate',
            'video_views', 'video_completion_rate',
            'link_clicks', 'additional_metrics',
            'last_fetched_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'engagement_rate', 'created_at', 'updated_at']
    
    def get_platform(self, obj):
        return obj.post_platform.social_account.platform if obj.post_platform else None
    
    def get_post_title(self, obj):
        return obj.post_platform.post.title if obj.post_platform and obj.post_platform.post else None




