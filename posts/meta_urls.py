"""
URL Configuration for Meta Permissions API
Hər bir Meta icazəsi üçün endpoint-lər
"""

from django.urls import path
from . import meta_views
from . import webhook_views

app_name = 'meta'

urlpatterns = [
    # ==================== FACEBOOK PAGES ====================
    # İcazə: pages_show_list
    path('pages/', meta_views.list_facebook_pages, name='list_pages'),
    
    # İcazə: pages_read_engagement
    path('pages/<str:page_id>/engagement/', meta_views.get_page_engagement, name='page_engagement'),
    path('pages/<str:page_id>/posts-insights/', meta_views.get_page_posts_insights, name='page_posts_insights'),
    
    # İcazə: pages_manage_posts
    path('pages/publish/', meta_views.publish_to_facebook_page, name='publish_facebook'),
    
    # ==================== INSTAGRAM ====================
    # İcazə: instagram_basic
    path('instagram/account/', meta_views.get_instagram_account, name='instagram_account'),
    path('instagram/media/', meta_views.get_instagram_media, name='instagram_media'),
    
    # İcazə: instagram_content_publish
    path('instagram/publish/', meta_views.publish_to_instagram, name='publish_instagram'),
    
    # İcazə: instagram_manage_messages, instagram_business_manage_messages
    path('instagram/conversations/', meta_views.get_instagram_conversations, name='instagram_conversations'),
    path('instagram/conversations/<str:conversation_id>/messages/', meta_views.get_instagram_messages, name='instagram_messages'),
    path('instagram/messages/send/', meta_views.send_instagram_message, name='send_instagram_message'),
    
    # İcazə: pages_messaging
    path('facebook/conversations/', meta_views.get_facebook_conversations, name='facebook_conversations'),
    path('facebook/conversations/<str:conversation_id>/messages/', meta_views.get_facebook_messages, name='facebook_messages'),
    path('facebook/messages/send/', meta_views.send_facebook_message, name='send_facebook_message'),
    
    # ==================== WEBHOOK ====================
    path('webhook/', webhook_views.meta_webhook, name='meta_webhook'),
    
    # ==================== BUSINESS MANAGEMENT ====================
    # İcazə: business_management
    path('business/accounts/', meta_views.get_business_accounts, name='business_accounts'),
    
    # ==================== ADS ====================
    # İcazə: ads_read
    path('ads/accounts/', meta_views.get_ad_accounts, name='ad_accounts'),
    path('ads/accounts/<str:ad_account_id>/campaigns/', meta_views.get_campaigns, name='campaigns'),
    path('ads/campaigns/<str:campaign_id>/insights/', meta_views.get_campaign_insights, name='campaign_insights'),
    
    # İcazə: ads_management
    path('ads/campaigns/create/', meta_views.create_campaign, name='create_campaign'),
    path('ads/campaigns/<str:campaign_id>/update/', meta_views.update_campaign, name='update_campaign'),
    
    # ==================== TEST ====================
    path('test-permissions/', meta_views.test_all_permissions, name='test_permissions'),
]

