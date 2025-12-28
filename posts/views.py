from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404, redirect
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
import requests
import secrets
import logging
import os

logger = logging.getLogger(__name__)
from .models import Post, AIGeneratedContent, ContentTemplate, PostPlatform, PostPerformance
from .serializers import (
    PostSerializer, 
    PostUpdateSerializer,
    AIGeneratedContentSerializer,
    PostApprovalSerializer,
    PostGenerationRequestSerializer,
    ContentTemplateSerializer,
    PostPerformanceSerializer
)
from .services import PostGenerationService
from .post_analytics import PostAnalyticsService


class PostListCreateView(generics.ListCreateAPIView):
    """List and create posts"""
    
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Post.objects.filter(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """Override create method to add extensive logging"""
        logger.info("=" * 80)
        logger.info("[DEBUG] 🎯 PostListCreateView.create() called")
        logger.info(f"[DEBUG] User: {request.user.email} (ID: {request.user.id})")
        logger.info(f"[DEBUG] Request method: {request.method}")
        logger.info(f"[DEBUG] Content-Type: {request.content_type}")
        logger.info(f"[DEBUG] Content-Length: {request.META.get('CONTENT_LENGTH', 'N/A')}")
        logger.info(f"[DEBUG] Has FILES: {bool(request.FILES)}")
        if request.FILES:
            logger.info(f"[DEBUG] FILES keys: {list(request.FILES.keys())}")
            for key, file in request.FILES.items():
                logger.info(f"[DEBUG]   - {key}: {file.name}, {file.size} bytes, {file.content_type}")
        
        logger.info(f"[DEBUG] Request data keys: {list(request.data.keys())}")
        logger.info(f"[DEBUG] Request data (first 1000 chars): {str(request.data)[:1000]}")
        
        # Log specific fields
        for field in ['title', 'content', 'description', 'hashtags', 'status', 'scheduled_time', 
                     'design_url', 'image_url', 'custom_image', 'imgly_scene']:
            if field in request.data:
                value = request.data[field]
                if isinstance(value, str) and len(value) > 200:
                    logger.info(f"[DEBUG]   {field}: {value[:200]}... (truncated, total length: {len(value)})")
                else:
                    logger.info(f"[DEBUG]   {field}: {value}")
        
        try:
            # Get serializer
            serializer = self.get_serializer(data=request.data)
            logger.info(f"[DEBUG] Serializer created: {type(serializer).__name__}")
            
            # Validate
            logger.info(f"[DEBUG] Validating serializer...")
            if not serializer.is_valid():
                logger.error(f"[ERROR] ❌ Serializer validation failed!")
                logger.error(f"[ERROR] Validation errors: {serializer.errors}")
                for field, errors in serializer.errors.items():
                    logger.error(f"[ERROR]   - {field}: {errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info(f"[DEBUG] ✅ Serializer is valid")
            logger.info(f"[DEBUG] Validated data keys: {list(serializer.validated_data.keys())}")
            
            # Log validated data
            for key, value in serializer.validated_data.items():
                if isinstance(value, str) and len(value) > 200:
                    logger.info(f"[DEBUG]   validated_data.{key}: {value[:200]}... (truncated)")
                elif isinstance(value, (dict, list)):
                    logger.info(f"[DEBUG]   validated_data.{key}: {type(value).__name__} with {len(value)} items")
                else:
                    logger.info(f"[DEBUG]   validated_data.{key}: {value}")
            
            # Perform create
            logger.info(f"[DEBUG] Saving post...")
            self.perform_create(serializer)
            logger.info(f"[DEBUG] ✅ Post saved successfully")
            logger.info(f"[DEBUG] Post ID: {serializer.instance.id}")
            logger.info(f"[DEBUG] Post status: {serializer.instance.status}")
            logger.info(f"[DEBUG] Post title: {serializer.instance.title}")
            logger.info(f"[DEBUG] Post content length: {len(serializer.instance.content) if serializer.instance.content else 0}")
            
            headers = self.get_success_headers(serializer.data)
            logger.info(f"[DEBUG] Response headers: {headers}")
            logger.info(f"[DEBUG] ✅ Post creation completed successfully")
            logger.info("=" * 80)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
            
        except Exception as e:
            logger.error(f"[ERROR] ❌ Exception during post creation: {e}", exc_info=True)
            logger.error(f"[ERROR] Exception type: {type(e).__name__}")
            logger.error(f"[ERROR] Exception args: {e.args}")
            logger.info("=" * 80)
            raise
    
    def perform_create(self, serializer):
        logger.info(f"[DEBUG] perform_create() called")
        logger.info(f"[DEBUG] User: {serializer.context['request'].user.email}")
        logger.info(f"[DEBUG] Saving post with user assignment...")
        instance = serializer.save(user=self.request.user)
        logger.info(f"[DEBUG] ✅ Post instance created: {instance.id}")
        logger.info(f"[DEBUG] Post instance details:")
        logger.info(f"[DEBUG]   - ID: {instance.id}")
        logger.info(f"[DEBUG]   - Title: {instance.title}")
        logger.info(f"[DEBUG]   - Status: {instance.status}")
        logger.info(f"[DEBUG]   - Content: {instance.content[:100] if instance.content else 'None'}...")
        logger.info(f"[DEBUG]   - Has image: {bool(instance.image_url or instance.custom_image or instance.design_url)}")
        if instance.image_url:
            logger.info(f"[DEBUG]   - image_url: {instance.image_url}")
        if instance.custom_image:
            logger.info(f"[DEBUG]   - custom_image: {instance.custom_image.name}")
        if instance.design_url:
            logger.info(f"[DEBUG]   - design_url: {instance.design_url}")
        return instance
    
    def get_serializer_context(self):
        """Pass request context to serializer"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, and delete posts"""
    
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Post.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return PostUpdateSerializer
        return PostSerializer
    
    def get_serializer_context(self):
        """Pass request context to serializer"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def perform_update(self, serializer):
        """Override to add logging for imgly_scene updates"""
        print("=" * 80)
        print("🔧 PostDetailView.perform_update called")
        print(f"📦 Request data keys: {list(self.request.data.keys())}")
        print(f"🔍 Has imgly_scene in request.data? {('imgly_scene' in self.request.data)}")
        
        if 'imgly_scene' in self.request.data:
            scene_data = self.request.data.get('imgly_scene')
            print(f"📊 imgly_scene type: {type(scene_data)}")
            print(f"📊 imgly_scene length: {len(scene_data) if scene_data else 0}")
            if isinstance(scene_data, str):
                print(f"📊 imgly_scene preview (first 100 chars): {scene_data[:100]}")
        
        # Save the instance
        instance = serializer.save()
        
        print(f"✅ Post saved: {instance.id}")
        print(f"🔍 Post.imgly_scene exists after save? {bool(instance.imgly_scene)}")
        if instance.imgly_scene:
            print(f"📊 Saved imgly_scene type: {type(instance.imgly_scene)}")
            print(f"📊 Saved imgly_scene length: {len(str(instance.imgly_scene))}")
        print("=" * 80)
    
    def update(self, request, *args, **kwargs):
        """Override to return full PostSerializer in response"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Use PostUpdateSerializer for validation
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # But return full PostSerializer for the response
        response_serializer = PostSerializer(instance, context=self.get_serializer_context())
        return Response(response_serializer.data)
    
    def partial_update(self, request, *args, **kwargs):
        """Override PATCH to also return full serializer"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


class PublishPostView(APIView):
    """Publish a post immediately"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id, user=request.user)
            
            # Update post status to published
            post.status = 'published'
            post.published_at = timezone.now()
            post.save()
            
            # Return updated post
            serializer = PostSerializer(post, context={'request': request})
            return Response({
                'message': 'Paylaşım uğurla dərc edildi',
                'post': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Post.DoesNotExist:
            return Response({
                'error': 'Paylaşım tapılmadı'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class PublishToFacebookView(APIView):
    """Publish a post to Facebook Page using multipart/form-data for image upload"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, post_id):
        try:
            from social_accounts.models import SocialAccount
            
            # Get the post
            post = Post.objects.get(id=post_id, user=request.user)
            
            # Get user's Facebook account
            facebook_account = SocialAccount.objects.filter(
                user=request.user,
                platform='facebook',
                is_active=True
            ).first()
            
            if not facebook_account:
                return Response({
                    'error': 'Facebook hesabı bağlı deyil'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get page access token
            page_token = facebook_account.get_access_token()
            page_id = facebook_account.platform_user_id
            
            # Prepare post message
            message = post.content
            if post.hashtags:
                message += '\n\n' + ' '.join(post.hashtags)
            
            # Facebook API endpoint for photos
            fb_api_url = f"https://graph.facebook.com/v18.0/{page_id}/photos"
            
            # Check if post has an image
            if post.custom_image:
                # Get local file path
                image_path = post.custom_image.path
                
                # Verify file exists
                if not os.path.exists(image_path):
                    return Response({
                        'error': f'Şəkil faylı tapılmadı: {image_path}'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Prepare multipart/form-data request
                try:
                    with open(image_path, 'rb') as image_file:
                        files = {
                            'source': (os.path.basename(image_path), image_file, 'image/png')
                        }
                        
                        # Prepare form data with message and access token
                        data = {
                            'message': message,
                            'access_token': page_token
                        }
                        
                        logger.info(f"📸 Facebook: Uploading image from {image_path} to page {page_id}")
                        
                        # Make POST request with multipart/form-data
                        response = requests.post(
                            fb_api_url,
                            files=files,
                            data=data,
                            timeout=30
                        )
                        
                except IOError as e:
                    logger.error(f"❌ Facebook: Error reading image file: {str(e)}")
                    return Response({
                        'error': f'Şəkil faylını oxumaq mümkün olmadı: {str(e)}'
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            else:
                # Text-only post (no image)
                post_data = {
                    'message': message,
                    'access_token': page_token
                }
                fb_api_url = f"https://graph.facebook.com/v18.0/{page_id}/feed"
                
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
                        
                        return Response({
                            'error': f"Facebook API Error: {error_message}",
                            'error_code': error_code,
                            'error_type': error_type
                        }, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        error_message = str(error_obj)
                        logger.error(f"❌ Facebook API Error: {error_message}")
                        return Response({
                            'error': f"Facebook API Error: {error_message}"
                        }, status=status.HTTP_400_BAD_REQUEST)
                        
                except ValueError:
                    # Response is not JSON
                    logger.error(f"❌ Facebook API Error: Non-JSON response: {response.text}")
                    return Response({
                        'error': f"Facebook API Error: {response.text}"
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Success - parse response
            fb_post_data = response.json()
            fb_post_id = fb_post_data.get('id')
            
            if not fb_post_id:
                logger.warning(f"⚠️ Facebook: Response received but no 'id' field: {fb_post_data}")
                return Response({
                    'error': 'Facebook paylaşımı uğurlu oldu, amma post ID alına bilmədi',
                    'response': fb_post_data
                }, status=status.HTTP_200_OK)
            
            logger.info(f"✅ Facebook: Post successfully published with ID: {fb_post_id}")
            
            # Update post status
            post.status = 'published'
            post.published_at = timezone.now()
            post.save()
            
            return Response({
                'message': 'Facebook-a uğurla paylaşıldı',
                'facebook_post_id': fb_post_id,
                'post': PostSerializer(post, context={'request': request}).data
            }, status=status.HTTP_200_OK)
            
        except Post.DoesNotExist:
            return Response({
                'error': 'Paylaşım tapılmadı'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"❌ Facebook publish error: {str(e)}", exc_info=True)
            import traceback
            traceback.print_exc()
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class PublishToInstagramView(APIView):
    """Publish a post to Instagram Business Account"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, post_id):
        try:
            from social_accounts.models import SocialAccount
            
            # Get the post
            post = Post.objects.get(id=post_id, user=request.user)
            
            # Get user's Instagram account
            instagram_account = SocialAccount.objects.filter(
                user=request.user,
                platform='instagram',
                is_active=True
            ).first()
            
            if not instagram_account:
                return Response({
                    'error': 'Instagram hesabı bağlı deyil'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get access token and Instagram account ID
            access_token = instagram_account.get_access_token()
            ig_account_id = instagram_account.platform_user_id
            
            # Get image URL - prioritize custom_image (uploaded to media/)
            image_url = None
            if post.custom_image:
                # Get absolute URL for custom_image (media file)
                if hasattr(post.custom_image, 'url'):
                    # Build absolute URL using request
                    image_url = request.build_absolute_uri(post.custom_image.url)
                else:
                    # Fallback: construct URL manually
                    relative_url = str(post.custom_image)
                    if not relative_url.startswith('/'):
                        relative_url = '/' + relative_url
                    image_url = f"{settings.BACKEND_URL}{relative_url}"
            elif post.design_url:
                # Check if design_url is already absolute
                if post.design_url.startswith('http'):
                    image_url = post.design_url
                else:
                    # Build absolute URL
                    if not post.design_url.startswith('/'):
                        image_url = f"{settings.BACKEND_URL}/{post.design_url}"
                    else:
                        image_url = f"{settings.BACKEND_URL}{post.design_url}"
            elif hasattr(post, 'design_url_absolute') and post.design_url_absolute:
                image_url = post.design_url_absolute
            
            if not image_url:
                return Response({
                    'error': 'Instagram paylaşımı üçün şəkil tələb olunur'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Make sure it's a full URL (fallback)
            if not image_url.startswith('http'):
                image_url = f"{settings.BACKEND_URL}{image_url}"
            
            # Instagram API requires public HTTPS URL that Instagram can access
            # Check if URL is localhost (Instagram can't access localhost)
            if 'localhost' in image_url or '127.0.0.1' in image_url:
                # In development, provide helpful error message
                if settings.DEBUG:
                    return Response({
                        'error': 'Instagram API localhost URL-lərini qəbul etmir. Production mühitində BACKEND_URL-in public olması lazımdır. Development-da test etmək üçün şəkli public bir yere (Cloudinary, Imgur, vb.) yükləyin.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                else:
                    # In production, this shouldn't happen if BACKEND_URL is set correctly
                    logger.warning(f"⚠️  Instagram: Image URL contains localhost in production: {image_url}")
                    return Response({
                        'error': 'Image URL localhost içərir. BACKEND_URL-in public olması lazımdır.'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate that URL is actually an image (Instagram requirement)
            try:
                head_response = requests.head(image_url, timeout=5, allow_redirects=True)
                content_type = head_response.headers.get('Content-Type', '').lower()
                
                # Instagram only accepts image/jpeg, image/png, image/webp
                if not content_type.startswith('image/'):
                    # If HEAD doesn't work, try GET with stream
                    img_response = requests.get(image_url, stream=True, timeout=5)
                    content_type = img_response.headers.get('Content-Type', '').lower()
                    
                    if not content_type.startswith('image/'):
                        return Response({
                            'error': f'URL bir şəkil deyil. Content-Type: {content_type}. Instagram yalnız şəkil fayllarını qəbul edir (jpg, png, webp).'
                        }, status=status.HTTP_400_BAD_REQUEST)
            except requests.exceptions.RequestException as e:
                logger.warning(f"Could not verify image URL: {e}")
                # Continue anyway, Instagram API will validate
            
            # Ensure URL is HTTPS (Instagram requirement)
            if image_url.startswith('http://') and not image_url.startswith('https://'):
                # Try to convert to HTTPS
                image_url = image_url.replace('http://', 'https://', 1)
            
            # Step 1: Create media container
            caption = post.content
            if post.hashtags:
                caption += '\n\n' + ' '.join(post.hashtags)
            
            # Instagram API requires specific parameters
            container_data = {
                'image_url': image_url,
                'caption': caption,
                'access_token': access_token
            }
            
            logger.info(f"📸 Instagram: Creating media container with image_url: {image_url[:100]}...")
            
            container_url = f"https://graph.facebook.com/v18.0/{ig_account_id}/media"
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
                        
                        # More specific error messages
                        if 'media type' in error_message.lower() or error_code == 100:
                            error_message = f"Şəkil URL-i düzgün deyil. Instagram yalnız şəkil fayllarını qəbul edir (jpg, png, webp). URL: {image_url[:100]}..."
                        elif 'permission' in error_message.lower() or error_code == 10:
                            error_message = "Instagram izinləri kifayət deyil. Zəhmət olmasa, Instagram hesabınızı yenidən qoşun və 'instagram_content_publish' iznini verin."
                        elif 'invalid' in error_message.lower():
                            error_message = f"Şəkil URL-i etibarsızdır və ya Instagram tərəfindən əldə edilə bilmir. URL: {image_url[:100]}..."
                    else:
                        error_message = str(error_obj)
                else:
                    error_message = str(error_data)
                
                logger.error(f"❌ Instagram API Error: {error_message} (Code: {error_code})")
                logger.error(f"   Image URL: {image_url}")
                logger.error(f"   Response: {error_data}")
                
                return Response({
                    'error': f"Instagram API Error: {error_message}",
                    'error_code': error_code,
                    'image_url': image_url[:100] + '...' if len(image_url) > 100 else image_url
                }, status=status.HTTP_400_BAD_REQUEST)
            
            container_id = container_response.json().get('id')
            
            # Step 2: Publish the media
            publish_data = {
                'creation_id': container_id,
                'access_token': access_token
            }
            
            publish_url = f"https://graph.facebook.com/v18.0/{ig_account_id}/media_publish"
            publish_response = requests.post(publish_url, data=publish_data, timeout=30)
            
            if publish_response.status_code != 200:
                error_data = publish_response.json()
                return Response({
                    'error': f"Instagram Publish Error: {error_data.get('error', {}).get('message', 'Unknown error')}"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            ig_post_data = publish_response.json()
            
            # Update post status
            post.status = 'published'
            post.published_at = timezone.now()
            post.save()
            
            return Response({
                'message': 'Instagram-a uğurla paylaşıldı',
                'instagram_post_id': ig_post_data.get('id'),
                'post': PostSerializer(post, context={'request': request}).data
            }, status=status.HTTP_200_OK)
            
        except Post.DoesNotExist:
            return Response({
                'error': 'Paylaşım tapılmadı'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"❌ Instagram publish error: {str(e)}", exc_info=True)
            import traceback
            traceback.print_exc()
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class PublishToLinkedInView(APIView):
    """Publish a post to LinkedIn"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, post_id):
        try:
            from social_accounts.models import SocialAccount
            import logging
            logger = logging.getLogger(__name__)
            
            # Get the post
            post = Post.objects.get(id=post_id, user=request.user)
            
            # Check if user wants to post to Company Page or personal account
            company_page_id = request.data.get('company_page_id', None)
            
            # Get LinkedIn account (Company Page or personal)
            if company_page_id:
                # Post to Company Page
                linkedin_account = SocialAccount.objects.filter(
                    user=request.user,
                    platform='linkedin',
                    platform_user_id=company_page_id,
                    is_active=True,
                    settings__is_company_page=True
                ).first()
                
                if not linkedin_account:
                    return Response({
                        'error': 'LinkedIn Company Page tapılmadı'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Use organization URN for Company Page
                author_urn = f"urn:li:organization:{company_page_id}"
            else:
                # Post to personal account (default)
                # Get LinkedIn account (prefer non-company page, but fallback to any if needed)
                linkedin_accounts = SocialAccount.objects.filter(
                    user=request.user,
                    platform='linkedin',
                    is_active=True
                )
                
                logger.info(f"🔍 Looking for LinkedIn account for user {request.user.email}")
                logger.info(f"   Total LinkedIn accounts found: {linkedin_accounts.count()}")
                
                # Try to find personal account (not a company page)
                linkedin_account = None
                for account in linkedin_accounts:
                    # Check if it's a company page
                    is_company_page = False
                    if account.settings:
                        is_company_page = account.settings.get('is_company_page', False)
                    logger.info(f"   Account ID: {account.platform_user_id}, is_company_page: {is_company_page}, settings: {account.settings}")
                    if not is_company_page:
                        linkedin_account = account
                        logger.info(f"✅ Found personal LinkedIn account: {account.platform_user_id}")
                        break
                
                # If no personal account found, use first account (fallback)
                if not linkedin_account and linkedin_accounts.exists():
                    linkedin_account = linkedin_accounts.first()
                    logger.info(f"⚠️ Using first LinkedIn account as fallback: {linkedin_account.platform_user_id}")
                
                if not linkedin_account:
                    logger.error(f"❌ No LinkedIn account found for user {request.user.email}")
                    return Response({
                        'error': 'LinkedIn hesabı bağlı deyil'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Use person URN for personal account
                linkedin_user_id = linkedin_account.platform_user_id
                author_urn = f"urn:li:person:{linkedin_user_id}"
            
            # Get access token
            access_token = linkedin_account.get_access_token()
            
            # Prepare the post content
            post_text = post.content
            if post.hashtags:
                post_text += '\n\n' + ' '.join(post.hashtags)
            
            # Get image URL if exists
            image_url = None
            if post.custom_image:
                image_url = post.custom_image.url if hasattr(post.custom_image, 'url') else str(post.custom_image)
            elif hasattr(post, 'design_url_absolute') and post.design_url_absolute:
                image_url = post.design_url_absolute
            
            # Make sure it's a full URL
            if image_url and not image_url.startswith('http'):
                image_url = f"{settings.BACKEND_URL}{image_url}"
            
            if image_url:
                # Upload image to LinkedIn first
                logger.info(f"📸 Uploading image to LinkedIn: {image_url}")
                
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
                        'Content-Type': 'application/json',
                        'X-Restli-Protocol-Version': '2.0.0'
                    },
                    json=register_payload
                )
                
                if register_response.status_code != 200:
                    error_data = register_response.json()
                    logger.error(f"❌ LinkedIn register upload error: {error_data}")
                    return Response({
                        'error': f"LinkedIn register upload error: {error_data.get('message', 'Unknown error')}"
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                register_data = register_response.json()
                asset_urn = register_data['value']['asset']
                upload_url = register_data['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
                
                logger.info(f"✅ Got upload URL and asset URN: {asset_urn}")
                
                # Step 2: Download the image
                image_response = requests.get(image_url)
                if image_response.status_code != 200:
                    return Response({
                        'error': 'Failed to download image'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                image_data = image_response.content
                
                # Step 3: Upload the image to LinkedIn
                upload_response = requests.put(
                    upload_url,
                    headers={
                        'Authorization': f'Bearer {access_token}',
                        'Content-Type': 'application/octet-stream'
                    },
                    data=image_data
                )
                
                if upload_response.status_code not in [200, 201]:
                    logger.error(f"❌ LinkedIn image upload error: {upload_response.text}")
                    return Response({
                        'error': f"Failed to upload image to LinkedIn"
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                logger.info(f"✅ Image uploaded successfully")
                
                # Step 4: Create UGC post with image
                ugc_payload = {
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
                                    "description": {
                                        "text": post.description or post_text[:100]
                                    },
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
                ugc_payload = {
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
            
            # Publish the post
            logger.info(f"📤 Publishing to LinkedIn...")
            ugc_response = requests.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json',
                    'X-Restli-Protocol-Version': '2.0.0'
                },
                json=ugc_payload
            )
            
            if ugc_response.status_code not in [200, 201]:
                error_data = ugc_response.json()
                logger.error(f"❌ LinkedIn publish error: {error_data}")
                return Response({
                    'error': f"LinkedIn API Error: {error_data.get('message', 'Unknown error')}"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            ugc_data = ugc_response.json()
            linkedin_post_id = ugc_data.get('id')
            
            logger.info(f"✅ Published to LinkedIn: {linkedin_post_id}")
            
            # Update post status
            post.status = 'published'
            post.published_at = timezone.now()
            post.save()
            
            return Response({
                'message': 'LinkedIn-ə uğurla paylaşıldı',
                'linkedin_post_id': linkedin_post_id,
                'post': PostSerializer(post, context={'request': request}).data
            }, status=status.HTTP_200_OK)
            
        except Post.DoesNotExist:
            return Response({
                'error': 'Paylaşım tapılmadı'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"LinkedIn publish error: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class GeneratePostsView(APIView):
    """Generate AI posts with ChatGPT and Canva integration"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        import logging
        logger = logging.getLogger(__name__)
        
        serializer = PostGenerationRequestSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        try:
            logger.info(f"Starting post generation for user: {request.user.email}")
            
            # Get custom prompt if provided
            custom_prompt = serializer.validated_data.get('custom_prompt', '')
            
            service = PostGenerationService(user=request.user)
            ai_batch, posts = service.generate_monthly_content(request.user, custom_prompt=custom_prompt)
            
            logger.info(f"Successfully generated {len(posts)} posts for user: {request.user.email}")
            
            return Response({
                'message': 'Posts generated successfully',
                'batch_id': ai_batch.id,
                'total_posts': len(posts),
                'posts': PostSerializer(posts, many=True, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            logger.error(f"ValueError in post generation: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Exception in post generation: {str(e)}", exc_info=True)
            return Response({
                'error': f'Failed to generate posts: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PostApprovalView(APIView):
    """Approve or reject generated posts"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = PostApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        action = serializer.validated_data['action']
        post_ids = serializer.validated_data['post_ids']
        
        service = PostGenerationService()
        updated_posts = []
        
        for post_id in post_ids:
            try:
                if action == 'approve':
                    post = service.approve_post(post_id, request.user)
                else:  # reject
                    post = service.reject_post(post_id, request.user)
                updated_posts.append(post)
            except ValueError as e:
                continue  # Skip invalid posts
        
        return Response({
            'message': f'{len(updated_posts)} posts {action}d successfully',
            'updated_posts': PostSerializer(updated_posts, many=True, context={'request': request}).data
        }, status=status.HTTP_200_OK)


class PendingPostsView(generics.ListAPIView):
    """List posts pending approval"""
    
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Post.objects.filter(
            user=self.request.user,
            status='pending_approval'
        ).order_by('-created_at')
    
    def get_serializer_context(self):
        """Pass request context to serializer"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class UploadCustomImageView(APIView):
    """Upload custom image for a post"""
    
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def options(self, request, post_id):
        """Handle preflight OPTIONS request"""
        from django.http import HttpResponse
        response = HttpResponse()
        response['Access-Control-Allow-Origin'] = request.META.get('HTTP_ORIGIN', '*')
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
        response['Access-Control-Allow-Credentials'] = 'true'
        return response
    
    def post(self, request, post_id):
        try:
            post = get_object_or_404(Post, id=post_id, user=request.user)
            
            if 'image' not in request.FILES:
                return Response({
                    'error': 'No image file provided'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            image_file = request.FILES['image']
            
            # Validate image file (increased to 10MB to match server limits)
            if image_file.size > 10 * 1024 * 1024:  # 10MB limit
                return Response({
                    'error': f'Image file too large ({image_file.size / 1024 / 1024:.2f}MB). Maximum size is 10MB.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            service = PostGenerationService()
            updated_post = service.upload_custom_image(post_id, request.user, image_file)
            
            response_data = Response({
                'message': 'Image uploaded successfully',
                'post': PostSerializer(updated_post, context={'request': request}).data
            }, status=status.HTTP_200_OK)
            
            # Add CORS headers explicitly
            response_data['Access-Control-Allow-Origin'] = request.META.get('HTTP_ORIGIN', '*')
            response_data['Access-Control-Allow-Credentials'] = 'true'
            
            return response_data
            
        except Exception as e:
            return Response({
                'error': 'Failed to upload image'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ApplyBrandingView(APIView):
    """Apply company branding (logo + slogan) to a post's image"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, post_id):
        try:
            import logging
            logger = logging.getLogger(__name__)
            from .branding import ImageBrandingService
            from accounts.models import CompanyProfile
            from django.core.files.base import ContentFile
            
            # Get the post
            post = get_object_or_404(Post, id=post_id, user=request.user)
            
            # Get company profile
            try:
                company_profile = CompanyProfile.objects.get(user=request.user)
            except CompanyProfile.DoesNotExist:
                return Response({
                    'error': 'Şirkət profili tapılmadı. Əvvəlcə şirkət profilini tamamlayın.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if branding is enabled
            if not company_profile.branding_enabled:
                return Response({
                    'error': 'Brending deaktivdir. Şirkət parametrlərində aktivləşdirin.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if logo exists
            if not company_profile.logo:
                return Response({
                    'error': 'Şirkət loqosu tapılmadı. Əvvəlcə loqo yükləyin.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get image to brand
            image_path = None
            if post.custom_image:
                image_path = post.custom_image.path
            elif post.design_url:
                # Try to use design_url
                image_path = post.design_url
            else:
                return Response({
                    'error': 'Bu postda brending tətbiq ediləcək şəkil yoxdur.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info(f"🎨 Applying branding to post {post_id}")
            logger.info(f"   Logo: {company_profile.logo.path}")
            logger.info(f"   Slogan: {company_profile.slogan or 'None'}")
            logger.info(f"   Position: {company_profile.logo_position}")
            
            # Apply branding
            branding_service = ImageBrandingService(company_profile)
            branded_image = branding_service.apply_branding(image_path)
            
            # Save branded image
            output = branding_service.save_branded_image(branded_image, format='PNG')
            
            # Update post with branded image
            filename = f"branded_{post_id}.png"
            post.custom_image.save(filename, ContentFile(output.read()), save=True)
            
            logger.info(f"✅ Branding applied successfully to post {post_id}")
            
            return Response({
                'message': 'Brending uğurla tətbiq edildi',
                'post': PostSerializer(post, context={'request': request}).data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            logger.error(f"❌ Branding error: {str(e)}")
            traceback.print_exc()
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class AIGeneratedContentListView(generics.ListAPIView):
    """List AI generated content batches"""
    
    serializer_class = AIGeneratedContentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return AIGeneratedContent.objects.filter(user=self.request.user)


class ContentTemplateListCreateView(generics.ListCreateAPIView):
    """List and create content templates"""
    
    serializer_class = ContentTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return ContentTemplate.objects.filter(user=self.request.user, is_active=True)


class ContentTemplateDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, and delete content templates"""
    
    serializer_class = ContentTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return ContentTemplate.objects.filter(user=self.request.user)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def post_stats(request):
    """Get post statistics for the user"""
    
    user = request.user
    
    stats = {
        'total_posts': Post.objects.filter(user=user).count(),
        'pending_approval': Post.objects.filter(user=user, status='pending_approval').count(),
        'approved_posts': Post.objects.filter(user=user, status='approved').count(),
        'scheduled_posts': Post.objects.filter(user=user, status='scheduled').count(),
        'published_posts': Post.objects.filter(user=user, status='published').count(),
        'draft_posts': Post.objects.filter(user=user, status='draft').count(),
        'ai_generated_posts': Post.objects.filter(user=user, ai_generated=True).count(),
        'manual_posts': Post.objects.filter(user=user, ai_generated=False).count(),
    }
    
    return Response(stats)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def regenerate_canva_design(request, post_id):
    """Regenerate design for a specific post using Ideogram.ai"""
    
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        post = get_object_or_404(Post, id=post_id, user=request.user)
        
        from .services import IdeogramService
        ideogram_service = IdeogramService(user=request.user)
        
        design_data = ideogram_service.create_design_for_post(post.content)
        
        post.canva_design_id = design_data['design_id']
        post.design_url = design_data['design_url']
        post.design_thumbnail = design_data['thumbnail_url']
        post.custom_image = None  # Clear custom image
        post.save()
        
        return Response({
            'message': 'Design regenerated successfully',
            'post': PostSerializer(post, context={'request': request}).data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Failed to regenerate design: {e}", exc_info=True)
        return Response({
            'error': 'Failed to regenerate design'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==============================================================================
# DEPRECATED: Canva OAuth Views (Replaced with Placid.app)
# ==============================================================================
# These views are no longer used as we've switched to Placid.app for design generation
# Keeping them commented out for reference
# ==============================================================================

# @api_view(['GET'])
# @permission_classes([permissions.IsAuthenticated])
# def canva_oauth_initiate(request):
#     """Initiate Canva OAuth flow"""
#     state = secrets.token_urlsafe(32)
#     request.session['canva_oauth_state'] = state
#     request.session['canva_user_id'] = str(request.user.id)
#     auth_url = (
#         f"https://www.canva.com/api/oauth/authorize"
#         f"?response_type=code"
#         f"&client_id={settings.CANVA_CLIENT_ID}"
#         f"&redirect_uri={settings.BACKEND_URL}/api/canva/callback/"
#         f"&scope=design:content:read design:content:write design:meta:read asset:read"
#         f"&state={state}"
#     )
#     return Response({'authorization_url': auth_url})


# @api_view(['GET'])
# def canva_oauth_callback(request):
#     """Handle Canva OAuth callback"""
#     # [OAuth callback logic - DEPRECATED]
#     return redirect(f'{settings.FRONTEND_URL}/settings?canva_error=deprecated')


# @api_view(['GET'])
# @permission_classes([permissions.IsAuthenticated])
# def canva_connection_status(request):
#     """Check if user has connected Canva"""
#     return Response({
#         'connected': False,
#         'message': 'Canva integration has been replaced with Placid.app'
#     })


class OptimalTimingView(APIView):
    """Get optimal posting times for platforms"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        from .optimal_timing import OptimalTimingService
        from social_accounts.models import SocialAccount
        
        platforms = request.GET.getlist('platforms', [])
        days_ahead = int(request.GET.get('days_ahead', 7))
        
        # If no platforms specified, get user's connected platforms
        if not platforms:
            connected_accounts = SocialAccount.objects.filter(
                user=request.user,
                is_active=True
            )
            platforms = list(connected_accounts.values_list('platform', flat=True).distinct())
        
        if not platforms:
            return Response({
                'error': 'No platforms specified or connected'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        timing_service = OptimalTimingService(user=request.user)
        
        # Get optimal times for each platform
        platform_times = timing_service.get_best_time_for_platforms(
            platforms=platforms,
            days_ahead=days_ahead
        )
        
        # Get common optimal times (for multiple platforms)
        common_times = timing_service.find_common_optimal_time(
            platforms=platforms,
            days_ahead=days_ahead
        )
        
        # Format response
        result = {
            'platforms': {},
            'common_times': []
        }
        
        for platform, suggestions in platform_times.items():
            result['platforms'][platform] = [
                {
                    'datetime': s['datetime'].isoformat(),
                    'date': s['date'].isoformat(),
                    'time': s['time'].strftime('%H:%M'),
                    'hour': s['hour'],
                    'day_name': s['day_name'],
                    'score': round(s['score'], 2)
                }
                for s in suggestions[:5]  # Top 5 per platform
            ]
        
        result['common_times'] = [
            {
                'datetime': ct['datetime'].isoformat(),
                'date': ct['date'].isoformat(),
                'time': ct['time'].strftime('%H:%M'),
                'platforms': ct['platforms'],
                'total_score': round(ct['total_score'], 2),
                'platform_count': ct['platform_count']
            }
            for ct in common_times[:10]  # Top 10 common times
        ]
        
        return Response(result, status=status.HTTP_200_OK)


class SchedulePostView(APIView):
    """Schedule a post for specific platforms at optimal times"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, post_id):
        from .optimal_timing import OptimalTimingService
        from social_accounts.models import SocialAccount
        from django.utils.dateparse import parse_datetime
        
        try:
            post = Post.objects.get(id=post_id, user=request.user)
        except Post.DoesNotExist:
            return Response({
                'error': 'Post tapılmadı'
            }, status=status.HTTP_404_NOT_FOUND)
        
        platforms = request.data.get('platforms', [])
        scheduled_time = request.data.get('scheduled_time')
        use_optimal = request.data.get('use_optimal', False)
        
        if not platforms:
            return Response({
                'error': 'Platform seçilməyib'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # If use_optimal, get optimal time for selected platforms
        if use_optimal:
            timing_service = OptimalTimingService(user=request.user)
            common_times = timing_service.find_common_optimal_time(
                platforms=platforms,
                days_ahead=7
            )
            
            if common_times:
                # Use the best common time
                optimal_time = common_times[0]['datetime']
                scheduled_time = optimal_time.isoformat()
            else:
                # Fallback: use first platform's best time
                platform_times = timing_service.get_best_time_for_platforms(
                    platforms=platforms,
                    days_ahead=7
                )
                if platform_times and platforms[0] in platform_times:
                    suggestions = platform_times[platforms[0]]
                    if suggestions:
                        optimal_time = suggestions[0]['datetime']
                        scheduled_time = optimal_time.isoformat()
        
        if not scheduled_time:
            return Response({
                'error': 'Zaman təyin edilməyib'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Parse scheduled time
        try:
            scheduled_datetime = parse_datetime(scheduled_time)
            if scheduled_datetime is None:
                scheduled_datetime = timezone.datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return Response({
                'error': 'Yanlış tarix formatı'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Make timezone aware
        if timezone.is_naive(scheduled_datetime):
            scheduled_datetime = timezone.make_aware(scheduled_datetime)
        
        # Check if time is in the past
        if scheduled_datetime <= timezone.now():
            return Response({
                'error': 'Zamanlanmış tarix keçmişdə ola bilməz'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update post
        post.scheduled_time = scheduled_datetime
        post.status = 'scheduled'
        post.save()
        
        # Create PostPlatform entries for each platform
        from .models import PostPlatform
        created_platforms = []
        
        for platform_name in platforms:
            try:
                social_account = SocialAccount.objects.get(
                    user=request.user,
                    platform=platform_name.lower(),
                    is_active=True
                )
                
                post_platform, created = PostPlatform.objects.update_or_create(
                    post=post,
                    social_account=social_account,
                    defaults={
                        'status': 'pending',
                        'platform_specific_data': {
                            'scheduled_time': scheduled_datetime.isoformat()
                        }
                    }
                )
                created_platforms.append({
                    'platform': platform_name,
                    'status': 'scheduled',
                    'scheduled_time': scheduled_datetime.isoformat()
                })
            except SocialAccount.DoesNotExist:
                continue
        
        return Response({
            'message': 'Post uğurla zamanlandı',
            'post': PostSerializer(post, context={'request': request}).data,
            'scheduled_time': scheduled_datetime.isoformat(),
            'platforms': created_platforms
        }, status=status.HTTP_200_OK)

from urllib.parse import urlparse
import socket
import ipaddress
import requests
import logging

from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework import permissions, status
from rest_framework.response import Response

logger = logging.getLogger(__name__)

# Yalnız bu host-lara icazə verilir (exact və ya subdomain)
ALLOWED_HOST_SUFFIXES = (
    "cdninstagram.com",
    "instagram.com",
    "licdn.com",
    "linkedin.com",
    "fbcdn.net",
    "facebook.com",
)

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5MB limit (lazıma görə tənzimləyin)
CONNECT_TIMEOUT = 3.05
READ_TIMEOUT = 10

def host_is_allowed(hostname: str) -> bool:
    """Yalnız icazə verilmiş domain və ya onun subdomain-ləri."""
    h = (hostname or "").lower().rstrip(".")
    return any(h == d or h.endswith("." + d) for d in ALLOWED_HOST_SUFFIXES)

def resolves_to_public_ip(hostname: str) -> bool:
    """DNS rebinding / SSRF qoruması: host yalnız public IP-lərə resolve olmalıdır."""
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False

    for _, _, _, _, sockaddr in infos:
        ip = ipaddress.ip_address(sockaddr[0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        ):
            return False
    return True

def pick_referer(hostname: str) -> str:
    h = (hostname or "").lower()
    if h.endswith("licdn.com") or h.endswith("linkedin.com"):
        return "https://www.linkedin.com/"
    if h.endswith("fbcdn.net") or h.endswith("facebook.com"):
        return "https://www.facebook.com/"
    return "https://www.instagram.com/"

@api_view(["GET"])
# ✅ TÖVSİYƏ OLUNUR: auth tələb edin ki, istənilən bot bandwidth-inizi istifadə etməsin
# Əgər mütləq public qalmalıdırsa, [] edin, amma EDGE throttling-i KEÇMƏYİN
@permission_classes([permissions.IsAuthenticated])
def proxy_image(request):
    """
    Təhlükəsiz image proxy:
    - Strict hostname allowlist (substring bypass yoxdur)
    - Redirect-lər yoxdur
    - Private/reserved IP-lər bloklanır
    - Stream + ölçü limiti
    - image/* content-type məcburidir
    """
    image_url = (request.GET.get("url") or "").strip()
    
    logger.info(f"🖼️ Proxy image request: {image_url[:100]}")

    if not image_url:
        logger.warning("Proxy image: URL parametri yoxdur")
        return Response({"error": "URL parametri tələb olunur"}, status=status.HTTP_400_BAD_REQUEST)

    # URL parse və yoxlama
    try:
        parsed = urlparse(image_url)
    except Exception:
        return Response({"error": "Yanlış URL"}, status=status.HTTP_400_BAD_REQUEST)

    if parsed.scheme != "https" or not parsed.hostname:
        return Response({"error": "Yalnız https URL-lərə icazə verilir"}, status=status.HTTP_400_BAD_REQUEST)

    hostname = parsed.hostname.lower().rstrip(".")

    # Strict host allowlist
    if not host_is_allowed(hostname):
        logger.warning("Proxy image: icazəsiz host: %s", hostname)
        return Response({"error": "Host icazəli deyil"}, status=status.HTTP_400_BAD_REQUEST)

    # DNS rebinding / internal IP qoruması
    if not resolves_to_public_ip(hostname):
        logger.warning("Proxy image: bloklanmış host (public IP deyil): %s", hostname)
        return Response({"error": "Bloklanmış host"}, status=status.HTTP_400_BAD_REQUEST)

    referer = pick_referer(hostname)

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "image/*,*/*;q=0.8",
        "Referer": referer,
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        resp = requests.get(
            image_url,
            headers=headers,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            stream=True,
            allow_redirects=False,  # ✅ KRİTİK
        )
    except requests.exceptions.Timeout:
        return Response({"error": "Request timeout"}, status=status.HTTP_504_GATEWAY_TIMEOUT)
    except requests.exceptions.RequestException:
        return Response({"error": "Şəbəkə xətası"}, status=status.HTTP_502_BAD_GATEWAY)

    if resp.status_code != 200:
        return Response({"error": f"Image fetch uğursuzdur: {resp.status_code}"}, status=status.HTTP_502_BAD_GATEWAY)

    content_type = (resp.headers.get("Content-Type") or "").lower()
    if not content_type.startswith("image/"):
        return Response({"error": "Upstream content image deyil"}, status=status.HTTP_400_BAD_REQUEST)

    total = 0
    chunks = []
    for chunk in resp.iter_content(chunk_size=8192):
        if not chunk:
            continue
        total += len(chunk)
        if total > MAX_IMAGE_BYTES:
            return Response({"error": "Image çox böyükdür"}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        chunks.append(chunk)

    body = b"".join(chunks)
    http_resp = HttpResponse(body, content_type=content_type)
    
    # CORS headers - development və production
    origin = request.META.get('HTTP_ORIGIN', '')
    if origin and (origin.startswith('http://localhost:') or origin.startswith('https://timera.az')):
        http_resp["Access-Control-Allow-Origin"] = origin
    else:
        # Production default
        http_resp["Access-Control-Allow-Origin"] = "https://timera.az"
    
    http_resp["Access-Control-Allow-Credentials"] = "true"
    http_resp["Cache-Control"] = "public, max-age=3600"
    return http_resp



class PostPerformanceView(APIView):
    """Get and update post performance metrics"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, post_id):
        """Get performance metrics for a post"""
        post = get_object_or_404(Post, id=post_id, user=request.user)
        
        # Get all platform posts for this post
        platform_posts = PostPlatform.objects.filter(post=post)
        
        # Get performance metrics for each platform
        performances = []
        for platform_post in platform_posts:
            try:
                performance = PostPerformance.objects.get(post_platform=platform_post)
                performances.append(PostPerformanceSerializer(performance).data)
            except PostPerformance.DoesNotExist:
                # Return empty metrics if not fetched yet
                performances.append({
                    'post_platform': str(platform_post.id),
                    'platform': platform_post.social_account.platform,
                    'post_title': post.title,
                    'likes': 0,
                    'comments': 0,
                    'shares': 0,
                    'saves': 0,
                    'reach': 0,
                    'impressions': 0,
                    'engagement_rate': None,
                    'link_clicks': 0,
                })
        
        return Response({
            'post_id': str(post.id),
            'post_title': post.title,
            'performances': performances
        })
    
    def post(self, request, post_id):
        """Fetch and update performance metrics for a post"""
        post = get_object_or_404(Post, id=post_id, user=request.user)
        
        # Get platform_post_id from request (optional, if not provided, update all)
        platform_post_id = request.data.get('platform_post_id')
        
        if platform_post_id:
            platform_posts = PostPlatform.objects.filter(
                post=post,
                id=platform_post_id,
                status='published'
            )
        else:
            platform_posts = PostPlatform.objects.filter(
                post=post,
                status='published'
            )
        
        if not platform_posts.exists():
            return Response({
                'error': 'No published platform posts found for this post'
            }, status=status.HTTP_404_NOT_FOUND)
        
        updated_count = 0
        errors = []
        
        for platform_post in platform_posts:
            try:
                # Get access token
                access_token = platform_post.social_account.get_access_token()
                
                # Initialize analytics service
                analytics_service = PostAnalyticsService(access_token)
                
                # Update performance
                performance = analytics_service.update_post_performance(platform_post)
                
                if performance:
                    updated_count += 1
                else:
                    errors.append(f"Failed to update metrics for {platform_post.social_account.platform}")
                    
            except Exception as e:
                logger.error(f"Error updating performance for platform_post {platform_post.id}: {e}")
                errors.append(f"Error updating {platform_post.social_account.platform}: {str(e)}")
        
        return Response({
            'message': f'Updated metrics for {updated_count} platform(s)',
            'updated_count': updated_count,
            'errors': errors if errors else None
        })


class PostPerformanceListView(APIView):
    """List all post performances for user's posts"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get all post performances for user's posts"""
        # Get all published platform posts for user's posts
        platform_posts = PostPlatform.objects.filter(
            post__user=request.user,
            status='published'
        )
        
        # Get performances
        performances = PostPerformance.objects.filter(
            post_platform__in=platform_posts
        ).select_related('post_platform__post', 'post_platform__social_account')
        
        serializer = PostPerformanceSerializer(performances, many=True)
        
        # Calculate summary statistics
        total_likes = sum(p.likes for p in performances)
        total_comments = sum(p.comments for p in performances)
        total_shares = sum(p.shares for p in performances)
        total_reach = sum(p.reach for p in performances)
        total_impressions = sum(p.impressions for p in performances)
        
        avg_engagement_rate = None
        if performances.exists():
            engagement_rates = [p.engagement_rate for p in performances if p.engagement_rate]
            if engagement_rates:
                avg_engagement_rate = sum(engagement_rates) / len(engagement_rates)
        
        return Response({
            'performances': serializer.data,
            'summary': {
                'total_posts': performances.count(),
                'total_likes': total_likes,
                'total_comments': total_comments,
                'total_shares': total_shares,
                'total_reach': total_reach,
                'total_impressions': total_impressions,
                'average_engagement_rate': round(avg_engagement_rate, 2) if avg_engagement_rate else None
            }
        })
