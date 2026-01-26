import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class User(AbstractUser):
    """Custom User model with additional fields for AI Social Media Management"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    company_name = models.CharField(max_length=200, blank=True, null=True)
    brand_voice_settings = models.JSONField(default=dict, blank=True)
    timezone = models.CharField(max_length=50, default='UTC')
    subscription_plan = models.CharField(
        max_length=20,
        choices=[
            ('free', 'Free'),
            ('pro', 'Pro'),
            ('enterprise', 'Enterprise'),
        ],
        default='free'
    )
    is_email_verified = models.BooleanField(default=False)
    
    # Canva Integration
    canva_access_token = models.TextField(blank=True, null=True)
    canva_refresh_token = models.TextField(blank=True, null=True)
    canva_token_expires_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.email} ({self.get_full_name()})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username


class CompanyProfile(models.Model):
    """Company profile information for AI content generation"""
    
    INDUSTRY_CHOICES = [
        ('technology', 'Technology'),
        ('healthcare', 'Healthcare'),
        ('finance', 'Finance'),
        ('education', 'Education'),
        ('retail', 'Retail'),
        ('manufacturing', 'Manufacturing'),
        ('consulting', 'Consulting'),
        ('real_estate', 'Real Estate'),
        ('food_beverage', 'Food & Beverage'),
        ('travel_tourism', 'Travel & Tourism'),
        ('automotive', 'Automotive'),
        ('fashion', 'Fashion'),
        ('sports_fitness', 'Sports & Fitness'),
        ('entertainment', 'Entertainment'),
        ('non_profit', 'Non-Profit'),
        ('other', 'Other'),
    ]
    
    COMPANY_SIZE_CHOICES = [
        ('1-10', '1-10 employees'),
        ('11-50', '11-50 employees'),
        ('51-200', '51-200 employees'),
        ('201-500', '201-500 employees'),
        ('501-1000', '501-1000 employees'),
        ('1000+', '1000+ employees'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='company_profile')
    
    # Basic Company Information
    company_name = models.CharField(max_length=200)
    industry = models.CharField(max_length=50, choices=INDUSTRY_CHOICES)
    company_size = models.CharField(max_length=20, choices=COMPANY_SIZE_CHOICES)
    website = models.URLField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True, help_text="Company logo")
    brand_analysis = models.JSONField(default=dict, blank=True, help_text="AI-analyzed brand information from logo")
    
    # Branding for Visual Composer
    slogan = models.CharField(max_length=200, blank=True, help_text="Company slogan to overlay on images")
    slogan_size_percent = models.IntegerField(
        default=4,
        validators=[MinValueValidator(2), MaxValueValidator(8)],
        help_text="Slogan font size as percentage of image height (2-8%)"
    )
    branding_enabled = models.BooleanField(default=True, help_text="Automatically apply logo and slogan to images")
    branding_mode = models.CharField(
        max_length=10,
        choices=[
            ('standard', 'Standard'),
            ('custom', 'Custom'),
        ],
        default='standard',
        help_text="Branding layout mode: Standard (fixed) or Custom (configurable)"
    )
    logo_position = models.CharField(
        max_length=20,
        choices=[
            ('top-center', 'Top Center'),
            ('top-left', 'Top Left'),
            ('top-right', 'Top Right'),
            ('bottom-center', 'Bottom Center'),
            ('bottom-left', 'Bottom Left'),
            ('bottom-right', 'Bottom Right'),
        ],
        default='top-center',
        help_text="Logo position on images"
    )
    slogan_position = models.CharField(
        max_length=20,
        choices=[
            ('top-center', 'Top Center'),
            ('bottom-center', 'Bottom Center'),
        ],
        default='bottom-center',
        help_text="Slogan position on images"
    )
    logo_size_percent = models.IntegerField(
        default=13,
        validators=[MinValueValidator(2), MaxValueValidator(25)],
        help_text="Logo size as percentage of image width (2-25% for custom mode)"
    )
    
    # Gradient Settings
    gradient_enabled = models.BooleanField(
        default=True,
        help_text="Apply gradient overlay behind logo/slogan"
    )
    gradient_color = models.CharField(
        max_length=7,
        default='#3B82F6',
        help_text="Gradient color (hex code)"
    )
    gradient_height_percent = models.IntegerField(
        default=25,
        validators=[MinValueValidator(10), MaxValueValidator(50)],
        help_text="Gradient height as percentage of image height (10-50%)"
    )
    gradient_position = models.CharField(
        max_length=10,
        choices=[
            ('top', 'Top'),
            ('bottom', 'Bottom'),
            ('both', 'Both'),
        ],
        default='both',
        help_text="Where to apply gradient"
    )
    
    # Business Description
    business_description = models.TextField(help_text="Describe what your company does")
    target_audience = models.TextField(help_text="Describe your target audience")
    unique_selling_points = models.TextField(help_text="What makes your company unique?")
    
    # Social Media Goals
    social_media_goals = models.TextField(help_text="What do you want to achieve with social media?")
    preferred_tone = models.CharField(
        max_length=50,
        choices=[
            ('professional', 'Professional'),
            ('casual', 'Casual'),
            ('friendly', 'Friendly'),
            ('authoritative', 'Authoritative'),
            ('humorous', 'Humorous'),
            ('inspirational', 'Inspirational'),
        ],
        default='professional'
    )
    
    # Content Preferences
    content_topics = models.JSONField(default=list, help_text="List of topics to focus on")
    keywords = models.JSONField(default=list, help_text="Important keywords for your business")
    avoid_topics = models.JSONField(default=list, help_text="Topics to avoid")
    
    # Language and Localization
    primary_language = models.CharField(max_length=10, default='az', help_text="Primary language for content")
    
    # AI Content Generation Settings
    posts_to_generate = models.IntegerField(
        default=10, 
        help_text="Number of posts to generate at once (1-30)",
        validators=[MinValueValidator(1), MaxValueValidator(30)]
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'company_profiles'
        verbose_name = 'Company Profile'
        verbose_name_plural = 'Company Profiles'

    def __str__(self):
        return f"{self.company_name} - {self.user.email}"


class BrandVoice(models.Model):
    """AI prompt configurations for different brand voices"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='brand_voices')
    name = models.CharField(max_length=100)
    tone = models.CharField(
        max_length=50,
        choices=[
            ('professional', 'Professional'),
            ('casual', 'Casual'),
            ('friendly', 'Friendly'),
            ('authoritative', 'Authoritative'),
            ('humorous', 'Humorous'),
            ('inspirational', 'Inspirational'),
        ],
        default='professional'
    )
    industry = models.CharField(max_length=100, blank=True)
    target_audience = models.CharField(max_length=200, blank=True)
    custom_instructions = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'brand_voices'
        verbose_name = 'Brand Voice'
        verbose_name_plural = 'Brand Voices'
        unique_together = ['user', 'name']

    def __str__(self):
        return f"{self.user.email} - {self.name} ({self.tone})"

    def save(self, *args, **kwargs):
        # Ensure only one default brand voice per user
        if self.is_default:
            BrandVoice.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)