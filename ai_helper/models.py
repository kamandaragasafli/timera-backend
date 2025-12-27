import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class ProfileAnalysis(models.Model):
    """Cache for social media profile analysis results"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile_analyses',
        null=True,
        blank=True
    )
    
    # Profile identification
    profile_url = models.URLField(max_length=500, db_index=True, help_text="Original profile URL")
    profile_username = models.CharField(max_length=200, blank=True, db_index=True)
    platform = models.CharField(max_length=50, blank=True, help_text="instagram, facebook, linkedin, etc.")
    
    # Cached data
    preview_data = models.JSONField(help_text="OG preview and scraped profile data")
    smm_analysis = models.JSONField(help_text="AI-generated SMM analysis")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_accessed = models.DateTimeField(auto_now=True, help_text="Last time this cache was accessed")
    access_count = models.IntegerField(default=1, help_text="Number of times this cache was accessed")
    
    class Meta:
        db_table = 'profile_analyses'
        verbose_name = 'Profile Analysis'
        verbose_name_plural = 'Profile Analyses'
        ordering = ['-last_accessed']
        indexes = [
            models.Index(fields=['profile_url']),
            models.Index(fields=['profile_username', 'platform']),
            models.Index(fields=['-last_accessed']),
        ]
        unique_together = [['profile_url']]  # One cache per URL
    
    def __str__(self):
        return f"Profile Analysis: {self.profile_username or self.profile_url} ({self.platform})"
    
    def increment_access(self):
        """Increment access count and update last_accessed"""
        self.access_count += 1
        self.last_accessed = timezone.now()
        self.save(update_fields=['access_count', 'last_accessed'])

