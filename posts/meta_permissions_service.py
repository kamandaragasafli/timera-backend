"""
Meta Permissions Service
Bu servis Meta Business Suite icazələrinin hamısını real kodda istifadə edir
Hər bir icazə üçün real API funksiyaları
"""

import requests
import logging
from datetime import datetime, timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)


class MetaPermissionsService:
    """
    Meta Business Suite API Service - Bütün icazələri əhatə edir
    
    İcazələr:
    - pages_manage_posts: Facebook Pages-ə post paylaşımı
    - instagram_content_publish: Instagram-a post paylaşımı
    - pages_read_engagement: Page engagement statistikaları
    - instagram_business_manage_messages: Instagram biznes mesajları
    - instagram_basic: Əsas Instagram məlumatları
    - instagram_manage_messages: Instagram mesajlarını idarə etmək
    - business_management: Business account-ları idarə etmək
    - ads_read: Ads məlumatlarını oxumaq
    - ads_management: Ads yaratmaq və idarə etmək
    - pages_show_list: Facebook Pages siyahısını göstərmək
    """
    
    BASE_URL = "https://graph.facebook.com/v21.0"
    
    def __init__(self, access_token):
        """
        Initialize with Meta access token
        
        Args:
            access_token: Meta Business Suite access token
        """
        self.access_token = access_token
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    
    # ==================== PAGES_SHOW_LIST ====================
    
    def get_user_pages(self, user_id='me'):
        """
        Get list of Facebook Pages user manages
        İcazə: pages_show_list
        
        Args:
            user_id: User ID (default 'me' for current user)
            
        Returns:
            list: List of pages with details
        """
        try:
            url = f"{self.BASE_URL}/{user_id}/accounts"
            params = {
                'access_token': self.access_token,
                'fields': 'id,name,access_token,category,fan_count,followers_count,picture'
            }
            
            logger.info(f"📄 Fetching Facebook Pages for user {user_id}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            pages = data.get('data', [])
            
            logger.info(f"✅ Found {len(pages)} Facebook Pages")
            return {
                'success': True,
                'pages': pages,
                'count': len(pages)
            }
            
        except Exception as e:
            logger.error(f"❌ Error fetching pages: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'pages': []
            }
    
    # ==================== PAGES_MANAGE_POSTS ====================
    
    def publish_page_post(self, page_id, message, image_url=None, page_access_token=None):
        """
        Publish post to Facebook Page
        İcazə: pages_manage_posts
        
        Args:
            page_id: Facebook Page ID
            message: Post text
            image_url: Optional image URL
            page_access_token: Page-specific access token (if available)
            
        Returns:
            dict: Post result with post_id
        """
        try:
            token = page_access_token or self.access_token
            
            if image_url:
                # Post with photo
                url = f"{self.BASE_URL}/{page_id}/photos"
                data = {
                    'url': image_url,
                    'message': message,
                    'access_token': token
                }
            else:
                # Text-only post
                url = f"{self.BASE_URL}/{page_id}/feed"
                data = {
                    'message': message,
                    'access_token': token
                }
            
            logger.info(f"📝 Publishing post to Facebook Page {page_id}")
            response = requests.post(url, data=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            post_id = result.get('id')
            
            logger.info(f"✅ Post published successfully: {post_id}")
            return {
                'success': True,
                'post_id': post_id,
                'platform': 'facebook'
            }
            
        except Exception as e:
            logger.error(f"❌ Error publishing to Facebook: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # ==================== PAGES_READ_ENGAGEMENT ====================
    
    def get_page_engagement_insights(self, page_id, page_access_token=None, period='day', since=None, until=None):
        """
        Get Facebook Page engagement insights
        İcazə: pages_read_engagement
        
        Args:
            page_id: Facebook Page ID
            page_access_token: Page-specific access token
            period: 'day', 'week', or 'days_28'
            since: Start date (YYYY-MM-DD)
            until: End date (YYYY-MM-DD)
            
        Returns:
            dict: Engagement insights (reach, impressions, engagement)
        """
        try:
            token = page_access_token or self.access_token
            url = f"{self.BASE_URL}/{page_id}/insights"
            
            # Default to last 7 days if no dates provided
            if not since:
                since = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            if not until:
                until = datetime.now().strftime('%Y-%m-%d')
            
            params = {
                'access_token': token,
                'metric': 'page_impressions,page_impressions_unique,page_engaged_users,page_post_engagements,page_fans,page_fan_adds,page_fan_removes',
                'period': period,
                'since': since,
                'until': until
            }
            
            logger.info(f"📊 Fetching engagement insights for page {page_id}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            insights_data = result.get('data', [])
            
            # Parse insights into readable format
            insights = {}
            for metric in insights_data:
                metric_name = metric.get('name')
                values = metric.get('values', [])
                if values:
                    insights[metric_name] = values[-1].get('value', 0)
            
            logger.info(f"✅ Retrieved {len(insights)} engagement metrics")
            return {
                'success': True,
                'insights': insights,
                'period': period,
                'date_range': {'since': since, 'until': until}
            }
            
        except Exception as e:
            logger.error(f"❌ Error fetching page insights: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'insights': {}
            }
    
    def get_page_posts_insights(self, page_id, page_access_token=None, limit=25):
        """
        Get insights for individual posts on Facebook Page
        İcazə: pages_read_engagement
        
        Args:
            page_id: Facebook Page ID
            page_access_token: Page-specific access token
            limit: Number of posts to retrieve
            
        Returns:
            dict: List of posts with engagement data
        """
        try:
            token = page_access_token or self.access_token
            url = f"{self.BASE_URL}/{page_id}/posts"
            
            params = {
                'access_token': token,
                'fields': 'id,message,created_time,likes.summary(true),comments.summary(true),shares,reactions.summary(true)',
                'limit': limit
            }
            
            logger.info(f"📄 Fetching posts insights for page {page_id}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            posts = result.get('data', [])
            
            # Format posts with engagement metrics
            formatted_posts = []
            for post in posts:
                formatted_posts.append({
                    'post_id': post.get('id'),
                    'message': post.get('message', '')[:100],
                    'created_time': post.get('created_time'),
                    'likes': post.get('likes', {}).get('summary', {}).get('total_count', 0),
                    'comments': post.get('comments', {}).get('summary', {}).get('total_count', 0),
                    'shares': post.get('shares', {}).get('count', 0),
                    'reactions': post.get('reactions', {}).get('summary', {}).get('total_count', 0),
                })
            
            logger.info(f"✅ Retrieved {len(formatted_posts)} posts with insights")
            return {
                'success': True,
                'posts': formatted_posts,
                'count': len(formatted_posts)
            }
            
        except Exception as e:
            logger.error(f"❌ Error fetching posts insights: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'posts': []
            }
    
    # ==================== INSTAGRAM_BASIC ====================
    
    def get_instagram_account_info(self, instagram_account_id):
        """
        Get basic Instagram Business Account information
        İcazə: instagram_basic
        
        Args:
            instagram_account_id: Instagram Business Account ID
            
        Returns:
            dict: Account info (username, followers, media count)
        """
        try:
            url = f"{self.BASE_URL}/{instagram_account_id}"
            params = {
                'access_token': self.access_token,
                'fields': 'id,username,name,profile_picture_url,followers_count,follows_count,media_count,biography,website'
            }
            
            logger.info(f"📱 Fetching Instagram account info for {instagram_account_id}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            account_info = response.json()
            
            logger.info(f"✅ Retrieved Instagram account: @{account_info.get('username')}")
            return {
                'success': True,
                'account': account_info
            }
            
        except Exception as e:
            logger.error(f"❌ Error fetching Instagram account info: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'account': {}
            }
    
    def get_instagram_media(self, instagram_account_id, limit=25):
        """
        Get Instagram media (posts) for account
        İcazə: instagram_basic
        
        Args:
            instagram_account_id: Instagram Business Account ID
            limit: Number of media items to retrieve
            
        Returns:
            dict: List of media items
        """
        try:
            url = f"{self.BASE_URL}/{instagram_account_id}/media"
            params = {
                'access_token': self.access_token,
                'fields': 'id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,like_count,comments_count',
                'limit': limit
            }
            
            logger.info(f"📷 Fetching Instagram media for account {instagram_account_id}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            media_items = result.get('data', [])
            
            logger.info(f"✅ Retrieved {len(media_items)} Instagram media items")
            return {
                'success': True,
                'media': media_items,
                'count': len(media_items)
            }
            
        except Exception as e:
            logger.error(f"❌ Error fetching Instagram media: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'media': []
            }
    
    # ==================== INSTAGRAM_CONTENT_PUBLISH ====================
    
    def publish_instagram_post(self, instagram_account_id, image_url, caption):
        """
        Publish post to Instagram Business Account
        İcazə: instagram_content_publish
        
        Args:
            instagram_account_id: Instagram Business Account ID
            image_url: Public HTTPS URL of image
            caption: Post caption with hashtags
            
        Returns:
            dict: Post result with media_id
        """
        try:
            # Step 1: Create media container
            container_url = f"{self.BASE_URL}/{instagram_account_id}/media"
            container_data = {
                'image_url': image_url,
                'caption': caption,
                'access_token': self.access_token
            }
            
            logger.info(f"📸 Creating Instagram media container")
            container_response = requests.post(container_url, data=container_data, timeout=30)
            container_response.raise_for_status()
            
            container_result = container_response.json()
            creation_id = container_result.get('id')
            
            if not creation_id:
                raise Exception("Failed to create media container")
            
            logger.info(f"✅ Media container created: {creation_id}")
            
            # Step 2: Publish media
            publish_url = f"{self.BASE_URL}/{instagram_account_id}/media_publish"
            publish_data = {
                'creation_id': creation_id,
                'access_token': self.access_token
            }
            
            logger.info(f"📤 Publishing Instagram post")
            publish_response = requests.post(publish_url, data=publish_data, timeout=30)
            publish_response.raise_for_status()
            
            publish_result = publish_response.json()
            media_id = publish_result.get('id')
            
            logger.info(f"✅ Instagram post published: {media_id}")
            return {
                'success': True,
                'media_id': media_id,
                'platform': 'instagram'
            }
            
        except Exception as e:
            logger.error(f"❌ Error publishing to Instagram: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # ==================== INSTAGRAM_MANAGE_MESSAGES ====================
    
    def get_instagram_conversations(self, instagram_account_id, limit=25):
        """
        Get Instagram Direct message conversations
        İcazə: instagram_manage_messages, instagram_business_manage_messages
        
        Args:
            instagram_account_id: Instagram Business Account ID
            limit: Number of conversations to retrieve
            
        Returns:
            dict: List of conversations
        """
        try:
            url = f"{self.BASE_URL}/{instagram_account_id}/conversations"
            params = {
                'access_token': self.access_token,
                'fields': 'id,updated_time,message_count,unread_count,participants{id,username,name}',
                'limit': limit
            }
            
            logger.info(f"💬 Fetching Instagram conversations for account {instagram_account_id}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            conversations = result.get('data', [])
            
            # Add snippet field if not present (for preview)
            for conv in conversations:
                if 'snippet' not in conv:
                    conv['snippet'] = ''
            
            logger.info(f"✅ Retrieved {len(conversations)} Instagram conversations")
            return {
                'success': True,
                'conversations': conversations,
                'count': len(conversations)
            }
            
        except requests.exceptions.HTTPError as e:
            error_msg = str(e)
            error_code = None
            if hasattr(e.response, 'text'):
                try:
                    error_data = e.response.json()
                    error_info = error_data.get('error', {})
                    error_msg = error_info.get('message', error_msg)
                    error_code = error_info.get('code')
                    
                    # Special handling for capability error
                    if error_code == 3 or 'capability' in error_msg.lower():
                        error_msg = (
                            "Instagram Messaging capability is not enabled for this app. "
                            "Please enable it in Meta App Dashboard: "
                            "Settings > Basic > Add Platform > Instagram Messaging. "
                            "Then submit instagram_manage_messages permission for App Review."
                        )
                except:
                    error_msg = e.response.text[:200]
            logger.error(f"❌ Error fetching Instagram conversations: {error_msg} (Code: {error_code})")
            return {
                'success': False,
                'error': error_msg,
                'error_code': error_code,
                'conversations': [],
                'help': 'Enable Instagram Messaging capability in Meta App Dashboard and request instagram_manage_messages permission'
            }
        except Exception as e:
            logger.error(f"❌ Error fetching Instagram conversations: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'conversations': []
            }
    
    def get_instagram_messages(self, conversation_id, limit=50):
        """
        Get messages from Instagram conversation
        İcazə: instagram_manage_messages, instagram_business_manage_messages
        
        Args:
            conversation_id: Instagram conversation ID
            limit: Number of messages to retrieve
            
        Returns:
            dict: List of messages
        """
        try:
            url = f"{self.BASE_URL}/{conversation_id}/messages"
            params = {
                'access_token': self.access_token,
                'fields': 'id,created_time,from{id,username,name},message',
                'limit': limit
            }
            
            logger.info(f"📩 Fetching messages from conversation {conversation_id}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            messages_data = result.get('data', [])
            
            logger.info(f"✅ Retrieved {len(messages_data)} messages")
            return {
                'success': True,
                'messages': messages_data,
                'count': len(messages_data)
            }
            
        except requests.exceptions.HTTPError as e:
            error_msg = str(e)
            if hasattr(e.response, 'text'):
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('error', {}).get('message', error_msg)
                except:
                    error_msg = e.response.text[:200]
            logger.error(f"❌ Error fetching Instagram messages: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'messages': []
            }
        except Exception as e:
            logger.error(f"❌ Error fetching Instagram messages: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'messages': []
            }
    
    def send_instagram_message(self, instagram_account_id, recipient_id, message_text):
        """
        Send message to Instagram user
        İcazə: instagram_manage_messages, instagram_business_manage_messages
        
        Args:
            instagram_account_id: Instagram Business Account ID
            recipient_id: Recipient's Instagram User ID
            message_text: Message text
            
        Returns:
            dict: Send result
        """
        try:
            url = f"{self.BASE_URL}/{instagram_account_id}/messages"
            data = {
                'recipient': {'id': recipient_id},
                'message': {'text': message_text},
                'access_token': self.access_token
            }
            
            logger.info(f"📤 Sending Instagram message to {recipient_id}")
            response = requests.post(url, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            message_id = result.get('message_id')
            
            logger.info(f"✅ Instagram message sent: {message_id}")
            return {
                'success': True,
                'message_id': message_id
            }
            
        except Exception as e:
            logger.error(f"❌ Error sending Instagram message: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # ==================== FACEBOOK PAGES MESSAGES ====================
    
    def get_facebook_conversations(self, page_id, limit=25):
        """
        Get Facebook Page conversations (messages)
        İcazə: pages_messaging
        
        Args:
            page_id: Facebook Page ID
            limit: Number of conversations to retrieve
            
        Returns:
            dict: List of conversations
        """
        try:
            url = f"{self.BASE_URL}/{page_id}/conversations"
            params = {
                'access_token': self.access_token,
                'fields': 'id,updated_time,message_count,unread_count,participants,can_reply',
                'limit': limit
            }
            
            logger.info(f"💬 Fetching Facebook Page conversations for page {page_id}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            conversations = result.get('data', [])
            
            logger.info(f"✅ Retrieved {len(conversations)} Facebook conversations")
            return {
                'success': True,
                'conversations': conversations,
                'count': len(conversations)
            }
            
        except Exception as e:
            logger.error(f"❌ Error fetching Facebook conversations: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'conversations': []
            }
    
    def get_facebook_messages(self, conversation_id, limit=50):
        """
        Get messages from Facebook Page conversation
        İcazə: pages_messaging
        
        Args:
            conversation_id: Facebook conversation ID
            limit: Number of messages to retrieve
            
        Returns:
            dict: List of messages
        """
        try:
            url = f"{self.BASE_URL}/{conversation_id}/messages"
            params = {
                'access_token': self.access_token,
                'fields': 'id,created_time,from,to,message,attachments',
                'limit': limit
            }
            
            logger.info(f"📩 Fetching messages from Facebook conversation {conversation_id}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            messages_data = result.get('data', [])
            
            logger.info(f"✅ Retrieved {len(messages_data)} Facebook messages")
            return {
                'success': True,
                'messages': messages_data,
                'count': len(messages_data)
            }
            
        except Exception as e:
            logger.error(f"❌ Error fetching Facebook messages: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'messages': []
            }
    
    def send_facebook_message(self, page_id, recipient_id, message_text):
        """
        Send message to Facebook user via Page
        İcazə: pages_messaging
        
        Args:
            page_id: Facebook Page ID
            recipient_id: Recipient's Facebook User ID (PSID - Page Scoped ID)
            message_text: Message text
            
        Returns:
            dict: Send result
        """
        try:
            url = f"{self.BASE_URL}/{page_id}/messages"
            data = {
                'recipient': {'id': recipient_id},
                'message': {'text': message_text},
                'access_token': self.access_token
            }
            
            logger.info(f"📤 Sending Facebook message to {recipient_id}")
            response = requests.post(url, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            message_id = result.get('message_id')
            
            logger.info(f"✅ Facebook message sent: {message_id}")
            return {
                'success': True,
                'message_id': message_id
            }
            
        except Exception as e:
            logger.error(f"❌ Error sending Facebook message: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # ==================== BUSINESS_MANAGEMENT ====================
    
    def get_business_accounts(self, user_id='me'):
        """
        Get Business Accounts (Business Manager)
        İcazə: business_management
        
        Args:
            user_id: User ID (default 'me')
            
        Returns:
            dict: List of business accounts
        """
        try:
            url = f"{self.BASE_URL}/{user_id}/businesses"
            params = {
                'access_token': self.access_token,
                'fields': 'id,name,verification_status,created_time,primary_page'
            }
            
            logger.info(f"🏢 Fetching business accounts")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            businesses = result.get('data', [])
            
            logger.info(f"✅ Retrieved {len(businesses)} business accounts")
            return {
                'success': True,
                'businesses': businesses,
                'count': len(businesses)
            }
            
        except Exception as e:
            logger.error(f"❌ Error fetching business accounts: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'businesses': []
            }
    
    def get_instagram_accounts_for_page(self, page_id, page_access_token=None):
        """
        Get Instagram Business Accounts connected to Facebook Page
        İcazə: business_management, instagram_basic
        
        Args:
            page_id: Facebook Page ID
            page_access_token: Page-specific access token
            
        Returns:
            dict: Instagram account info
        """
        try:
            token = page_access_token or self.access_token
            url = f"{self.BASE_URL}/{page_id}"
            params = {
                'access_token': token,
                'fields': 'instagram_business_account{id,username,name,profile_picture_url,followers_count,follows_count,media_count}'
            }
            
            logger.info(f"📱 Fetching Instagram account for page {page_id}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            ig_account = result.get('instagram_business_account')
            
            if ig_account:
                logger.info(f"✅ Found Instagram account: @{ig_account.get('username')}")
                return {
                    'success': True,
                    'instagram_account': ig_account
                }
            else:
                logger.warning(f"⚠️ No Instagram account connected to page {page_id}")
                return {
                    'success': False,
                    'error': 'No Instagram account connected to this page',
                    'instagram_account': None
                }
            
        except Exception as e:
            logger.error(f"❌ Error fetching Instagram account: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'instagram_account': None
            }
    
    # ==================== ADS_READ ====================
    
    def get_ad_accounts(self, user_id='me'):
        """
        Get Ad Accounts
        İcazə: ads_read
        
        Args:
            user_id: User ID (default 'me')
            
        Returns:
            dict: List of ad accounts
        """
        try:
            url = f"{self.BASE_URL}/{user_id}/adaccounts"
            params = {
                'access_token': self.access_token,
                'fields': 'id,name,account_id,account_status,currency,timezone_name,balance,amount_spent,spend_cap'
            }
            
            logger.info(f"💰 Fetching ad accounts")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            ad_accounts = result.get('data', [])
            
            logger.info(f"✅ Retrieved {len(ad_accounts)} ad accounts")
            return {
                'success': True,
                'ad_accounts': ad_accounts,
                'count': len(ad_accounts)
            }
            
        except Exception as e:
            logger.error(f"❌ Error fetching ad accounts: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'ad_accounts': []
            }
    
    def get_campaigns(self, ad_account_id, limit=25):
        """
        Get Ad Campaigns
        İcazə: ads_read
        
        Args:
            ad_account_id: Ad Account ID
            limit: Number of campaigns to retrieve
            
        Returns:
            dict: List of campaigns
        """
        try:
            url = f"{self.BASE_URL}/act_{ad_account_id}/campaigns"
            params = {
                'access_token': self.access_token,
                'fields': 'id,name,status,objective,daily_budget,lifetime_budget,start_time,stop_time,created_time',
                'limit': limit
            }
            
            logger.info(f"📊 Fetching campaigns for ad account {ad_account_id}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            campaigns = result.get('data', [])
            
            logger.info(f"✅ Retrieved {len(campaigns)} campaigns")
            return {
                'success': True,
                'campaigns': campaigns,
                'count': len(campaigns)
            }
            
        except Exception as e:
            logger.error(f"❌ Error fetching campaigns: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'campaigns': []
            }
    
    def get_campaign_insights(self, campaign_id, date_preset='last_7d'):
        """
        Get insights for campaign
        İcazə: ads_read
        
        Args:
            campaign_id: Campaign ID
            date_preset: Date range preset
            
        Returns:
            dict: Campaign insights
        """
        try:
            url = f"{self.BASE_URL}/{campaign_id}/insights"
            params = {
                'access_token': self.access_token,
                'fields': 'impressions,reach,clicks,spend,cpm,cpc,ctr,conversions,cost_per_conversion',
                'date_preset': date_preset
            }
            
            logger.info(f"📈 Fetching insights for campaign {campaign_id}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            insights = result.get('data', [])
            
            logger.info(f"✅ Retrieved insights for campaign")
            return {
                'success': True,
                'insights': insights[0] if insights else {},
                'date_preset': date_preset
            }
            
        except Exception as e:
            logger.error(f"❌ Error fetching campaign insights: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'insights': {}
            }
    
    # ==================== ADS_MANAGEMENT ====================
    
    def create_campaign(self, ad_account_id, name, objective, status='PAUSED', daily_budget=None, lifetime_budget=None):
        """
        Create new ad campaign
        İcazə: ads_management
        
        Args:
            ad_account_id: Ad Account ID
            name: Campaign name
            objective: Campaign objective (REACH, TRAFFIC, CONVERSIONS, etc.)
            status: Campaign status (PAUSED, ACTIVE)
            daily_budget: Daily budget in cents (optional)
            lifetime_budget: Lifetime budget in cents (optional)
            
        Returns:
            dict: Created campaign info
        """
        try:
            url = f"{self.BASE_URL}/act_{ad_account_id}/campaigns"
            data = {
                'name': name,
                'objective': objective,
                'status': status,
                'access_token': self.access_token
            }
            
            if daily_budget:
                data['daily_budget'] = daily_budget
            if lifetime_budget:
                data['lifetime_budget'] = lifetime_budget
            
            logger.info(f"🎯 Creating campaign '{name}' for ad account {ad_account_id}")
            response = requests.post(url, data=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            campaign_id = result.get('id')
            
            logger.info(f"✅ Campaign created: {campaign_id}")
            return {
                'success': True,
                'campaign_id': campaign_id
            }
            
        except Exception as e:
            logger.error(f"❌ Error creating campaign: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_campaign(self, campaign_id, status=None, name=None, daily_budget=None):
        """
        Update existing campaign
        İcazə: ads_management
        
        Args:
            campaign_id: Campaign ID
            status: New status (ACTIVE, PAUSED)
            name: New name
            daily_budget: New daily budget
            
        Returns:
            dict: Update result
        """
        try:
            url = f"{self.BASE_URL}/{campaign_id}"
            data = {
                'access_token': self.access_token
            }
            
            if status:
                data['status'] = status
            if name:
                data['name'] = name
            if daily_budget:
                data['daily_budget'] = daily_budget
            
            logger.info(f"📝 Updating campaign {campaign_id}")
            response = requests.post(url, data=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            logger.info(f"✅ Campaign updated successfully")
            return {
                'success': True,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"❌ Error updating campaign: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_ad_creative(self, ad_account_id, name, object_story_spec, image_url=None, video_id=None):
        """
        Create ad creative
        İcazə: ads_management
        
        Args:
            ad_account_id: Ad Account ID
            name: Creative name
            object_story_spec: Creative specification
            image_url: Image URL (optional)
            video_id: Video ID (optional)
            
        Returns:
            dict: Created creative info
        """
        try:
            url = f"{self.BASE_URL}/act_{ad_account_id}/adcreatives"
            data = {
                'name': name,
                'object_story_spec': object_story_spec,
                'access_token': self.access_token
            }
            
            logger.info(f"🎨 Creating ad creative '{name}'")
            response = requests.post(url, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            creative_id = result.get('id')
            
            logger.info(f"✅ Ad creative created: {creative_id}")
            return {
                'success': True,
                'creative_id': creative_id
            }
            
        except Exception as e:
            logger.error(f"❌ Error creating ad creative: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # ==================== COMPREHENSIVE TEST ====================
    
    def test_all_permissions(self, page_id=None, instagram_account_id=None, ad_account_id=None):
        """
        Test all Meta permissions with real API calls
        
        Args:
            page_id: Facebook Page ID (optional)
            instagram_account_id: Instagram Business Account ID (optional)
            ad_account_id: Ad Account ID (optional)
            
        Returns:
            dict: Test results for all permissions
        """
        results = {}
        
        logger.info("🧪 Starting comprehensive permissions test...")
        
        # Test pages_show_list
        logger.info("\n1️⃣ Testing pages_show_list...")
        results['pages_show_list'] = self.get_user_pages()
        
        # Get page_id from results if not provided
        if not page_id and results['pages_show_list']['success']:
            pages = results['pages_show_list'].get('pages', [])
            if pages:
                page_id = pages[0]['id']
                logger.info(f"   Using page_id: {page_id}")
        
        # Test pages_read_engagement
        if page_id:
            logger.info("\n2️⃣ Testing pages_read_engagement...")
            results['pages_read_engagement'] = self.get_page_engagement_insights(page_id)
            results['pages_posts_insights'] = self.get_page_posts_insights(page_id)
        
        # Test instagram_basic
        if instagram_account_id:
            logger.info("\n3️⃣ Testing instagram_basic...")
            results['instagram_basic'] = self.get_instagram_account_info(instagram_account_id)
            results['instagram_media'] = self.get_instagram_media(instagram_account_id)
        elif page_id:
            # Try to get Instagram account from page
            logger.info("\n3️⃣ Getting Instagram account from page...")
            ig_result = self.get_instagram_accounts_for_page(page_id)
            if ig_result['success'] and ig_result.get('instagram_account'):
                instagram_account_id = ig_result['instagram_account']['id']
                results['instagram_basic'] = self.get_instagram_account_info(instagram_account_id)
                results['instagram_media'] = self.get_instagram_media(instagram_account_id)
        
        # Test instagram_manage_messages
        if instagram_account_id:
            logger.info("\n4️⃣ Testing instagram_manage_messages...")
            results['instagram_conversations'] = self.get_instagram_conversations(instagram_account_id)
        
        # Test business_management
        logger.info("\n5️⃣ Testing business_management...")
        results['business_accounts'] = self.get_business_accounts()
        
        # Test ads_read
        logger.info("\n6️⃣ Testing ads_read...")
        results['ad_accounts'] = self.get_ad_accounts()
        
        # Get ad_account_id from results if not provided
        if not ad_account_id and results['ad_accounts']['success']:
            ad_accounts = results['ad_accounts'].get('ad_accounts', [])
            if ad_accounts:
                # Extract account_id (remove 'act_' prefix if present)
                ad_account_id = ad_accounts[0]['account_id']
                logger.info(f"   Using ad_account_id: {ad_account_id}")
        
        # Test campaigns
        if ad_account_id:
            results['campaigns'] = self.get_campaigns(ad_account_id)
        
        logger.info("\n✅ Permissions test completed!")
        
        return {
            'success': True,
            'results': results,
            'tested_permissions': [
                'pages_show_list',
                'pages_read_engagement',
                'instagram_basic',
                'instagram_manage_messages',
                'business_management',
                'ads_read'
            ]
        }


def get_meta_service(access_token):
    """Get MetaPermissionsService instance"""
    return MetaPermissionsService(access_token)

