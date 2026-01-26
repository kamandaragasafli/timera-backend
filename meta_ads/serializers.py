"""
Meta Ads Serializers
"""

from rest_framework import serializers
from .models import MetaAdAccount, MetaCampaign, MetaAdSet, MetaAd, MetaInsight


class MetaAdAccountSerializer(serializers.ModelSerializer):
    """Serializer for Meta Ad Account"""
    
    class Meta:
        model = MetaAdAccount
        fields = [
            'id', 'account_id', 'name', 'currency', 'timezone',
            'status', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MetaCampaignSerializer(serializers.ModelSerializer):
    """Serializer for Meta Campaign"""
    
    account_name = serializers.CharField(source='account.name', read_only=True)
    
    class Meta:
        model = MetaCampaign
        fields = [
            'id', 'campaign_id', 'name', 'status', 'objective',
            'daily_budget', 'lifetime_budget', 'start_time', 'end_time',
            'meta_created_time', 'meta_updated_time',
            'account', 'account_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'campaign_id', 'account_name', 'created_at', 'updated_at']


class MetaAdSetSerializer(serializers.ModelSerializer):
    """Serializer for Meta Ad Set"""
    
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)
    
    class Meta:
        model = MetaAdSet
        fields = [
            'id', 'ad_set_id', 'name', 'status',
            'daily_budget', 'lifetime_budget',
            'billing_event', 'optimization_goal', 'targeting',
            'campaign', 'campaign_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'ad_set_id', 'campaign_name', 'created_at', 'updated_at']


class MetaAdSerializer(serializers.ModelSerializer):
    """Serializer for Meta Ad"""
    
    ad_set_name = serializers.CharField(source='ad_set.name', read_only=True)
    campaign_name = serializers.CharField(source='ad_set.campaign.name', read_only=True)
    
    class Meta:
        model = MetaAd
        fields = [
            'id', 'ad_id', 'name', 'status', 'creative',
            'meta_created_time', 'ad_set', 'ad_set_name', 'campaign_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'ad_id', 'ad_set_name', 'campaign_name', 'created_at', 'updated_at']


class MetaInsightSerializer(serializers.ModelSerializer):
    """Serializer for Meta Insights"""
    
    class Meta:
        model = MetaInsight
        fields = [
            'id', 'date_start', 'date_stop',
            'impressions', 'reach', 'clicks', 'spend',
            'cpm', 'cpc', 'ctr', 'conversions', 'cost_per_conversion',
            'metrics_data', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# Request Serializers
class CampaignCreateSerializer(serializers.Serializer):
    """Serializer for creating a campaign"""
    
    account_id = serializers.CharField()
    name = serializers.CharField(max_length=255)
    objective = serializers.ChoiceField(choices=[
        ('OUTCOME_TRAFFIC', 'Traffic'),
        ('OUTCOME_ENGAGEMENT', 'Engagement'),
        ('OUTCOME_LEADS', 'Leads'),
        ('OUTCOME_SALES', 'Sales'),
        ('OUTCOME_AWARENESS', 'Awareness'),
    ])
    status = serializers.ChoiceField(choices=['ACTIVE', 'PAUSED'], default='PAUSED')
    daily_budget = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    lifetime_budget = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)


class InsightsRequestSerializer(serializers.Serializer):
    """Serializer for insights request"""
    
    account_id = serializers.CharField(required=False, allow_null=True)
    campaign_id = serializers.CharField(required=False, allow_null=True)
    ad_set_id = serializers.CharField(required=False, allow_null=True)
    ad_id = serializers.CharField(required=False, allow_null=True)
    
    date_preset = serializers.ChoiceField(
        choices=['today', 'yesterday', 'last_7d', 'last_14d', 'last_30d', 'last_90d', 'this_month', 'last_month'],
        default='last_7d',
        required=False
    )
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    
    def validate(self, data):
        # At least one ID must be provided
        if not any([data.get('account_id'), data.get('campaign_id'), data.get('ad_set_id'), data.get('ad_id')]):
            raise serializers.ValidationError("One of account_id, campaign_id, ad_set_id, or ad_id is required")
        return data

