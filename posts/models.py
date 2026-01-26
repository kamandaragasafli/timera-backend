import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class AIGeneratedContent(models.Model):
    """AI generated content batch for approval workflow"""
    
    STATUS_CHOICES = [
        ('generating', 'Generating'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_content_batches')
    
    # Generation parameters
    company_info = models.JSONField(help_text="Company information used for generation")
    generation_prompt = models.TextField(help_text="AI prompt used for generation")
    language = models.CharField(max_length=10, default='az')
    
    # Status and metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='generating')
    total_posts = models.IntegerField(default=10)
    approved_posts = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_generated_content'
        verbose_name = 'AI Generated Content'
        verbose_name_plural = 'AI Generated Content'
        ordering = ['-created_at']

    def __str__(self):
        return f"AI Content Batch {self.id} - {self.user.email}"


class Post(models.Model):
    """Social media posts with scheduling and multi-platform support"""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('scheduled', 'Scheduled'),
        ('published', 'Published'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    
    # Content
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    hashtags = models.JSONField(default=list, help_text="List of hashtags")
    description = models.TextField(blank=True, help_text="Post description/summary")
    
    # Images and Design
    design_url = models.URLField(blank=True, help_text="URL to Canva design or uploaded image")
    design_thumbnail = models.URLField(blank=True)
    canva_design_id = models.CharField(max_length=200, blank=True, help_text="Canva design ID")
    custom_image = models.ImageField(upload_to='post_images/', blank=True, null=True)
    image_url = models.URLField(blank=True, help_text="Supabase Storage URL for the image")
    design_specs = models.JSONField(null=True, blank=True, help_text="AI-generated design specifications")
    imgly_scene = models.JSONField(null=True, blank=True, help_text="img.ly editor scene state for re-editing")
    
    # AI Generation
    ai_generated = models.BooleanField(default=False)
    ai_content_batch = models.ForeignKey(
        AIGeneratedContent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posts'
    )
    brand_voice = models.ForeignKey(
        'accounts.BrandVoice', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='posts'
    )
    ai_prompt = models.TextField(blank=True, help_text="Original AI prompt used")
    
    # Approval workflow
    requires_approval = models.BooleanField(default=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_posts'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Scheduling
    scheduled_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Publishing
    platforms = models.ManyToManyField(
        'social_accounts.SocialAccount',
        through='PostPlatform',
        related_name='posts'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'posts'
        verbose_name = 'Post'
        verbose_name_plural = 'Posts'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.title or 'Untitled'} ({self.status})"

    @property
    def is_scheduled(self):
        """Check if post is scheduled for future"""
        return self.status == 'scheduled' and self.scheduled_time and self.scheduled_time > timezone.now()

    @property
    def character_count(self):
        """Get character count of content"""
        return len(self.content)

    def get_platform_posts(self):
        """Get all platform-specific post instances"""
        return self.postplatform_set.all()


class PostPlatform(models.Model):
    """Junction table for posts and platforms with platform-specific data"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('published', 'Published'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    social_account = models.ForeignKey('social_accounts.SocialAccount', on_delete=models.CASCADE)
    
    # Platform-specific content (if different from main post)
    platform_content = models.TextField(blank=True, help_text="Platform-optimized content")
    platform_specific_data = models.JSONField(default=dict, blank=True)
    
    # Publishing status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    platform_post_id = models.CharField(max_length=200, blank=True, help_text="ID from social platform")
    platform_post_url = models.URLField(blank=True)
    
    # Error handling
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    last_retry_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'post_platforms'
        verbose_name = 'Post Platform'
        verbose_name_plural = 'Post Platforms'
        unique_together = ['post', 'social_account']

    def __str__(self):
        return f"{self.post.title or 'Untitled'} -> {self.social_account.platform} ({self.status})"

    @property
    def effective_content(self):
        """Get the content to use for this platform"""
        return self.platform_content or self.post.content


class PostPerformance(models.Model):
    """Post engagement metrics and performance tracking"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post_platform = models.ForeignKey(PostPlatform, on_delete=models.CASCADE, related_name='performance_metrics')
    
    # Engagement metrics
    likes = models.IntegerField(default=0)
    comments = models.IntegerField(default=0)
    shares = models.IntegerField(default=0)
    saves = models.IntegerField(default=0, help_text="Instagram saves, LinkedIn saves, etc.")
    
    # Reach and impressions
    reach = models.IntegerField(default=0, help_text="Unique users who saw the post")
    impressions = models.IntegerField(default=0, help_text="Total number of times post was shown")
    
    # Engagement rate (calculated)
    engagement_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="(likes + comments + shares) / reach * 100")
    
    # Video-specific metrics (if applicable)
    video_views = models.IntegerField(default=0)
    video_completion_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Link clicks (if post has link)
    link_clicks = models.IntegerField(default=0)
    
    # Additional platform-specific metrics
    additional_metrics = models.JSONField(default=dict, blank=True, help_text="Platform-specific metrics (e.g., profile visits, website clicks)")
    
    # Timestamp of when metrics were last fetched
    last_fetched_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'post_performance'
        verbose_name = 'Post Performance'
        verbose_name_plural = 'Post Performances'
        unique_together = ['post_platform']
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.post_platform.post.title or 'Untitled'} - {self.post_platform.social_account.platform} Performance"

    def calculate_engagement_rate(self):
        """Calculate engagement rate"""
        if self.reach > 0:
            total_engagement = self.likes + self.comments + self.shares
            self.engagement_rate = (total_engagement / self.reach) * 100
        else:
            self.engagement_rate = None
        return self.engagement_rate

    def save(self, *args, **kwargs):
        """Override save to calculate engagement rate"""
        self.calculate_engagement_rate()
        super().save(*args, **kwargs)


class ContentTemplate(models.Model):
    """Reusable content templates for different types of posts"""
    
    CATEGORY_CHOICES = [
        ('announcement', 'Announcement'),
        ('educational', 'Educational'),
        ('promotional', 'Promotional'),
        ('engagement', 'Engagement'),
        ('news', 'News'),
        ('personal', 'Personal'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='content_templates')
    
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    template_content = models.TextField(help_text="Use {variables} for dynamic content")
    description = models.TextField(blank=True)
    
    # Template variables
    variables = models.JSONField(default=list, help_text="List of variable names used in template")
    
    # Usage tracking
    usage_count = models.IntegerField(default=0)
    last_used = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'content_templates'
        verbose_name = 'Content Template'
        verbose_name_plural = 'Content Templates'
        unique_together = ['user', 'name']

    def __str__(self):
        return f"{self.user.email} - {self.name} ({self.category})"

    def render_template(self, variables_dict):
        """Render template with provided variables"""
        content = self.template_content
        for var_name, var_value in variables_dict.items():
            content = content.replace(f"{{{var_name}}}", str(var_value))
        return content
