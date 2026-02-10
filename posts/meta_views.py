"""
Meta Permissions API Views
Bu views Meta icazələrinin hamısını istifadə edir
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
import logging

from .meta_permissions_service import get_meta_service
from social_accounts.models import SocialAccount

logger = logging.getLogger(__name__)


def get_user_meta_token(user, platform='facebook'):
    """
    Get Meta access token for user
    
    Args:
        user: Django User object
        platform: 'facebook' or 'instagram'
        
    Returns:
        str: Access token or None
    """
    try:
        social_account = SocialAccount.objects.filter(
            user=user,
            platform=platform,
            is_active=True
        ).first()
        
        if social_account:
            return social_account.get_access_token()
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting Meta token: {str(e)}")
        return None


# ==================== FACEBOOK PAGES ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_facebook_pages(request):
    """
    Get list of Facebook Pages user manages
    İcazə: pages_show_list
    
    GET /api/posts/meta/pages/
    """
    try:
        access_token = get_user_meta_token(request.user, 'facebook')
        if not access_token:
            return Response({
                'success': False,
                'error': 'Facebook hesabı bağlanmayıb'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        meta_service = get_meta_service(access_token)
        result = meta_service.get_user_pages()
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in list_facebook_pages: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_page_engagement(request, page_id):
    """
    Get Facebook Page engagement insights
    İcazə: pages_read_engagement
    
    GET /api/posts/meta/pages/<page_id>/engagement/
    Query params:
        - period: 'day', 'week', 'days_28' (default: 'day')
        - since: Start date YYYY-MM-DD (optional)
        - until: End date YYYY-MM-DD (optional)
    """
    try:
        access_token = get_user_meta_token(request.user, 'facebook')
        if not access_token:
            return Response({
                'success': False,
                'error': 'Facebook hesabı bağlanmayıb'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        period = request.query_params.get('period', 'day')
        since = request.query_params.get('since')
        until = request.query_params.get('until')
        
        meta_service = get_meta_service(access_token)
        result = meta_service.get_page_engagement_insights(
            page_id, 
            page_access_token=access_token,
            period=period,
            since=since,
            until=until
        )
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in get_page_engagement: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_page_posts_insights(request, page_id):
    """
    Get insights for posts on Facebook Page
    İcazə: pages_read_engagement
    
    GET /api/posts/meta/pages/<page_id>/posts-insights/
    Query params:
        - limit: Number of posts (default: 25)
    """
    try:
        access_token = get_user_meta_token(request.user, 'facebook')
        if not access_token:
            return Response({
                'success': False,
                'error': 'Facebook hesabı bağlanmayıb'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        limit = int(request.query_params.get('limit', 25))
        
        meta_service = get_meta_service(access_token)
        result = meta_service.get_page_posts_insights(
            page_id,
            page_access_token=access_token,
            limit=limit
        )
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in get_page_posts_insights: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def publish_to_facebook_page(request):
    """
    Publish post to Facebook Page
    İcazə: pages_manage_posts
    
    POST /api/posts/meta/pages/publish/
    Body:
        {
            "page_id": "123456789",
            "message": "Post text",
            "image_url": "https://..." (optional)
        }
    """
    try:
        access_token = get_user_meta_token(request.user, 'facebook')
        if not access_token:
            return Response({
                'success': False,
                'error': 'Facebook hesabı bağlanmayıb'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        page_id = request.data.get('page_id')
        message = request.data.get('message')
        image_url = request.data.get('image_url')
        
        if not page_id or not message:
            return Response({
                'success': False,
                'error': 'page_id və message tələb olunur'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        meta_service = get_meta_service(access_token)
        result = meta_service.publish_page_post(
            page_id,
            message,
            image_url=image_url,
            page_access_token=access_token
        )
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in publish_to_facebook_page: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== INSTAGRAM ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_instagram_account(request):
    """
    Get Instagram Business Account info
    İcazə: instagram_basic
    
    GET /api/posts/meta/instagram/account/
    Query params:
        - account_id: Instagram Business Account ID (optional, will try to find from page)
    """
    try:
        access_token = get_user_meta_token(request.user, 'facebook')
        if not access_token:
            return Response({
                'success': False,
                'error': 'Facebook hesabı bağlanmayıb'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        account_id = request.query_params.get('account_id')
        
        meta_service = get_meta_service(access_token)
        
        # If no account_id provided, try to find from pages
        if not account_id:
            pages_result = meta_service.get_user_pages()
            if pages_result['success'] and pages_result['pages']:
                page_id = pages_result['pages'][0]['id']
                ig_result = meta_service.get_instagram_accounts_for_page(page_id, access_token)
                if ig_result['success'] and ig_result.get('instagram_account'):
                    account_id = ig_result['instagram_account']['id']
        
        if not account_id:
            return Response({
                'success': False,
                'error': 'Instagram Business Account tapılmadı'
            }, status=status.HTTP_404_NOT_FOUND)
        
        result = meta_service.get_instagram_account_info(account_id)
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in get_instagram_account: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_instagram_media(request):
    """
    Get Instagram media (posts)
    İcazə: instagram_basic
    
    GET /api/posts/meta/instagram/media/
    Query params:
        - account_id: Instagram Business Account ID
        - limit: Number of items (default: 25)
    """
    try:
        access_token = get_user_meta_token(request.user, 'facebook')
        if not access_token:
            return Response({
                'success': False,
                'error': 'Facebook hesabı bağlanmayıb'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        account_id = request.query_params.get('account_id')
        limit = int(request.query_params.get('limit', 25))
        
        if not account_id:
            return Response({
                'success': False,
                'error': 'account_id tələb olunur'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        meta_service = get_meta_service(access_token)
        result = meta_service.get_instagram_media(account_id, limit=limit)
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in get_instagram_media: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def publish_to_instagram(request):
    """
    Publish post to Instagram Business Account
    İcazə: instagram_content_publish
    
    POST /api/posts/meta/instagram/publish/
    Body:
        {
            "account_id": "17841...",
            "image_url": "https://...",
            "caption": "Post caption #hashtags"
        }
    """
    try:
        access_token = get_user_meta_token(request.user, 'facebook')
        if not access_token:
            return Response({
                'success': False,
                'error': 'Facebook hesabı bağlanmayıb'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        account_id = request.data.get('account_id')
        image_url = request.data.get('image_url')
        caption = request.data.get('caption')
        
        if not account_id or not image_url or not caption:
            return Response({
                'success': False,
                'error': 'account_id, image_url və caption tələb olunur'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        meta_service = get_meta_service(access_token)
        result = meta_service.publish_instagram_post(account_id, image_url, caption)
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in publish_to_instagram: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== INSTAGRAM MESSAGES ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_instagram_conversations(request):
    """
    Get Instagram Direct conversations
    İcazə: instagram_manage_messages, instagram_business_manage_messages
    
    GET /api/posts/meta/instagram/conversations/
    Query params:
        - account_id: Instagram Business Account ID
        - limit: Number of conversations (default: 25)
    """
    try:
        access_token = get_user_meta_token(request.user, 'facebook')
        if not access_token:
            return Response({
                'success': False,
                'error': 'Facebook hesabı bağlanmayıb'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        account_id = request.query_params.get('account_id')
        limit = int(request.query_params.get('limit', 25))
        
        if not account_id:
            return Response({
                'success': False,
                'error': 'account_id tələb olunur'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        meta_service = get_meta_service(access_token)
        result = meta_service.get_instagram_conversations(account_id, limit=limit)
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in get_instagram_conversations: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_instagram_messages(request, conversation_id):
    """
    Get messages from Instagram conversation
    İcazə: instagram_manage_messages, instagram_business_manage_messages
    
    GET /api/posts/meta/instagram/conversations/<conversation_id>/messages/
    Query params:
        - limit: Number of messages (default: 50)
    """
    try:
        access_token = get_user_meta_token(request.user, 'facebook')
        if not access_token:
            return Response({
                'success': False,
                'error': 'Facebook hesabı bağlanmayıb'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        limit = int(request.query_params.get('limit', 50))
        
        meta_service = get_meta_service(access_token)
        result = meta_service.get_instagram_messages(conversation_id, limit=limit)
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in get_instagram_messages: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_instagram_message(request):
    """
    Send message to Instagram user
    İcazə: instagram_manage_messages, instagram_business_manage_messages
    
    POST /api/posts/meta/instagram/messages/send/
    Body:
        {
            "account_id": "17841...",
            "recipient_id": "123456",
            "message": "Hello!"
        }
    """
    try:
        access_token = get_user_meta_token(request.user, 'facebook')
        if not access_token:
            return Response({
                'success': False,
                'error': 'Facebook hesabı bağlanmayıb'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        account_id = request.data.get('account_id')
        recipient_id = request.data.get('recipient_id')
        message_text = request.data.get('message')
        
        if not account_id or not recipient_id or not message_text:
            return Response({
                'success': False,
                'error': 'account_id, recipient_id və message tələb olunur'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        meta_service = get_meta_service(access_token)
        result = meta_service.send_instagram_message(account_id, recipient_id, message_text)
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in send_instagram_message: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== BUSINESS MANAGEMENT ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_business_accounts(request):
    """
    Get Business Accounts (Business Manager)
    İcazə: business_management
    
    GET /api/posts/meta/business/accounts/
    """
    try:
        access_token = get_user_meta_token(request.user, 'facebook')
        if not access_token:
            return Response({
                'success': False,
                'error': 'Facebook hesabı bağlanmayıb'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        meta_service = get_meta_service(access_token)
        result = meta_service.get_business_accounts()
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in get_business_accounts: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== ADS ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ad_accounts(request):
    """
    Get Ad Accounts
    İcazə: ads_read
    
    GET /api/posts/meta/ads/accounts/
    """
    try:
        access_token = get_user_meta_token(request.user, 'facebook')
        if not access_token:
            return Response({
                'success': False,
                'error': 'Facebook hesabı bağlanmayıb'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        meta_service = get_meta_service(access_token)
        result = meta_service.get_ad_accounts()
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in get_ad_accounts: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_campaigns(request, ad_account_id):
    """
    Get Ad Campaigns
    İcazə: ads_read
    
    GET /api/posts/meta/ads/accounts/<ad_account_id>/campaigns/
    Query params:
        - limit: Number of campaigns (default: 25)
    """
    try:
        access_token = get_user_meta_token(request.user, 'facebook')
        if not access_token:
            return Response({
                'success': False,
                'error': 'Facebook hesabı bağlanmayıb'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        limit = int(request.query_params.get('limit', 25))
        
        meta_service = get_meta_service(access_token)
        result = meta_service.get_campaigns(ad_account_id, limit=limit)
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in get_campaigns: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_campaign_insights(request, campaign_id):
    """
    Get campaign insights
    İcazə: ads_read
    
    GET /api/posts/meta/ads/campaigns/<campaign_id>/insights/
    Query params:
        - date_preset: 'last_7d', 'last_30d', etc. (default: 'last_7d')
    """
    try:
        access_token = get_user_meta_token(request.user, 'facebook')
        if not access_token:
            return Response({
                'success': False,
                'error': 'Facebook hesabı bağlanmayıb'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        date_preset = request.query_params.get('date_preset', 'last_7d')
        
        meta_service = get_meta_service(access_token)
        result = meta_service.get_campaign_insights(campaign_id, date_preset=date_preset)
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in get_campaign_insights: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_campaign(request):
    """
    Create new ad campaign
    İcazə: ads_management
    
    POST /api/posts/meta/ads/campaigns/create/
    Body:
        {
            "ad_account_id": "123456789",
            "name": "Campaign Name",
            "objective": "REACH",
            "status": "PAUSED",
            "daily_budget": 1000 (optional, in cents)
        }
    """
    try:
        access_token = get_user_meta_token(request.user, 'facebook')
        if not access_token:
            return Response({
                'success': False,
                'error': 'Facebook hesabı bağlanmayıb'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        ad_account_id = request.data.get('ad_account_id')
        name = request.data.get('name')
        objective = request.data.get('objective')
        campaign_status = request.data.get('status', 'PAUSED')
        daily_budget = request.data.get('daily_budget')
        
        if not ad_account_id or not name or not objective:
            return Response({
                'success': False,
                'error': 'ad_account_id, name və objective tələb olunur'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        meta_service = get_meta_service(access_token)
        result = meta_service.create_campaign(
            ad_account_id,
            name,
            objective,
            status=campaign_status,
            daily_budget=daily_budget
        )
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in create_campaign: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_campaign(request, campaign_id):
    """
    Update existing campaign
    İcazə: ads_management
    
    PUT /api/posts/meta/ads/campaigns/<campaign_id>/update/
    Body:
        {
            "status": "ACTIVE" (optional),
            "name": "New Name" (optional),
            "daily_budget": 2000 (optional)
        }
    """
    try:
        access_token = get_user_meta_token(request.user, 'facebook')
        if not access_token:
            return Response({
                'success': False,
                'error': 'Facebook hesabı bağlanmayıb'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        campaign_status = request.data.get('status')
        name = request.data.get('name')
        daily_budget = request.data.get('daily_budget')
        
        meta_service = get_meta_service(access_token)
        result = meta_service.update_campaign(
            campaign_id,
            status=campaign_status,
            name=name,
            daily_budget=daily_budget
        )
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in update_campaign: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== COMPREHENSIVE TEST ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_all_permissions(request):
    """
    Test all Meta permissions
    
    POST /api/posts/meta/test-permissions/
    Body:
        {
            "page_id": "..." (optional),
            "instagram_account_id": "..." (optional),
            "ad_account_id": "..." (optional)
        }
    """
    try:
        access_token = get_user_meta_token(request.user, 'facebook')
        if not access_token:
            return Response({
                'success': False,
                'error': 'Facebook hesabı bağlanmayıb'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        page_id = request.data.get('page_id')
        instagram_account_id = request.data.get('instagram_account_id')
        ad_account_id = request.data.get('ad_account_id')
        
        meta_service = get_meta_service(access_token)
        result = meta_service.test_all_permissions(
            page_id=page_id,
            instagram_account_id=instagram_account_id,
            ad_account_id=ad_account_id
        )
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in test_all_permissions: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

