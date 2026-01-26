"""
Post Analytics Service
Fetches engagement metrics from social media platforms
"""

import logging
import requests
from django.utils import timezone
from .models import PostPlatform, PostPerformance

logger = logging.getLogger(__name__)


class PostAnalyticsService:
    """Service to fetch and update post engagement metrics"""
    
    def __init__(self, access_token):
        """Initialize with platform access token"""
        self.access_token = access_token
        self.base_url = "https://graph.facebook.com/v18.0"
    
    def fetch_facebook_post_metrics(self, post_id):
        """Fetch metrics for a Facebook Page post"""
        try:
            # Get post insights
            url = f"{self.base_url}/{post_id}"
            params = {
                'fields': 'id,message,created_time,likes.summary(true),comments.summary(true),shares,reactions.summary(true)',
                'access_token': self.access_token
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            post_data = response.json()
            
            # Get insights (reach, impressions)
            insights_url = f"{self.base_url}/{post_id}/insights"
            insights_params = {
                'metric': 'post_impressions,post_impressions_unique,post_engaged_users',
                'access_token': self.access_token
            }
            
            insights_response = requests.get(insights_url, params=insights_params)
            insights_data = {}
            if insights_response.status_code == 200:
                insights_list = insights_response.json().get('data', [])
                for insight in insights_list:
                    metric_name = insight.get('name')
                    values = insight.get('values', [])
                    if values:
                        insights_data[metric_name] = values[0].get('value', 0)
            
            # Extract metrics
            likes = post_data.get('likes', {}).get('summary', {}).get('total_count', 0)
            comments = post_data.get('comments', {}).get('summary', {}).get('total_count', 0)
            shares = post_data.get('shares', {}).get('count', 0) if post_data.get('shares') else 0
            reactions = post_data.get('reactions', {}).get('summary', {}).get('total_count', 0)
            
            # Use reactions if available, otherwise likes
            total_likes = reactions if reactions > likes else likes
            
            impressions = insights_data.get('post_impressions', 0)
            reach = insights_data.get('post_impressions_unique', 0)
            engaged_users = insights_data.get('post_engaged_users', 0)
            
            return {
                'likes': total_likes,
                'comments': comments,
                'shares': shares,
                'impressions': impressions,
                'reach': reach,
                'engaged_users': engaged_users,
                'link_clicks': 0,  # Would need separate API call
            }
            
        except Exception as e:
            logger.error(f"Error fetching Facebook post metrics: {e}")
            raise
    
    def fetch_instagram_post_metrics(self, post_id):
        """Fetch metrics for an Instagram Business post"""
        try:
            # Get post insights
            url = f"{self.base_url}/{post_id}"
            params = {
                'fields': 'id,caption,like_count,comments_count,timestamp',
                'access_token': self.access_token
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            post_data = response.json()
            
            # Get insights (reach, impressions, saves)
            insights_url = f"{self.base_url}/{post_id}/insights"
            insights_params = {
                'metric': 'impressions,reach,saved,engagement',
                'access_token': self.access_token
            }
            
            insights_response = requests.get(insights_url, params=insights_params)
            insights_data = {}
            if insights_response.status_code == 200:
                insights_list = insights_response.json().get('data', [])
                for insight in insights_list:
                    metric_name = insight.get('name')
                    values = insight.get('values', [])
                    if values:
                        insights_data[metric_name] = values[0].get('value', 0)
            
            return {
                'likes': post_data.get('like_count', 0),
                'comments': post_data.get('comments_count', 0),
                'shares': 0,  # Instagram doesn't provide shares
                'saves': insights_data.get('saved', 0),
                'impressions': insights_data.get('impressions', 0),
                'reach': insights_data.get('reach', 0),
                'engaged_users': insights_data.get('engagement', 0),
                'link_clicks': 0,  # Would need separate API call for link in bio
            }
            
        except Exception as e:
            logger.error(f"Error fetching Instagram post metrics: {e}")
            raise
    
    def update_post_performance(self, post_platform):
        """Update or create PostPerformance record for a PostPlatform"""
        if not post_platform.platform_post_id:
            logger.warning(f"PostPlatform {post_platform.id} has no platform_post_id")
            return None
        
        try:
            # Get access token from social account
            access_token = post_platform.social_account.get_access_token()
            self.access_token = access_token
            
            # Fetch metrics based on platform
            platform = post_platform.social_account.platform
            metrics = {}
            
            if platform == 'facebook':
                metrics = self.fetch_facebook_post_metrics(post_platform.platform_post_id)
            elif platform == 'instagram':
                metrics = self.fetch_instagram_post_metrics(post_platform.platform_post_id)
            else:
                logger.warning(f"Metrics fetching not implemented for platform: {platform}")
                return None
            
            # Update or create PostPerformance
            performance, created = PostPerformance.objects.update_or_create(
                post_platform=post_platform,
                defaults={
                    'likes': metrics.get('likes', 0),
                    'comments': metrics.get('comments', 0),
                    'shares': metrics.get('shares', 0),
                    'saves': metrics.get('saves', 0),
                    'impressions': metrics.get('impressions', 0),
                    'reach': metrics.get('reach', 0),
                    'link_clicks': metrics.get('link_clicks', 0),
                    'last_fetched_at': timezone.now(),
                    'additional_metrics': {
                        'engaged_users': metrics.get('engaged_users', 0),
                    }
                }
            )
            
            # Calculate engagement rate
            performance.calculate_engagement_rate()
            performance.save()
            
            logger.info(f"Updated performance metrics for PostPlatform {post_platform.id}")
            return performance
            
        except Exception as e:
            logger.error(f"Error updating post performance: {e}")
            return None

