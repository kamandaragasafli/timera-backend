import uuid
from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet
import base64


class SocialAccount(models.Model):
    """Connected social media accounts for users"""
    
    PLATFORM_CHOICES = [
        ('linkedin', 'LinkedIn'),
        ('telegram', 'Telegram'),
        ('instagram', 'Instagram'),
        ('twitter', 'Twitter/X'),
        ('facebook', 'Facebook'),
        ('youtube', 'YouTube'),
        ('tiktok', 'TikTok'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='social_accounts')
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    platform_user_id = models.CharField(max_length=100)
    platform_username = models.CharField(max_length=100, blank=True)
    display_name = models.CharField(max_length=200, blank=True)
    profile_picture_url = models.URLField(max_length=500, blank=True)  # Reduced to 500 to match DB constraint
    
    # Encrypted token storage
    access_token_encrypted = models.TextField()
    refresh_token_encrypted = models.TextField(blank=True)
    
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_used = models.DateTimeField(null=True, blank=True)
    
    # Platform-specific settings
    settings = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'social_accounts'
        verbose_name = 'Social Account'
        verbose_name_plural = 'Social Accounts'
        unique_together = ['user', 'platform', 'platform_user_id']

    def __str__(self):
        return f"{self.user.email} - {self.get_platform_display()} ({self.platform_username})"

    def _get_cipher(self):
        """Get encryption cipher using Django secret key"""
        key = base64.urlsafe_b64encode(settings.SECRET_KEY[:32].encode().ljust(32)[:32])
        return Fernet(key)

    def set_access_token(self, token):
        """Encrypt and store access token"""
        cipher = self._get_cipher()
        self.access_token_encrypted = cipher.encrypt(token.encode()).decode()

    def get_access_token(self):
        """Decrypt and return access token"""
        if not self.access_token_encrypted:
            return None
        cipher = self._get_cipher()
        return cipher.decrypt(self.access_token_encrypted.encode()).decode()

    def set_refresh_token(self, token):
        """Encrypt and store refresh token"""
        if not token:
            return
        cipher = self._get_cipher()
        self.refresh_token_encrypted = cipher.encrypt(token.encode()).decode()

    def get_refresh_token(self):
        """Decrypt and return refresh token"""
        if not self.refresh_token_encrypted:
            return None
        cipher = self._get_cipher()
        return cipher.decrypt(self.refresh_token_encrypted.encode()).decode()

    @property
    def is_token_expired(self):
        """Check if access token is expired"""
        if not self.expires_at:
            return False
        from django.utils import timezone
        return timezone.now() >= self.expires_at
