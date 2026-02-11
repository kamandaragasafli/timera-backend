"""
Meta Webhook Views
Meta-dan gələn webhook-ları qəbul edir (mesajlar, notifications və s.)
"""

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.conf import settings
import json
import logging
import hmac
import hashlib

logger = logging.getLogger(__name__)


@csrf_exempt
@api_view(['GET', 'POST'])
def meta_webhook(request):
    """
    Meta Webhook endpoint
    GET: Webhook verification (Meta tərəfindən çağırılır)
    POST: Webhook events (mesajlar, notifications və s.)
    
    GET /api/posts/meta/webhook/
    POST /api/posts/meta/webhook/
    """
    
    if request.method == 'GET':
        # Webhook verification
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        
        # Verify token (Meta App Dashboard-da təyin olunmalıdır)
        verify_token = getattr(settings, 'META_WEBHOOK_VERIFY_TOKEN', 'timera_webhook_token')
        
        if mode == 'subscribe' and token == verify_token:
            logger.info("✅ Meta webhook verified successfully")
            return HttpResponse(challenge, content_type='text/plain')
        else:
            logger.warning(f"❌ Meta webhook verification failed: mode={mode}, token_match={token == verify_token}")
            return HttpResponse('Verification failed', status=403)
    
    elif request.method == 'POST':
        # Webhook event received
        try:
            # Verify webhook signature (optional but recommended)
            signature = request.headers.get('X-Hub-Signature-256', '')
            if signature:
                app_secret = getattr(settings, 'META_APP_SECRET', '')
                if app_secret:
                    expected_signature = 'sha256=' + hmac.new(
                        app_secret.encode(),
                        request.body,
                        hashlib.sha256
                    ).hexdigest()
                    if not hmac.compare_digest(signature, expected_signature):
                        logger.warning("❌ Invalid webhook signature")
                        return Response({'error': 'Invalid signature'}, status=403)
            
            # Parse webhook data
            data = json.loads(request.body)
            
            # Handle different webhook events
            if 'object' in data and data['object'] == 'page':
                # Facebook Page webhook
                for entry in data.get('entry', []):
                    page_id = entry.get('id')
                    messaging = entry.get('messaging', [])
                    
                    for event in messaging:
                        handle_messaging_event(event, page_id)
            
            elif 'object' in data and data['object'] == 'instagram':
                # Instagram webhook
                for entry in data.get('entry', []):
                    instagram_id = entry.get('id')
                    messaging = entry.get('messaging', [])
                    
                    for event in messaging:
                        handle_messaging_event(event, instagram_id, platform='instagram')
            
            logger.info("✅ Webhook event processed successfully")
            return Response({'success': True}, status=200)
            
        except Exception as e:
            logger.error(f"❌ Error processing webhook: {str(e)}", exc_info=True)
            return Response({'error': str(e)}, status=500)
    
    return Response({'error': 'Method not allowed'}, status=405)


def handle_messaging_event(event, account_id, platform='facebook'):
    """
    Handle messaging event from Meta webhook
    
    Args:
        event: Webhook event data
        account_id: Page ID or Instagram Account ID
        platform: 'facebook' or 'instagram'
    """
    try:
        sender_id = event.get('sender', {}).get('id')
        recipient_id = event.get('recipient', {}).get('id')
        message = event.get('message')
        timestamp = event.get('timestamp')
        
        if message:
            message_text = message.get('text', '')
            message_id = message.get('mid')
            
            logger.info(f"📩 New {platform} message received: {message_id} from {sender_id}")
            
            # Burada mesajı database-ə yaza bilərsiniz və ya real-time notification göndərə bilərsiniz
            # Məsələn:
            # - Database-ə yazmaq
            # - WebSocket ilə frontend-ə bildirmək
            # - Email/SMS notification göndərmək
            
            # TODO: Implement message storage and real-time notifications
            
    except Exception as e:
        logger.error(f"❌ Error handling messaging event: {str(e)}", exc_info=True)

