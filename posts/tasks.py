"""
Celery tasks for automatic post publishing
"""
import logging
from celery import shared_task
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import requests

from .models import Post, PostPlatform
from social_accounts.models import SocialAccount

logger = logging.getLogger(__name__)


@shared_task
def publish_scheduled_posts():
    """
    Check for scheduled posts that are due and publish them automatically.
    Runs every minute via Celery Beat.
    """
    logger.info("🕐 Checking for scheduled posts to publish...")
    
    # Get current time
    now = timezone.now()
    
    # Find posts that are scheduled and due (within the last 2 minutes to account for delays)
    # We check posts from 2 minutes ago to now to ensure we don't miss any
    time_window_start = now - timedelta(minutes=2)
    
    scheduled_posts = Post.objects.filter(
        status='scheduled',
        scheduled_time__lte=now,
        scheduled_time__gte=time_window_start
    ).select_related('user').prefetch_related('postplatform_set__social_account')
    
    logger.info(f"📋 Found {scheduled_posts.count()} scheduled posts due for publishing")
    
    published_count = 0
    failed_count = 0
    
    for post in scheduled_posts:
        try:
            logger.info(f"📤 Publishing post {post.id} (scheduled for {post.scheduled_time})")
            
            # Get all PostPlatform entries for this post
            post_platforms = PostPlatform.objects.filter(
                post=post,
                status='pending'
            ).select_related('social_account')
            
            if not post_platforms.exists():
                logger.warning(f"⚠️  Post {post.id} has no platforms to publish to")
                post.status = 'failed'
                post.save()
                failed_count += 1
                continue
            
            # Publish to each platform
            success_count = 0
            for post_platform in post_platforms:
                try:
                    platform_name = post_platform.social_account.platform
                    logger.info(f"  → Publishing to {platform_name}...")
                    
                    # Publish based on platform
                    if platform_name == 'facebook':
                        result = _publish_to_facebook(post, post_platform)
                    elif platform_name == 'instagram':
                        result = _publish_to_instagram(post, post_platform)
                    elif platform_name == 'linkedin':
                        result = _publish_to_linkedin(post, post_platform)
                    else:
                        logger.warning(f"  ⚠️  Platform {platform_name} not supported for auto-publishing")
                        continue
                    
                    if result['success']:
                        success_count += 1
                        post_platform.status = 'published'
                        post_platform.platform_post_id = result.get('post_id', '')
                        post_platform.platform_post_url = result.get('post_url', '')
                        post_platform.published_at = timezone.now()
                        post_platform.save()
                        logger.info(f"  ✅ Successfully published to {platform_name}")
                    else:
                        post_platform.status = 'failed'
                        post_platform.error_message = result.get('error', 'Unknown error')
                        post_platform.save()
                        logger.error(f"  ❌ Failed to publish to {platform_name}: {result.get('error')}")
                        
                except Exception as e:
                    logger.error(f"  ❌ Error publishing to {platform_name}: {str(e)}", exc_info=True)
                    post_platform.status = 'failed'
                    post_platform.error_message = str(e)
                    post_platform.save()
            
            # Update post status based on results
            if success_count > 0:
                # At least one platform succeeded
                post.status = 'published'
                post.published_at = timezone.now()
                post.save()
                published_count += 1
                logger.info(f"✅ Post {post.id} published successfully to {success_count} platform(s)")
            else:
                # All platforms failed
                post.status = 'failed'
                post.save()
                failed_count += 1
                logger.error(f"❌ Post {post.id} failed to publish to all platforms")
                
        except Exception as e:
            logger.error(f"❌ Error processing post {post.id}: {str(e)}", exc_info=True)
            post.status = 'failed'
            post.save()
            failed_count += 1
    
    logger.info(f"✅ Published: {published_count}, ❌ Failed: {failed_count}")
    return {
        'published': published_count,
        'failed': failed_count,
        'total_checked': scheduled_posts.count()
    }


@shared_task
def cleanup_rejected_posts():
    """
    Clean up rejected/cancelled posts based on data retention policy.
    Runs daily via Celery Beat.
    
    Data retention policy:
    - Default: Delete cancelled posts after 30 days
    - Can be configured per user in settings (immediately or X days)
    """
    logger.info("🧹 Starting cleanup of rejected posts...")
    
    # Default retention: 30 days
    # In production, this should be configurable per user
    retention_days = getattr(settings, 'DELETED_POSTS_RETENTION_DAYS', 30)
    
    cutoff_date = timezone.now() - timedelta(days=retention_days)
    
    # Find cancelled posts older than retention period
    old_cancelled_posts = Post.objects.filter(
        status='cancelled',
        updated_at__lte=cutoff_date
    )
    
    count = old_cancelled_posts.count()
    
    if count > 0:
        logger.info(f"🗑️  Found {count} cancelled posts to delete (older than {retention_days} days)")
        
        # Delete posts (this will cascade to PostPlatform entries)
        deleted_count = old_cancelled_posts.delete()[0]
        
        logger.info(f"✅ Deleted {deleted_count} cancelled posts")
    else:
        logger.info("✅ No cancelled posts to clean up")
    
    return {
        'deleted': count,
        'retention_days': retention_days
    }


def _publish_to_facebook(post, post_platform):
    """Publish post to Facebook"""
    try:
        social_account = post_platform.social_account
        page_token = social_account.get_access_token()
        page_id = social_account.platform_user_id
        
        # Get image URL
        image_url = None
        if post.custom_image:
            if hasattr(post.custom_image, 'url'):
                image_url = post.custom_image.url
            else:
                image_url = str(post.custom_image)
        elif post.design_url:
            image_url = post.design_url
        
        # Make absolute URL
        if image_url and not image_url.startswith('http'):
            image_url = f"{settings.BACKEND_URL}{image_url}"
        
        # Publish to Facebook
        if image_url:
            post_data = {
                'message': post.content,
                'url': image_url,
                'access_token': page_token
            }
            fb_api_url = f"https://graph.facebook.com/v18.0/{page_id}/photos"
        else:
            post_data = {
                'message': post.content,
                'access_token': page_token
            }
            fb_api_url = f"https://graph.facebook.com/v18.0/{page_id}/feed"
        
        response = requests.post(fb_api_url, data=post_data, timeout=30)
        
        if response.status_code == 200:
            fb_post_data = response.json()
            return {
                'success': True,
                'post_id': fb_post_data.get('id', ''),
                'post_url': f"https://www.facebook.com/{fb_post_data.get('id', '')}"
            }
        else:
            error_data = response.json()
            error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            return {
                'success': False,
                'error': f"Facebook API Error: {error_msg}"
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def _publish_to_instagram(post, post_platform):
    """Publish post to Instagram"""
    try:
        social_account = post_platform.social_account
        access_token = social_account.get_access_token()
        ig_account_id = social_account.platform_user_id
        
        # Get image URL
        image_url = None
        if post.custom_image:
            if hasattr(post.custom_image, 'url'):
                image_url = post.custom_image.url
            else:
                image_url = str(post.custom_image)
        elif post.design_url:
            image_url = post.design_url
        
        if not image_url:
            return {
                'success': False,
                'error': 'Instagram paylaşımı üçün şəkil tələb olunur'
            }
        
        # Make absolute URL
        if not image_url.startswith('http'):
            image_url = f"{settings.BACKEND_URL}{image_url}"
        
        # Ensure HTTPS
        if image_url.startswith('http://') and not image_url.startswith('https://'):
            image_url = image_url.replace('http://', 'https://', 1)
        
        # Step 1: Create media container
        create_url = f"https://graph.facebook.com/v18.0/{ig_account_id}/media"
        create_data = {
            'image_url': image_url,
            'caption': post.content,
            'access_token': access_token
        }
        
        create_response = requests.post(create_url, data=create_data, timeout=30)
        
        if create_response.status_code != 200:
            error_data = create_response.json()
            error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            return {
                'success': False,
                'error': f"Instagram Create Media Error: {error_msg}"
            }
        
        creation_id = create_response.json().get('id')
        
        # Step 2: Publish the media container
        publish_url = f"https://graph.facebook.com/v18.0/{ig_account_id}/media_publish"
        publish_data = {
            'creation_id': creation_id,
            'access_token': access_token
        }
        
        publish_response = requests.post(publish_url, data=publish_data, timeout=30)
        
        if publish_response.status_code == 200:
            ig_post_data = publish_response.json()
            return {
                'success': True,
                'post_id': ig_post_data.get('id', ''),
                'post_url': f"https://www.instagram.com/p/{ig_post_data.get('id', '')}/"
            }
        else:
            error_data = publish_response.json()
            error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            return {
                'success': False,
                'error': f"Instagram Publish Error: {error_msg}"
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def _publish_to_linkedin(post, post_platform):
    """Publish post to LinkedIn"""
    try:
        social_account = post_platform.social_account
        access_token = social_account.get_access_token()
        linkedin_user_id = social_account.platform_user_id
        
        # Prepare post content
        post_text = post.content
        if post.hashtags:
            post_text += '\n\n' + ' '.join(post.hashtags)
        
        # Get image URL
        image_url = None
        if post.custom_image:
            if hasattr(post.custom_image, 'url'):
                image_url = post.custom_image.url
            else:
                image_url = str(post.custom_image)
        elif post.design_url:
            image_url = post.design_url
        
        # Make absolute URL
        if image_url and not image_url.startswith('http'):
            image_url = f"{settings.BACKEND_URL}{image_url}"
        
        author_urn = f"urn:li:person:{linkedin_user_id}"
        
        if image_url:
            # Upload image to LinkedIn first
            # Step 1: Register the upload
            register_payload = {
                "registerUploadRequest": {
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                    "owner": author_urn,
                    "serviceRelationships": [
                        {
                            "relationshipType": "OWNER",
                            "identifier": "urn:li:userGeneratedContent"
                        }
                    ]
                }
            }
            
            register_response = requests.post(
                "https://api.linkedin.com/v2/assets?action=registerUpload",
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                json=register_payload,
                timeout=30
            )
            
            if register_response.status_code != 200:
                error_data = register_response.json()
                error_msg = error_data.get('message', 'Unknown error')
                return {
                    'success': False,
                    'error': f"LinkedIn Register Upload Error: {error_msg}"
                }
            
            register_data = register_response.json()
            upload_url = register_data['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
            asset_urn = register_data['value']['asset']
            
            # Step 2: Upload the image
            image_response = requests.get(image_url, timeout=30)
            if image_response.status_code != 200:
                return {
                    'success': False,
                    'error': f"Failed to fetch image from {image_url}"
                }
            
            upload_response = requests.put(
                upload_url,
                headers={
                    'Authorization': f'Bearer {access_token}',
                },
                data=image_response.content,
                timeout=30
            )
            
            if upload_response.status_code not in [200, 201]:
                return {
                    'success': False,
                    'error': f"LinkedIn Image Upload Error: {upload_response.status_code}"
                }
            
            # Step 3: Create UGC post with image
            ugc_post_payload = {
                "author": author_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": post_text
                        },
                        "shareMediaCategory": "IMAGE",
                        "media": [
                            {
                                "status": "READY",
                                "media": asset_urn,
                                "title": {
                                    "text": post.title or "Post"
                                }
                            }
                        ]
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
        else:
            # Text-only post
            ugc_post_payload = {
                "author": author_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": post_text
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
        
        # Step 4: Publish the post
        post_response = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'X-Restli-Protocol-Version': '2.0.0'
            },
            json=ugc_post_payload,
            timeout=30
        )
        
        if post_response.status_code in [200, 201]:
            post_data = post_response.json()
            post_id = post_data.get('id', '')
            return {
                'success': True,
                'post_id': post_id,
                'post_url': f"https://www.linkedin.com/feed/update/{post_id}"
            }
        else:
            error_data = post_response.json()
            error_msg = error_data.get('message', 'Unknown error')
            return {
                'success': False,
                'error': f"LinkedIn Post Error: {error_msg}"
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

