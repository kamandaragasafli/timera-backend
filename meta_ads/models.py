"""
Meta Ads Models
Facebook & Instagram Ad Campaign Management
"""

import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from cryptography.fernet import Fernet
import base64


class MetaAdAccount(models.Model):
    """Meta (Facebook/Instagram) Ad Account"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='meta_ad_accounts')
    
    account_id = models.CharField(max_length=100, unique=True, help_text="Meta Ad Account ID")
    name = models.CharField(max_length=255)
    currency = models.CharField(max_length=10, default='USD')
    timezone = models.CharField(max_length=50, default='UTC')
    
    # Encrypted access token
    access_token_encrypted = models.TextField()
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('ACTIVE', 'Active'),
            ('DISABLED', 'Disabled'),
            ('UNSETTLED', 'Unsettled'),
            ('CLOSED', 'Closed'),
        ],
        default='ACTIVE'
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'meta_ad_accounts'
        verbose_name = 'Meta Ad Account'
        verbose_name_plural = 'Meta Ad Accounts'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.account_id})"
    
    def _get_cipher(self):
        """Get encryption cipher"""
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


class MetaCampaign(models.Model):
    """Meta Ad Campaign"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(MetaAdAccount, on_delete=models.CASCADE, related_name='campaigns')
    
    campaign_id = models.CharField(max_length=100, unique=True, help_text="Meta Campaign ID")
    name = models.CharField(max_length=255)
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('ACTIVE', 'Active'),
            ('PAUSED', 'Paused'),
            ('DELETED', 'Deleted'),
            ('ARCHIVED', 'Archived'),
        ],
        default='PAUSED'
    )
    
    objective = models.CharField(max_length=50, help_text="Campaign objective")
    daily_budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    lifetime_budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    
    meta_created_time = models.DateTimeField(null=True, blank=True, help_text="Created time from Meta")
    meta_updated_time = models.DateTimeField(null=True, blank=True, help_text="Updated time from Meta")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'meta_campaigns'
        verbose_name = 'Meta Campaign'
        verbose_name_plural = 'Meta Campaigns'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.status})"


class MetaAdSet(models.Model):
    """Meta Ad Set"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(MetaCampaign, on_delete=models.CASCADE, related_name='ad_sets')
    
    ad_set_id = models.CharField(max_length=100, unique=True, help_text="Meta Ad Set ID")
    name = models.CharField(max_length=255)
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('ACTIVE', 'Active'),
            ('PAUSED', 'Paused'),
            ('DELETED', 'Deleted'),
            ('ARCHIVED', 'Archived'),
        ],
        default='PAUSED'
    )
    
    daily_budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    lifetime_budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    
    billing_event = models.CharField(max_length=50, blank=True, help_text="IMPRESSIONS, CLICKS, etc.")
    optimization_goal = models.CharField(max_length=50, blank=True, help_text="REACH, CLICKS, etc.")
    
    targeting = models.JSONField(default=dict, blank=True, help_text="Targeting criteria")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'meta_ad_sets'
        verbose_name = 'Meta Ad Set'
        verbose_name_plural = 'Meta Ad Sets'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.status})"


class MetaAd(models.Model):
    """Meta Ad"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ad_set = models.ForeignKey(MetaAdSet, on_delete=models.CASCADE, related_name='ads')
    
    ad_id = models.CharField(max_length=100, unique=True, help_text="Meta Ad ID")
    name = models.CharField(max_length=255)
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('ACTIVE', 'Active'),
            ('PAUSED', 'Paused'),
            ('DELETED', 'Deleted'),
            ('ARCHIVED', 'Archived'),
        ],
        default='PAUSED'
    )
    
    creative = models.JSONField(default=dict, blank=True, help_text="Ad creative data")
    
    meta_created_time = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'meta_ads'
        verbose_name = 'Meta Ad'
        verbose_name_plural = 'Meta Ads'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.status})"


class MetaInsight(models.Model):
    """Meta Insights - Analytics Cache"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Foreign keys - at least one must be set
    account = models.ForeignKey(MetaAdAccount, on_delete=models.CASCADE, related_name='insights', null=True, blank=True)
    campaign = models.ForeignKey(MetaCampaign, on_delete=models.CASCADE, related_name='insights', null=True, blank=True)
    ad_set = models.ForeignKey(MetaAdSet, on_delete=models.CASCADE, related_name='insights', null=True, blank=True)
    ad = models.ForeignKey(MetaAd, on_delete=models.CASCADE, related_name='insights', null=True, blank=True)
    
    # Date range
    date_start = models.DateField()
    date_stop = models.DateField()
    
    # Key metrics
    impressions = models.BigIntegerField(default=0)
    reach = models.BigIntegerField(default=0)
    clicks = models.BigIntegerField(default=0)
    spend = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Calculated metrics
    cpm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Cost per 1000 impressions")
    cpc = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Cost per click")
    ctr = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Click-through rate %")
    
    # Conversions
    conversions = models.IntegerField(default=0)
    cost_per_conversion = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Additional data
    metrics_data = models.JSONField(default=dict, blank=True, help_text="Additional metrics")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'meta_insights'
        verbose_name = 'Meta Insight'
        verbose_name_plural = 'Meta Insights'
        ordering = ['-date_start']
        # Ensure unique insights per date range per object
        unique_together = [
            ['account', 'date_start', 'date_stop'],
            ['campaign', 'date_start', 'date_stop'],
            ['ad_set', 'date_start', 'date_stop'],
            ['ad', 'date_start', 'date_stop'],
        ]
    
    def __str__(self):
        target = self.account or self.campaign or self.ad_set or self.ad
        return f"Insights: {target} ({self.date_start} - {self.date_stop})"
