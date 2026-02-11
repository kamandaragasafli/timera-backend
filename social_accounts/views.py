from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from django.shortcuts import redirect, get_object_or_404
from django.utils import timezone
from datetime import timedelta
import requests
import secrets
import json
import base64
from .models import SocialAccount
from .serializers import SocialAccountSerializer


class SocialAccountListView(generics.ListAPIView):
    """List all connected social accounts for the current user"""
    
    serializer_class = SocialAccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return SocialAccount.objects.filter(user=self.request.user)


class GetOAuthUrlView(APIView):
    """Generate OAuth URL for social media platform"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, platform):
        # Encode user ID and random token in state (no session needed for cross-origin)
        random_token = secrets.token_urlsafe(16)
        state_data = {
            'user_id': str(request.user.id),
            'email': request.user.email,
            'token': random_token,
            'platform': platform
        }
        # Base64 encode the state data
        state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
        
        if platform in ['facebook', 'instagram']:
            # Meta (Facebook/Instagram) OAuth
            app_id = settings.META_APP_ID
            
            # Check if Meta credentials are configured
            if not app_id:
                return Response({
                    'error': f'{platform.capitalize()} integration not configured',
                    'details': 'META_APP_ID is missing in server configuration. Please contact administrator.'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            # Callback goes to backend, not frontend
            backend_url = settings.BACKEND_URL
            redirect_uri = f"{backend_url}/api/social-accounts/callback/{platform}/"
            
            # Request ALL Meta Business Suite permissions for App Review
            # Facebook Pages:
            # - pages_show_list: List Facebook Pages user manages
            # - pages_manage_posts: Publish posts to Facebook Pages
            # - pages_read_engagement: Read Page engagement insights and post statistics
            # Instagram:
            # - instagram_basic: Access Instagram Business Account info
            # - instagram_content_publish: Publish posts to Instagram
            # - instagram_manage_messages: Read Instagram Direct messages
            # - instagram_business_manage_messages: Send messages from Instagram Business Account
            # Business:
            # - business_management: Access Business Manager accounts
            # Ads:
            # - ads_read: Read ad accounts, campaigns, and insights
            # - ads_management: Create and manage ad campaigns
            # Additional:
            # - pages_messaging: Read and send messages from Page inbox (for completeness)
            # - read_insights: Read Page and Instagram analytics (legacy, kept for compatibility)
            
            # Minimal permissions for profile connection and posting
            # Required for basic functionality:
            # - pages_show_list: List Facebook Pages user manages
            # - pages_manage_posts: Publish posts to Facebook Pages
            # - instagram_basic: Access Instagram Business Account info
            # - instagram_content_publish: Publish posts to Instagram
            # Optional but useful:
            # - pages_read_engagement: Read Page engagement stats (useful for analytics)
            # - read_insights: Read Page and Instagram analytics (useful for analytics)
            # - business_management: Access Business Manager accounts (often needed for Instagram)
            permissions_str = (
                'pages_show_list,'  # List pages (REQUIRED)
                'pages_manage_posts,'  # Publish to Facebook (REQUIRED)
                'pages_read_engagement,'  # Page engagement stats (OPTIONAL but useful)
                'pages_messaging,'  # Facebook Pages messaging (REQUIRED for messages)
                'instagram_basic,'  # Instagram account info (REQUIRED)
                'instagram_content_publish,'  # Publish to Instagram (REQUIRED)
                'instagram_manage_messages,'  # Instagram Direct messages (REQUIRED for messages)
                'business_management,'  # Business accounts (OPTIONAL but often needed)
                'read_insights'  # Analytics (OPTIONAL but useful)
            )
            
            auth_url = (
                f"https://www.facebook.com/v18.0/dialog/oauth?"
                f"client_id={app_id}&"
                f"redirect_uri={redirect_uri}&"
                f"state={state}&"
                f"scope={permissions_str}&"
                f"response_type=code"
            )
            
            return Response({
                'auth_url': auth_url,
                'state': state
            })
        
        elif platform == 'linkedin':
            # LinkedIn OAuth 2.0
            client_id = settings.LINKEDIN_CLIENT_ID
            
            # Check if LinkedIn credentials are configured
            if not client_id:
                return Response({
                    'error': 'LinkedIn integration not configured',
                    'details': 'LINKEDIN_CLIENT_ID is missing in server configuration. Please contact administrator.'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            backend_url = settings.BACKEND_URL
            redirect_uri = f"{backend_url}/api/social-accounts/callback/{platform}/"
            
            # Required scopes: 
            # - openid, profile, email: for user info
            # - w_member_social: for personal account posting
            # Note: w_organization_social requires LinkedIn approval - temporarily removed
            # To enable Company Page posting, request this scope from LinkedIn Partner Program
            scopes = 'openid profile email w_member_social'
            
            auth_url = (
                f"https://www.linkedin.com/oauth/v2/authorization?"
                f"response_type=code&"
                f"client_id={client_id}&"
                f"redirect_uri={redirect_uri}&"
                f"state={state}&"
                f"scope={scopes}"
            )
            
            return Response({
                'auth_url': auth_url,
                'state': state
            })
        
        elif platform == 'youtube':
            # YouTube OAuth 2.0
            # TODO: Add YouTube OAuth configuration
            client_id = getattr(settings, 'YOUTUBE_CLIENT_ID', None)
            
            if not client_id:
                return Response({
                    'error': 'YouTube integration not configured',
                    'details': 'YOUTUBE_CLIENT_ID is missing in server configuration. Please contact administrator.'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            redirect_uri = f"{backend_url}/api/social-accounts/callback/{platform}/"
            scopes = 'https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly'
            
            auth_url = (
                f"https://accounts.google.com/o/oauth2/v2/auth?"
                f"client_id={client_id}&"
                f"redirect_uri={redirect_uri}&"
                f"response_type=code&"
                f"scope={scopes}&"
                f"access_type=offline&"
                f"prompt=consent&"
                f"state={state}"
            )
            
            return Response({
                'auth_url': auth_url,
                'state': state
            })
        
        elif platform == 'tiktok':
            # TikTok OAuth 2.0
            # TODO: Add TikTok OAuth configuration
            client_key = getattr(settings, 'TIKTOK_CLIENT_KEY', None)
            
            if not client_key:
                return Response({
                    'error': 'TikTok integration not configured',
                    'details': 'TIKTOK_CLIENT_KEY is missing in server configuration. Please contact administrator.'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            redirect_uri = f"{backend_url}/api/social-accounts/callback/{platform}/"
            scopes = 'user.info.basic,video.upload,video.publish'
            
            auth_url = (
                f"https://www.tiktok.com/v2/auth/authorize/"
                f"?client_key={client_key}&"
                f"redirect_uri={redirect_uri}&"
                f"response_type=code&"
                f"scope={scopes}&"
                f"state={state}"
            )
            
            return Response({
                'auth_url': auth_url,
                'state': state
            })
        
        return Response({
            'error': 'Platform not supported'
        }, status=status.HTTP_400_BAD_REQUEST)


class OAuthCallbackView(APIView):
    """Handle OAuth callback from social media platforms"""
    
    permission_classes = []  # No authentication required for callback
    
    def get(self, request, platform):
        code = request.GET.get('code')
        state = request.GET.get('state')
        error = request.GET.get('error')
        
        # Check for errors
        if error:
            return redirect(f"{settings.FRONTEND_URL}/social-accounts?error={error}")
        
        if not code:
            return redirect(f"{settings.FRONTEND_URL}/social-accounts?error=no_code")
        
        # Decode state token to get user_id and other info
        try:
            state_json = base64.urlsafe_b64decode(state.encode()).decode()
            state_data = json.loads(state_json)
            user_id = state_data.get('user_id')
            state_platform = state_data.get('platform')
            
            # Verify platform matches
            if state_platform != platform:
                return redirect(f"{settings.FRONTEND_URL}/social-accounts?error=invalid_platform")
            
            if not user_id:
                return redirect(f"{settings.FRONTEND_URL}/social-accounts?error=invalid_state")
                
        except Exception as e:
            print(f"State decode error: {str(e)}")
            return redirect(f"{settings.FRONTEND_URL}/social-accounts?error=invalid_state")
        
        try:
            if platform in ['facebook', 'instagram']:
                self._handle_meta_callback(request, platform, code, user_id, state_data)
            elif platform == 'linkedin':
                self._handle_linkedin_callback(request, platform, code, user_id, state_data)
            elif platform == 'youtube':
                self._handle_youtube_callback(request, platform, code, user_id, state_data)
            elif platform == 'tiktok':
                self._handle_tiktok_callback(request, platform, code, user_id, state_data)
            else:
                return redirect(f"{settings.FRONTEND_URL}/social-accounts?error=unsupported_platform")
            
            return redirect(f"{settings.FRONTEND_URL}/social-accounts?success=true")
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            error_msg = str(e)
            logger.error(f"OAuth callback error for {platform}: {error_msg}", exc_info=True)
            print(f"OAuth callback error: {error_msg}")
            import traceback
            traceback.print_exc()
            
            # More detailed error message
            error_details = error_msg[:100]  # Allow longer error message
            # URL encode the error details
            import urllib.parse
            error_details_encoded = urllib.parse.quote(error_details)
            return redirect(f"{settings.FRONTEND_URL}/social-accounts?error=callback_failed&details={error_details_encoded}")
    
    def _handle_meta_callback(self, request, platform, code, user_id, state_data=None):
        """Handle Facebook/Instagram OAuth callback"""
        
        # Exchange code for access token
        token_url = "https://graph.facebook.com/v18.0/oauth/access_token"
        # Use backend URL for redirect_uri (must match the one used in auth request)
        backend_url = settings.BACKEND_URL
        redirect_uri = f"{backend_url}/api/social-accounts/callback/{platform}/"
        
        token_response = requests.post(token_url, data={
            'client_id': settings.META_APP_ID,
            'client_secret': settings.META_APP_SECRET,
            'redirect_uri': redirect_uri,
            'code': code
        })
        
        token_data = token_response.json()
        
        if 'error' in token_data:
            raise Exception(f"Token exchange failed: {token_data.get('error_description')}")
        
        access_token = token_data['access_token']
        
        # Get long-lived token
        long_lived_response = requests.get(
            "https://graph.facebook.com/v18.0/oauth/access_token",
            params={
                'grant_type': 'fb_exchange_token',
                'client_id': settings.META_APP_ID,
                'client_secret': settings.META_APP_SECRET,
                'fb_exchange_token': access_token
            }
        )
        
        long_lived_data = long_lived_response.json()
        long_lived_token = long_lived_data.get('access_token', access_token)
        expires_in = long_lived_data.get('expires_in', 5184000)  # 60 days default
        
        # Get user from user_id decoded from state token
        from accounts.models import User
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            # Fallback: try to get user by email from state (for safety if IDs changed)
            email = None
            if state_data and isinstance(state_data, dict):
                email = state_data.get('email')
            if email:
                user = User.objects.filter(email=email).first()
            else:
                user = None
            
            if not user:
                raise Exception("User matching query does not exist")
        
        # Get Facebook user info
        me_response = requests.get(
            "https://graph.facebook.com/v18.0/me",
            params={
                'access_token': long_lived_token,
                'fields': 'id,name,email,picture'
            }
        )
        
        me_data = me_response.json()
        
        if platform == 'facebook':
            # Get Facebook Pages that user manages
            # First, check which permissions we actually have
            perms_response = requests.get(
                "https://graph.facebook.com/v18.0/me/permissions",
                params={'access_token': long_lived_token}
            )
            perms_data = perms_response.json()
            print(f"🔑 Granted permissions: {perms_data}")
            
            pages_response = requests.get(
                "https://graph.facebook.com/v18.0/me/accounts",
                params={'access_token': long_lived_token}
            )
            
            pages_data = pages_response.json()
            print(f"📄 Pages API response: {pages_data}")
            print(f"📄 Status code: {pages_response.status_code}")
            print(f"📄 Full response: {pages_response.text}")
            
            # Also try to get user info to see what account this is
            print(f"👤 User info: {me_data}")
            
            if pages_data.get('data'):
                print(f"✅ Found {len(pages_data['data'])} pages")
                # Store the first page (or you can let user choose later)
                for page in pages_data['data']:
                    page_id = page['id']
                    page_token = page['access_token']
                    page_name = page['name']
                    
                    # Get page picture
                    page_pic_response = requests.get(
                        f"https://graph.facebook.com/v18.0/{page_id}/picture",
                        params={
                            'access_token': page_token,
                            'redirect': '0',
                            'type': 'large'
                        }
                    )
                    page_pic_data = page_pic_response.json()
                    
                    # Store Facebook Page
                    print(f"💾 Saving page: {page_name} (ID: {page_id})")
                    
                    # Safely truncate all fields to prevent DB errors
                    safe_page_name = (page_name or '')[:100]  # Max 100 for platform_username
                    safe_display_name = (page_name or '')[:200]  # Max 200 for display_name
                    pic_url = page_pic_data.get('data', {}).get('url', '') if page_pic_data.get('data') else ''
                    safe_pic_url = pic_url[:500] if pic_url else ''  # Max 500 for profile_picture_url (DB limit)
                    
                    # Truncate settings fields too - be very conservative
                    # Use minimal settings to avoid any JSON serialization issues
                    page_category = (page.get('category', '') or '')[:50]  # Very short to be safe
                    page_tasks = page.get('tasks', [])
                    if isinstance(page_tasks, list):
                        # Limit tasks list size and truncate each task string
                        page_tasks = [str(task)[:50] for task in page_tasks[:5]]  # Max 5 tasks, each max 50 chars
                    else:
                        page_tasks = []
                    
                    # Build minimal settings dict
                    settings_dict = {}
                    if page_category:
                        settings_dict['page_category'] = page_category
                    if page_tasks:
                        settings_dict['page_tasks'] = page_tasks
                    
                    try:
                        account, created = SocialAccount.objects.update_or_create(
                            user=user,
                            platform='facebook',
                            platform_user_id=str(page_id)[:100],  # Ensure page_id is string and not too long
                            defaults={
                                'platform_username': safe_page_name[:100] if safe_page_name else '',
                                'display_name': safe_display_name[:200] if safe_display_name else '',
                                'profile_picture_url': safe_pic_url[:500] if safe_pic_url else '',
                                'is_active': True,
                                'expires_at': timezone.now() + timedelta(seconds=expires_in),
                                'settings': settings_dict  # Minimal settings
                            }
                        )
                        # Save account first
                        account.save()
                        print(f"✅ Account object saved: {account.id} (created={created})")
                        
                        # Then set access token (this encrypts and saves)
                        try:
                            account.set_access_token(page_token)
                            account.save()
                            print(f"✅ Access token saved successfully")
                        except Exception as token_error:
                            print(f"⚠️ Warning: Could not save access token: {str(token_error)}")
                            # Account is saved, token can be set later
                        
                        print(f"✅ Saved account: {account.id} (created={created})")
                    except Exception as save_error:
                        error_str = str(save_error)
                        print(f"❌ Error saving account: {error_str}")
                        print(f"❌ Error type: {type(save_error).__name__}")
                        import traceback
                        traceback.print_exc()
                        
                        # Try with even shorter values and minimal data
                        try:
                            print(f"🔄 Retrying with minimal data...")
                            account, created = SocialAccount.objects.update_or_create(
                                user=user,
                                platform='facebook',
                                platform_user_id=str(page_id)[:50],  # Very short
                                defaults={
                                    'platform_username': safe_page_name[:50] if safe_page_name else 'Facebook Page',
                                    'display_name': safe_display_name[:100] if safe_display_name else 'Facebook Page',
                                    'profile_picture_url': '',  # Empty to avoid any issues
                                    'is_active': True,
                                    'expires_at': timezone.now() + timedelta(seconds=expires_in),
                                    'settings': {}  # Empty settings to avoid any issues
                                }
                            )
                            account.save()
                            print(f"✅ Account saved with minimal data: {account.id}")
                            
                            # Try to set token separately
                            try:
                                account.set_access_token(page_token)
                                account.save()
                                print(f"✅ Token saved on retry")
                            except Exception as token_error2:
                                print(f"⚠️ Token save failed on retry: {str(token_error2)}")
                            
                            print(f"✅ Saved account with shorter fields: {account.id} (created={created})")
                        except Exception as retry_error:
                            print(f"❌ Retry also failed: {str(retry_error)}")
                            import traceback
                            traceback.print_exc()
                            raise retry_error
                    break  # Use first page found
            else:
                print(f"❌ No pages found in response")
                print(f"📝 This is likely due to Development Mode restrictions")
                print(f"💡 Solution: Switch app to Live Mode or add Pages as Test Pages")
                # As fallback, we could store personal profile, but that won't allow posting
                # For now, let's show helpful error
                raise Exception("No Facebook Pages found. Please ensure: 1) Your app is in Live Mode, OR 2) Your Pages are added as Test Pages in App Settings > Roles")
            
        elif platform == 'instagram':
            # Get Facebook pages
            print(f"📸 Instagram: Fetching pages...")
            pages_response = requests.get(
                "https://graph.facebook.com/v18.0/me/accounts",
                params={'access_token': long_lived_token}
            )
            
            pages_data = pages_response.json()
            print(f"📸 Instagram: Found {len(pages_data.get('data', []))} pages")
            
            if pages_data.get('data'):
                # Get Instagram Business Account connected to first page
                for page in pages_data['data']:
                    page_id = page['id']
                    page_token = page['access_token']
                    page_name = page['name']
                    print(f"📸 Instagram: Checking page '{page_name}' (ID: {page_id})")
                    
                    # Get Instagram account connected to this page
                    ig_response = requests.get(
                        f"https://graph.facebook.com/v18.0/{page_id}",
                        params={
                            'access_token': page_token,
                            'fields': 'instagram_business_account'
                        }
                    )
                    
                    ig_data = ig_response.json()
                    print(f"📸 Instagram: Page response: {ig_data}")
                    
                    if 'instagram_business_account' in ig_data:
                        ig_account_id = ig_data['instagram_business_account']['id']
                        print(f"📸 Instagram: Found Instagram account ID: {ig_account_id}")
                        
                        # Get Instagram account info
                        ig_info_response = requests.get(
                            f"https://graph.facebook.com/v18.0/{ig_account_id}",
                            params={
                                'access_token': page_token,
                                'fields': 'id,username,name,profile_picture_url'
                            }
                        )
                        
                        ig_info = ig_info_response.json()
                        print(f"📸 Instagram: Account info: {ig_info}")
                        
                        # Store Instagram account
                        print(f"💾 Saving Instagram account: @{ig_info.get('username', 'unknown')}")
                        
                        # Safely truncate all fields to prevent DB errors
                        safe_username = (ig_info.get('username', '') or '')[:100]  # Max 100
                        safe_name = (ig_info.get('name', '') or '')[:200]  # Max 200
                        safe_pic_url = (ig_info.get('profile_picture_url', '') or '')[:500]  # Max 500
                        safe_page_id = (page_id or '')[:100]  # Max 100
                        safe_page_name = (page['name'] or '')[:100]  # Max 100 for settings
                        
                        try:
                            account, created = SocialAccount.objects.update_or_create(
                                user=user,
                                platform='instagram',
                                platform_user_id=ig_account_id[:100],  # Ensure not too long
                                defaults={
                                    'platform_username': safe_username,
                                    'display_name': safe_name,
                                    'profile_picture_url': safe_pic_url,
                                    'is_active': True,
                                    'expires_at': timezone.now() + timedelta(seconds=expires_in),
                                    'settings': {
                                        'page_id': safe_page_id,
                                        'page_name': safe_page_name,
                                        'ig_account_id': ig_account_id[:100]  # ✅ Instagram Account ID
                                    }
                                }
                            )
                            account.set_access_token(page_token)
                            account.save()
                            print(f"✅ Saved Instagram account: {account.id} (created={created})")
                        except Exception as save_error:
                            print(f"❌ Error saving Instagram account: {str(save_error)}")
                            # Try with even shorter values
                            try:
                                account, created = SocialAccount.objects.update_or_create(
                                    user=user,
                                    platform='instagram',
                                    platform_user_id=ig_account_id[:100],
                                    defaults={
                                        'platform_username': safe_username[:50],  # Even shorter
                                        'display_name': safe_name[:100],  # Even shorter
                                        'profile_picture_url': safe_pic_url[:400],  # Even shorter
                                        'is_active': True,
                                        'expires_at': timezone.now() + timedelta(seconds=expires_in),
                                        'settings': {}  # Empty settings to avoid any issues
                                    }
                                )
                                account.set_access_token(page_token)
                                account.save()
                                print(f"✅ Saved Instagram account with shorter fields: {account.id} (created={created})")
                            except Exception as retry_error:
                                print(f"❌ Retry also failed: {str(retry_error)}")
                                raise retry_error
                        break  # Use first Instagram account found
                    else:
                        print(f"❌ No Instagram account linked to page '{page_name}'")
    
    def _handle_linkedin_callback(self, request, platform, code, user_id, state_data=None):
        """Handle LinkedIn OAuth callback"""
        
        # Exchange code for access token
        token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        backend_url = settings.BACKEND_URL
        redirect_uri = f"{backend_url}/api/social-accounts/callback/{platform}/"
        
        token_response = requests.post(token_url, data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': settings.LINKEDIN_CLIENT_ID,
            'client_secret': settings.LINKEDIN_CLIENT_SECRET,
        })
        
        token_data = token_response.json()
        
        if 'error' in token_data:
            raise Exception(f"Token exchange failed: {token_data.get('error_description', token_data.get('error'))}")
        
        access_token = token_data['access_token']
        expires_in = token_data.get('expires_in', 5184000)  # Default 60 days
        
        # Get user from user_id decoded from state token
        from accounts.models import User
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            email = None
            if state_data and isinstance(state_data, dict):
                email = state_data.get('email')
            if email:
                user = User.objects.filter(email=email).first()
            else:
                user = None
            if not user:
                raise Exception("User matching query does not exist")
        
        # Get LinkedIn user info using OpenID Connect userinfo endpoint
        userinfo_response = requests.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={
                'Authorization': f'Bearer {access_token}',
            }
        )
        
        userinfo_data = userinfo_response.json()
        print(f"👤 LinkedIn user info: {userinfo_data}")
        
        if 'error' in userinfo_data:
            raise Exception(f"Failed to get user info: {userinfo_data.get('error_description', userinfo_data.get('error'))}")
        
        # Extract user information
        linkedin_user_id = userinfo_data.get('sub')  # 'sub' is the user ID in OpenID Connect
        name = userinfo_data.get('name', '')
        email = userinfo_data.get('email', '')
        picture = userinfo_data.get('picture', '')
        
        # Store LinkedIn account
        print(f"💾 Saving LinkedIn account: {name} ({email})")
        account, created = SocialAccount.objects.update_or_create(
            user=user,
            platform='linkedin',
            platform_user_id=linkedin_user_id,
            defaults={
                'platform_username': (email or '')[:100],  # Truncate to 100 chars
                'display_name': (name or '')[:200],  # Truncate to 200 chars
                'profile_picture_url': (picture or '')[:500] if picture else '',  # Truncate to 500 chars (DB limit)
                'is_active': True,
                'expires_at': timezone.now() + timedelta(seconds=expires_in),
                'settings': {
                    'email': email,
                }
            }
        )
        account.set_access_token(access_token)
        account.save()
        print(f"✅ Saved LinkedIn account: {account.id} (created={created})")
        
        # NOTE: Company Page support requires w_organization_social scope
        # This scope needs approval from LinkedIn Partner Program
        # For now, only personal account posting is supported
        # To enable Company Pages:
        # 1. Apply for LinkedIn Partner Program
        # 2. Request w_organization_social scope approval
        # 3. Once approved, uncomment the code below
    
    def _handle_youtube_callback(self, request, platform, code, user_id, state_data=None):
        """Handle YouTube OAuth callback"""
        from accounts.models import User
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            email = None
            if state_data and isinstance(state_data, dict):
                email = state_data.get('email')
            if email:
                user = User.objects.filter(email=email).first()
            else:
                user = None
            if not user:
                raise Exception("User matching query does not exist")
        
        backend_url = settings.BACKEND_URL
        redirect_uri = f"{backend_url}/api/social-accounts/callback/{platform}/"
        
        client_id = getattr(settings, 'YOUTUBE_CLIENT_ID', None)
        client_secret = getattr(settings, 'YOUTUBE_CLIENT_SECRET', None)
        
        if not client_id or not client_secret:
            raise Exception("YouTube OAuth credentials not configured")
        
        # Exchange code for access token
        token_url = "https://oauth2.googleapis.com/token"
        token_response = requests.post(token_url, data={
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri
        })
        
        token_data = token_response.json()
        
        if 'error' in token_data:
            raise Exception(f"Token exchange failed: {token_data.get('error_description', token_data.get('error'))}")
        
        access_token = token_data['access_token']
        refresh_token = token_data.get('refresh_token')
        expires_in = token_data.get('expires_in', 3600)
        
        # Get YouTube channel info
        channel_response = requests.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={
                'part': 'snippet,contentDetails',
                'mine': 'true',
                'access_token': access_token
            }
        )
        
        channel_data = channel_response.json()
        
        if 'error' in channel_data or not channel_data.get('items'):
            raise Exception("Failed to get YouTube channel info")
        
        channel = channel_data['items'][0]
        channel_id = channel['id']
        channel_info = channel['snippet']
        
        # Store YouTube account
        account, created = SocialAccount.objects.update_or_create(
            user=user,
            platform='youtube',
            platform_user_id=channel_id,
            defaults={
                'platform_username': (channel_info.get('customUrl', channel_info.get('title', '')) or '')[:100],  # Truncate to 100 chars
                'display_name': (channel_info.get('title', '') or '')[:200],  # Truncate to 200 chars
                'profile_picture_url': (channel_info.get('thumbnails', {}).get('default', {}).get('url', '') or '')[:500] if channel_info.get('thumbnails', {}).get('default', {}).get('url') else '',  # Truncate to 500 chars (DB limit)
                'is_active': True,
                'expires_at': timezone.now() + timedelta(seconds=expires_in),
                'settings': {
                    'channel_id': channel_id,
                }
            }
        )
        account.set_access_token(access_token)
        if refresh_token:
            account.set_refresh_token(refresh_token)
        account.save()
        print(f"✅ Saved YouTube account: {account.id} (created={created})")
    
    def _handle_tiktok_callback(self, request, platform, code, user_id, state_data=None):
        """Handle TikTok OAuth callback"""
        from accounts.models import User
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            email = None
            if state_data and isinstance(state_data, dict):
                email = state_data.get('email')
            if email:
                user = User.objects.filter(email=email).first()
            else:
                user = None
            if not user:
                raise Exception("User matching query does not exist")
        
        backend_url = settings.BACKEND_URL
        redirect_uri = f"{backend_url}/api/social-accounts/callback/{platform}/"
        
        client_key = getattr(settings, 'TIKTOK_CLIENT_KEY', None)
        client_secret = getattr(settings, 'TIKTOK_CLIENT_SECRET', None)
        
        if not client_key or not client_secret:
            raise Exception("TikTok OAuth credentials not configured")
        
        # Exchange code for access token
        token_url = "https://open.tiktokapis.com/v2/oauth/token/"
        token_response = requests.post(token_url, data={
            'client_key': client_key,
            'client_secret': client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri
        })
        
        token_data = token_response.json()
        
        if 'error' in token_data or token_data.get('data', {}).get('error'):
            error_info = token_data.get('data', {}).get('error', {}) if token_data.get('data') else token_data.get('error', {})
            raise Exception(f"Token exchange failed: {error_info.get('description', error_info.get('message', 'Unknown error'))}")
        
        access_token = token_data.get('data', {}).get('access_token')
        refresh_token = token_data.get('data', {}).get('refresh_token')
        expires_in = token_data.get('data', {}).get('expires_in', 7200)
        
        if not access_token:
            raise Exception("No access token received from TikTok")
        
        # Get TikTok user info
        user_info_response = requests.get(
            "https://open.tiktokapis.com/v2/user/info/",
            params={
                'fields': 'open_id,union_id,avatar_url,display_name,username'
            },
            headers={
                'Authorization': f'Bearer {access_token}'
            }
        )
        
        user_info_data = user_info_response.json()
        
        if 'error' in user_info_data or user_info_data.get('data', {}).get('error'):
            error_info = user_info_data.get('data', {}).get('error', {}) if user_info_data.get('data') else user_info_data.get('error', {})
            raise Exception(f"Failed to get user info: {error_info.get('description', error_info.get('message', 'Unknown error'))}")
        
        user_info = user_info_data.get('data', {}).get('user', {})
        open_id = user_info.get('open_id')
        username = user_info.get('username', '')
        display_name = user_info.get('display_name', username)
        avatar_url = user_info.get('avatar_url', '')
        
        # Store TikTok account
        account, created = SocialAccount.objects.update_or_create(
            user=user,
            platform='tiktok',
            platform_user_id=open_id,
            defaults={
                'platform_username': (username or '')[:100],  # Truncate to 100 chars
                'display_name': (display_name or '')[:200],  # Truncate to 200 chars
                'profile_picture_url': (avatar_url or '')[:500] if avatar_url else '',  # Truncate to 500 chars (DB limit)
                'is_active': True,
                'expires_at': timezone.now() + timedelta(seconds=expires_in),
                'settings': {
                    'open_id': open_id,
                    'union_id': user_info.get('union_id', ''),
                }
            }
        )
        account.set_access_token(access_token)
        if refresh_token:
            account.set_refresh_token(refresh_token)
        account.save()
        print(f"✅ Saved TikTok account: {account.id} (created={created})")


class TestPermissionsView(APIView):
    """Test API calls for permissions that require advanced access"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        """Test permissions by making API calls"""
        import requests
        from django.utils import timezone
        
        account = get_object_or_404(SocialAccount, pk=pk, user=request.user)
        
        if account.platform not in ['facebook', 'instagram']:
            return Response({
                'error': 'This endpoint is only for Facebook/Instagram accounts'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        access_token = account.get_access_token()
        if not access_token:
            return Response({
                'error': 'No access token found'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        results = {}
        page_id = account.settings.get('page_id') or account.platform_user_id
        
        # Test pages_messaging permission
        try:
            # Get conversations (messages)
            messages_response = requests.get(
                f"https://graph.facebook.com/v18.0/{page_id}/conversations",
                params={
                    'access_token': access_token,
                    'limit': 1,
                    'fields': 'id,message_count'
                }
            )
            results['pages_messaging'] = {
                'status': messages_response.status_code,
                'success': messages_response.status_code == 200,
                'data': messages_response.json() if messages_response.status_code == 200 else messages_response.text[:200]
            }
        except Exception as e:
            results['pages_messaging'] = {
                'status': 'error',
                'success': False,
                'error': str(e)[:200]
            }
        
        # Test read_insights permission
        try:
            # Get page insights
            insights_response = requests.get(
                f"https://graph.facebook.com/v18.0/{page_id}/insights",
                params={
                    'access_token': access_token,
                    'metric': 'page_fans,page_impressions',
                    'period': 'day',
                    'since': int((timezone.now() - timezone.timedelta(days=7)).timestamp()),
                    'until': int(timezone.now().timestamp())
                }
            )
            results['read_insights'] = {
                'status': insights_response.status_code,
                'success': insights_response.status_code == 200,
                'data': insights_response.json() if insights_response.status_code == 200 else insights_response.text[:200]
            }
        except Exception as e:
            results['read_insights'] = {
                'status': 'error',
                'success': False,
                'error': str(e)[:200]
            }
        
        # Test pages_manage_posts permission (if needed)
        try:
            # Just check permissions (this doesn't require posting)
            perms_response = requests.get(
                "https://graph.facebook.com/v18.0/me/permissions",
                params={'access_token': access_token}
            )
            results['permissions_check'] = {
                'status': perms_response.status_code,
                'success': perms_response.status_code == 200,
                'data': perms_response.json() if perms_response.status_code == 200 else None
            }
        except Exception as e:
            results['permissions_check'] = {
                'status': 'error',
                'success': False,
                'error': str(e)[:200]
            }
        
        return Response({
            'message': 'Test API calls completed',
            'results': results,
            'note': 'Meta will track these API calls. Check App Review in 24 hours to see if "Request" button becomes active.'
        })


class DisconnectAccountView(generics.DestroyAPIView):
    """Disconnect a social account"""
    
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SocialAccountSerializer
    
    def get_queryset(self):
        return SocialAccount.objects.filter(user=self.request.user)
    
    def perform_destroy(self, instance):
        instance.delete()
