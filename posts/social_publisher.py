"""
Social Media Publisher Service
Handles publishing posts to Facebook and Instagram using Supabase Storage
"""

import requests
import logging
from django.conf import settings
from .supabase_upload import get_upload_service

logger = logging.getLogger(__name__)


class SocialMediaPublisher:
    """Service for publishing posts to social media platforms"""
    
    def __init__(self):
        self.upload_service = get_upload_service()
    
    def publish_to_facebook(self, post, page_token, page_id):
        """
        Publish post to Facebook Page
        
        Args:
            post: Post model instance
            page_token: Facebook Page access token
            page_id: Facebook Page ID
            
        Returns:
            dict: {
                'success': bool,
                'post_id': str (Facebook post ID if successful),
                'error': str (error message if failed),
                'post_url': str (post URL if available)
            }
        """
        try:
            # Prepare message
            message = post.content
            if post.hashtags:
                message += '\n\n' + ' '.join(post.hashtags)
            
            # Check if post has an image
            if post.custom_image or post.image_url:
                # Get image URL (should be Supabase URL)
                image_url = post.image_url
                
                # If no Supabase URL, upload to Supabase first
                if not image_url:
                    # Try to get from custom_image field
                    if post.custom_image and hasattr(post.custom_image, 'path'):
                        # Local file - upload to Supabase
                        upload_result = self.upload_service.upload_image(post.custom_image.path)
                        if not upload_result['success']:
                            # Fallback: use local file directly if Supabase upload fails
                            logger.warning(f"⚠️ Supabase upload failed, using local file: {upload_result['error']}")
                            try:
                                with open(post.custom_image.path, 'rb') as f:
                                    image_bytes = f.read()
                                logger.info(f"✅ Using local file as fallback: {post.custom_image.path}")
                            except Exception as e:
                                return {
                                    'success': False,
                                    'error': f"Supabase yükləmə xətası və lokal fayl oxuna bilmədi: {upload_result['error']} | {str(e)}",
                                    'post_id': None,
                                    'post_url': None
                                }
                        else:
                            image_url = upload_result['url']
                            # Save URL to post
                            post.image_url = image_url
                            post.save()
                    else:
                        return {
                            'success': False,
                            'error': 'Şəkil URL-i tapılmadı',
                            'post_id': None,
                            'post_url': None
                        }
                
                # If we have image_url, download from Supabase; otherwise use local bytes
                if image_url:
                    # Download image from Supabase as bytes
                    logger.info(f"📥 Downloading image from Supabase: {image_url}")
                    image_bytes = self.upload_service.get_image_bytes(image_url)
                    
                    if not image_bytes:
                        # Fallback: try local file if Supabase download fails
                        if post.custom_image and hasattr(post.custom_image, 'path'):
                            logger.warning(f"⚠️ Supabase download failed, using local file as fallback")
                            try:
                                with open(post.custom_image.path, 'rb') as f:
                                    image_bytes = f.read()
                                logger.info(f"✅ Using local file as fallback: {post.custom_image.path}")
                            except Exception as e:
                                return {
                                    'success': False,
                                    'error': f'Supabase-dən şəkil yüklənə bilmədi və lokal fayl oxuna bilmədi: {str(e)}',
                                    'post_id': None,
                                    'post_url': None
                                }
                        else:
                            return {
                                'success': False,
                                'error': 'Supabase-dən şəkil yüklənə bilmədi',
                                'post_id': None,
                                'post_url': None
                            }
                
                # Upload to Facebook using multipart/form-data
                fb_api_url = f"https://graph.facebook.com/v18.0/{page_id}/photos"
                
                # Prepare multipart/form-data
                files = {
                    'source': ('image.png', image_bytes, 'image/png')
                }
                
                data = {
                    'message': message,
                    'access_token': page_token
                }
                
                logger.info(f"📸 Facebook: Uploading image to page {page_id}")
                
                response = requests.post(
                    fb_api_url,
                    files=files,
                    data=data,
                    timeout=30
                )
                
            else:
                # Text-only post
                fb_api_url = f"https://graph.facebook.com/v18.0/{page_id}/feed"
                
                post_data = {
                    'message': message,
                    'access_token': page_token
                }
                
                logger.info(f"📝 Facebook: Publishing text-only post to page {page_id}")
                
                response = requests.post(
                    fb_api_url,
                    data=post_data,
                    timeout=30
                )
            
            # Handle response
            if response.status_code != 200:
                try:
                    error_data = response.json()
                    error_obj = error_data.get('error', {})
                    
                    if isinstance(error_obj, dict):
                        error_message = error_obj.get('message', 'Unknown error')
                        error_code = error_obj.get('code')
                        error_type = error_obj.get('type', '')
                        
                        logger.error(f"❌ Facebook API Error: {error_message} (Code: {error_code}, Type: {error_type})")
                        logger.error(f"   Full response: {error_data}")
                        
                        return {
                            'success': False,
                            'error': f"Facebook API Error: {error_message}",
                            'error_code': error_code,
                            'error_type': error_type,
                            'post_id': None,
                            'post_url': None
                        }
                    else:
                        error_message = str(error_obj)
                        logger.error(f"❌ Facebook API Error: {error_message}")
                        return {
                            'success': False,
                            'error': f"Facebook API Error: {error_message}",
                            'post_id': None,
                            'post_url': None
                        }
                except ValueError:
                    logger.error(f"❌ Facebook API Error: Non-JSON response: {response.text}")
                    return {
                        'success': False,
                        'error': f"Facebook API Error: {response.text}",
                        'post_id': None,
                        'post_url': None
                    }
            
            # Success
            fb_post_data = response.json()
            fb_post_id = fb_post_data.get('id')
            
            if not fb_post_id:
                logger.warning(f"⚠️ Facebook: Response received but no 'id' field: {fb_post_data}")
                return {
                    'success': False,
                    'error': 'Facebook paylaşımı uğurlu oldu, amma post ID alına bilmədi',
                    'post_id': None,
                    'post_url': None
                }
            
            # Construct post URL
            post_url = f"https://www.facebook.com/{fb_post_id}" if fb_post_id else None
            
            logger.info(f"✅ Facebook: Post successfully published with ID: {fb_post_id}")
            
            return {
                'success': True,
                'post_id': fb_post_id,
                'error': None,
                'post_url': post_url
            }
            
        except Exception as e:
            error_msg = f"Facebook paylaşım xətası: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return {
                'success': False,
                'error': error_msg,
                'post_id': None,
                'post_url': None
            }
    
    def publish_to_instagram(self, post, access_token, ig_account_id):
        """
        Publish post to Instagram Business Account
        
        Args:
            post: Post model instance
            access_token: Instagram access token
            ig_account_id: Instagram Business Account ID
            
        Returns:
            dict: {
                'success': bool,
                'post_id': str (Instagram post ID if successful),
                'error': str (error message if failed),
                'post_url': str (post URL if available)
            }
        """
        try:
            # Get image URL (should be Supabase URL)
            image_url = post.image_url
            
            # If no Supabase URL, upload to Supabase first
            if not image_url:
                if post.custom_image and hasattr(post.custom_image, 'path'):
                    # Local file - MUST upload to Supabase for Instagram
                    logger.info(f"📤 No Supabase URL found, uploading to Supabase...")
                    upload_result = self.upload_service.upload_image(
                        post.custom_image.path,
                        filename=f"instagram_{post.id}.png",
                        content_type='image/png'
                    )
                    if not upload_result['success']:
                        # Instagram requires public HTTPS URL - cannot use localhost
                        error_msg = f"Supabase yükləmə xətası: {upload_result['error']}. Instagram üçün public HTTPS URL lazımdır (localhost işləmir)."
                        logger.error(f"❌ {error_msg}")
                        return {
                            'success': False,
                            'error': error_msg,
                            'post_id': None,
                            'post_url': None
                        }
                    else:
                        image_url = upload_result['url']
                        # Ensure public endpoint
                        if '/storage/v1/object/' in image_url and '/object/public/' not in image_url:
                            image_url = image_url.replace('/storage/v1/object/', '/storage/v1/object/public/')
                        # Save URL to post
                        post.image_url = image_url
                        post.save()
                        logger.info(f"✅ Image uploaded to Supabase: {image_url[:100]}...")
                elif post.design_url:
                    # Use design_url if available (fallback for old posts)
                    # But check if it's a valid public URL
                    if 'localhost' in post.design_url or '127.0.0.1' in post.design_url:
                        return {
                            'success': False,
                            'error': 'Instagram üçün public HTTPS URL lazımdır. Design URL localhost içərir və işləmir.',
                            'post_id': None,
                            'post_url': None
                        }
                    image_url = post.design_url
                else:
                    return {
                        'success': False,
                        'error': 'Instagram paylaşımı üçün şəkil tələb olunur',
                        'post_id': None,
                        'post_url': None
                    }
            
            # CRITICAL: Check if URL is localhost (Instagram will reject it)
            if 'localhost' in image_url or '127.0.0.1' in image_url:
                logger.error(f"❌ Instagram cannot use localhost URL: {image_url}")
                # Try to upload to Supabase if we have local file
                if post.custom_image and hasattr(post.custom_image, 'path'):
                    logger.info(f"🔄 Attempting to upload local file to Supabase...")
                    upload_result = self.upload_service.upload_image(
                        post.custom_image.path,
                        filename=f"instagram_{post.id}.png",
                        content_type='image/png'
                    )
                    if upload_result['success']:
                        image_url = upload_result['url']
                        if '/storage/v1/object/' in image_url and '/object/public/' not in image_url:
                            image_url = image_url.replace('/storage/v1/object/', '/storage/v1/object/public/')
                        post.image_url = image_url
                        post.save()
                        logger.info(f"✅ Re-uploaded to Supabase: {image_url[:100]}...")
                    else:
                        return {
                            'success': False,
                            'error': f'Instagram localhost URL-lərini qəbul etmir. Supabase yükləmə də uğursuz oldu: {upload_result["error"]}',
                            'post_id': None,
                            'post_url': None
                        }
                else:
                    return {
                        'success': False,
                        'error': 'Instagram localhost URL-lərini qəbul etmir. Şəkil Supabase-ə yüklənməlidir.',
                        'post_id': None,
                        'post_url': None
                    }
            
            # Ensure URL is HTTPS
            if image_url.startswith('http://'):
                image_url = image_url.replace('http://', 'https://', 1)
            
            # Remove query parameters from URL (Instagram doesn't like them)
            if '?' in image_url:
                image_url = image_url.split('?')[0]
            
            # For Supabase Storage URLs, ensure we're using the public endpoint
            # Supabase Storage public URL format: /storage/v1/object/public/{bucket}/{path}
            # Sometimes the URL might have /object/ instead of /object/public/
            if '/storage/v1/object/' in image_url and '/object/public/' not in image_url:
                # Replace /object/ with /object/public/ for public access
                image_url = image_url.replace('/storage/v1/object/', '/storage/v1/object/public/')
                logger.info(f"🔧 Fixed Supabase URL to use public endpoint: {image_url[:100]}...")
            
            # Validate that URL is actually an image (Instagram requirement)
            # Instagram API requires the URL to return proper content-type headers
            logger.info(f"🔍 Validating image URL for Instagram: {image_url[:100]}...")
            content_type_valid = False
            try:
                # Use User-Agent header to mimic a browser (some servers require this)
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                # First try HEAD request
                head_response = requests.head(image_url, timeout=10, allow_redirects=True, headers=headers)
                content_type = head_response.headers.get('Content-Type', '').lower()
                
                # If HEAD doesn't work or doesn't return content-type, try GET with stream
                if not content_type or not content_type.startswith('image/'):
                    logger.warning(f"⚠️ HEAD request didn't return image content-type, trying GET: {content_type}")
                    img_response = requests.get(image_url, stream=True, timeout=10, allow_redirects=True, headers=headers)
                    content_type = img_response.headers.get('Content-Type', '').lower()
                    
                    # Instagram only accepts image/jpeg, image/png, image/webp
                    if not content_type.startswith('image/'):
                        logger.error(f"❌ URL is not an image. Content-Type: {content_type}")
                        logger.error(f"   Response headers: {dict(img_response.headers)}")
                        logger.error(f"   Response status: {img_response.status_code}")
                        
                        # If Supabase URL doesn't work, try to re-upload with correct content-type
                        if 'supabase' in image_url.lower() and post.custom_image and hasattr(post.custom_image, 'path'):
                            logger.info(f"🔄 Supabase URL Content-Type invalid, re-uploading with correct settings...")
                            # Re-upload to Supabase with explicit content-type
                            upload_result = self.upload_service.upload_image(
                                post.custom_image.path,
                                filename=f"instagram_{post.id}.png",
                                content_type='image/png'
                            )
                            if upload_result['success']:
                                image_url = upload_result['url']
                                # Ensure public endpoint
                                if '/storage/v1/object/' in image_url and '/object/public/' not in image_url:
                                    image_url = image_url.replace('/storage/v1/object/', '/storage/v1/object/public/')
                                post.image_url = image_url
                                post.save()
                                logger.info(f"✅ Re-uploaded to Supabase: {image_url[:100]}...")
                                content_type_valid = True
                            else:
                                return {
                                    'success': False,
                                    'error': f'URL bir şəkil deyil. Content-Type: {content_type}. Supabase yenidən yükləmə də uğursuz oldu: {upload_result["error"]}',
                                    'post_id': None,
                                    'post_url': None
                                }
                        else:
                            return {
                                'success': False,
                                'error': f'URL bir şəkil deyil. Content-Type: {content_type}. Instagram yalnız şəkil fayllarını qəbul edir (jpg, png, webp).',
                                'post_id': None,
                                'post_url': None
                            }
                    else:
                        content_type_valid = True
                else:
                    content_type_valid = True
                
                if content_type_valid:
                    logger.info(f"✅ Image URL validated. Content-Type: {content_type}")
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"⚠️ Could not validate image URL: {e}. Continuing anyway, Instagram API will validate.")
                # Continue anyway, Instagram API will validate
            
            # Prepare caption
            caption = post.content
            if post.hashtags:
                caption += '\n\n' + ' '.join(post.hashtags)
            
            # Step 1: Create media container
            container_url = f"https://graph.facebook.com/v18.0/{ig_account_id}/media"
            
            # For Supabase URLs, ensure we're using the signed/public URL format
            # Instagram API sometimes has issues with Supabase Storage URLs
            # Try to verify the URL works before sending to Instagram
            if 'supabase' in image_url.lower():
                logger.info(f"🔍 Verifying Supabase URL before Instagram submission...")
                try:
                    test_response = requests.head(image_url, timeout=5, allow_redirects=True)
                    if test_response.status_code != 200:
                        logger.warning(f"⚠️ Supabase URL returned status {test_response.status_code}")
                    else:
                        content_type = test_response.headers.get('Content-Type', '')
                        logger.info(f"✅ Supabase URL verified. Status: {test_response.status_code}, Content-Type: {content_type}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not verify Supabase URL: {e}")
            
            container_data = {
                'image_url': image_url,
                'caption': caption,
                'access_token': access_token
            }
            
            logger.info(f"📸 Instagram: Creating media container with image_url: {image_url[:100]}...")
            logger.info(f"   Full URL: {image_url}")
            
            container_response = requests.post(container_url, data=container_data, timeout=30)
            
            if container_response.status_code != 200:
                error_data = container_response.json()
                error_message = 'Unknown error'
                error_code = None
                
                if isinstance(error_data, dict):
                    error_obj = error_data.get('error', {})
                    if isinstance(error_obj, dict):
                        error_message = error_obj.get('message', 'Unknown error')
                        error_code = error_obj.get('code')
                        error_type = error_obj.get('type', '')
                        
                        logger.error(f"❌ Instagram API Error (Media Container): {error_message} (Code: {error_code}, Type: {error_type})")
                        logger.error(f"   Full response: {error_data}")
                        logger.error(f"   Image URL used: {image_url}")
                        
                        # If error is about media type, provide more helpful message
                        if 'media type' in error_message.lower() or 'photo or video' in error_message.lower():
                            logger.error(f"   ⚠️ Media type error detected. This usually means:")
                            logger.error(f"      1. URL doesn't return proper Content-Type header")
                            logger.error(f"      2. URL is not publicly accessible")
                            logger.error(f"      3. URL redirects to a non-image resource")
                            logger.error(f"   Try checking the URL manually: {image_url}")
                    else:
                        error_message = str(error_obj)
                        logger.error(f"❌ Instagram API Error: {error_message}")
                else:
                    error_message = str(error_data)
                    logger.error(f"❌ Instagram API Error: {error_message}")
                
                return {
                    'success': False,
                    'error': f"Instagram API Error: {error_message}",
                    'error_code': error_code,
                    'post_id': None,
                    'post_url': None
                }
            
            container_data = container_response.json()
            creation_id = container_data.get('id')
            
            if not creation_id:
                logger.error(f"❌ Instagram: No creation_id in response: {container_data}")
                return {
                    'success': False,
                    'error': 'Instagram media container yaradıla bilmədi',
                    'post_id': None,
                    'post_url': None
                }
            
            logger.info(f"✅ Instagram: Media container created with ID: {creation_id}")
            
            # Step 2: Publish the media
            publish_url = f"https://graph.facebook.com/v18.0/{ig_account_id}/media_publish"
            
            publish_data = {
                'creation_id': creation_id,
                'access_token': access_token
            }
            
            logger.info(f"📤 Instagram: Publishing media with creation_id: {creation_id}")
            
            publish_response = requests.post(publish_url, data=publish_data, timeout=30)
            
            if publish_response.status_code != 200:
                error_data = publish_response.json()
                error_message = 'Unknown error'
                error_code = None
                
                if isinstance(error_data, dict):
                    error_obj = error_data.get('error', {})
                    if isinstance(error_obj, dict):
                        error_message = error_obj.get('message', 'Unknown error')
                        error_code = error_obj.get('code')
                        error_type = error_obj.get('type', '')
                        
                        logger.error(f"❌ Instagram API Error (Media Publish): {error_message} (Code: {error_code}, Type: {error_type})")
                        logger.error(f"   Full response: {error_data}")
                    else:
                        error_message = str(error_obj)
                        logger.error(f"❌ Instagram API Error: {error_message}")
                else:
                    error_message = str(error_data)
                    logger.error(f"❌ Instagram API Error: {error_message}")
                
                return {
                    'success': False,
                    'error': f"Instagram Media Publish Error: {error_message}",
                    'error_code': error_code,
                    'post_id': None,
                    'post_url': None
                }
            
            publish_data = publish_response.json()
            ig_post_id = publish_data.get('id')
            
            if not ig_post_id:
                logger.warning(f"⚠️ Instagram: Response received but no 'id' field: {publish_data}")
                return {
                    'success': False,
                    'error': 'Instagram paylaşımı uğurlu oldu, amma post ID alına bilmədi',
                    'post_id': None,
                    'post_url': None
                }
            
            logger.info(f"✅ Instagram: Post successfully published with ID: {ig_post_id}")
            
            return {
                'success': True,
                'post_id': ig_post_id,
                'error': None,
                'post_url': None  # Instagram doesn't provide direct post URLs in API response
            }
            
        except Exception as e:
            error_msg = f"Instagram paylaşım xətası: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return {
                'success': False,
                'error': error_msg,
                'post_id': None,
                'post_url': None
            }


# Singleton instance
_publisher = None

def get_publisher():
    """Get singleton instance of SocialMediaPublisher"""
    global _publisher
    if _publisher is None:
        _publisher = SocialMediaPublisher()
    return _publisher

