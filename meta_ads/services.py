"""
Meta Marketing API Service
Simplified service layer for Meta Ads
"""

import logging
import requests

logger = logging.getLogger(__name__)


class MetaAPIService:
    """Simplified Meta Marketing API Service"""
    
    BASE_URL = "https://graph.facebook.com/v18.0"
    
    def __init__(self, access_token):
        """Initialize with access token"""
        self.access_token = access_token
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    
    def _request(self, method, endpoint, **kwargs):
        """Make API request"""
        url = f"{self.BASE_URL}/{endpoint}"
        kwargs['headers'] = self.headers
        
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
    
    # Ad Accounts
    def get_ad_accounts(self, user_id='me'):
        """Get ad accounts for user"""
        try:
            data = self._request('GET', f'{user_id}/adaccounts', params={
                'fields': 'id,name,currency,timezone_name,account_status'
            })
            return data.get('data', [])
        except Exception as e:
            logger.error(f"Error getting ad accounts: {e}")
            raise
    
    # Campaigns
    def get_campaigns(self, account_id, fields=None):
        """Get campaigns for ad account"""
        if fields is None:
            fields = 'id,name,status,objective,daily_budget,lifetime_budget,start_time,stop_time,created_time,updated_time'
        
        try:
            data = self._request('GET', f'act_{account_id}/campaigns', params={'fields': fields})
            return data.get('data', [])
        except Exception as e:
            logger.error(f"Error getting campaigns: {e}")
            raise
    
    def create_campaign(self, account_id, name, objective, status='PAUSED', **kwargs):
        """Create new campaign"""
        try:
            params = {
                'name': name,
                'objective': objective,
                'status': status,
                **kwargs
            }
            return self._request('POST', f'act_{account_id}/campaigns', json=params)
        except Exception as e:
            logger.error(f"Error creating campaign: {e}")
            raise
    
    def update_campaign(self, campaign_id, **kwargs):
        """Update campaign"""
        try:
            return self._request('POST', campaign_id, json=kwargs)
        except Exception as e:
            logger.error(f"Error updating campaign: {e}")
            raise
    
    # Insights
    def get_insights(self, object_id, date_preset='last_7d', fields=None, level='account'):
        """Get insights for account/campaign/adset/ad"""
        if fields is None:
            fields = 'impressions,reach,clicks,spend,cpm,cpc,ctr,conversions'
        
        try:
            params = {
                'fields': fields,
                'date_preset': date_preset,
                'level': level
            }
            data = self._request('GET', f'{object_id}/insights', params=params)
            return data.get('data', [])
        except Exception as e:
            logger.error(f"Error getting insights: {e}")
            raise
    
    # Ad Sets
    def get_ad_sets(self, campaign_id=None, account_id=None, fields=None):
        """Get ad sets"""
        if fields is None:
            fields = 'id,name,status,daily_budget,lifetime_budget,billing_event,optimization_goal,targeting'
        
        try:
            if campaign_id:
                endpoint = f'{campaign_id}/adsets'
            elif account_id:
                endpoint = f'act_{account_id}/adsets'
            else:
                raise ValueError("campaign_id or account_id required")
            
            data = self._request('GET', endpoint, params={'fields': fields})
            return data.get('data', [])
        except Exception as e:
            logger.error(f"Error getting ad sets: {e}")
            raise
    
    # Ads
    def get_ads(self, ad_set_id=None, account_id=None, fields=None):
        """Get ads"""
        if fields is None:
            fields = 'id,name,status,creative,created_time'
        
        try:
            if ad_set_id:
                endpoint = f'{ad_set_id}/ads'
            elif account_id:
                endpoint = f'act_{account_id}/ads'
            else:
                raise ValueError("ad_set_id or account_id required")
            
            data = self._request('GET', endpoint, params={'fields': fields})
            return data.get('data', [])
        except Exception as e:
            logger.error(f"Error getting ads: {e}")
            raise
    
    def update_ad_set(self, ad_set_id, **kwargs):
        """Update ad set"""
        try:
            return self._request('POST', ad_set_id, json=kwargs)
        except Exception as e:
            logger.error(f"Error updating ad set: {e}")
            raise
    
    def update_ad(self, ad_id, **kwargs):
        """Update ad"""
        try:
            return self._request('POST', ad_id, json=kwargs)
        except Exception as e:
            logger.error(f"Error updating ad: {e}")
            raise

