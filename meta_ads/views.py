"""
Meta Ads API Views
Simplified implementation for structure demo
"""

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
import logging

from .models import MetaAdAccount, MetaCampaign, MetaAdSet, MetaAd, MetaInsight
from .serializers import (
    MetaAdAccountSerializer, MetaCampaignSerializer, MetaAdSetSerializer,
    MetaAdSerializer, MetaInsightSerializer, CampaignCreateSerializer,
    InsightsRequestSerializer
)
from .services import MetaAPIService

logger = logging.getLogger(__name__)


# ============================================================================
# AD ACCOUNTS
# ============================================================================

class AdAccountListView(generics.ListAPIView):
    """List user's Meta ad accounts"""
    
    serializer_class = MetaAdAccountSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return MetaAdAccount.objects.filter(user=self.request.user, is_active=True)


class AdAccountDetailView(generics.RetrieveAPIView):
    """Get single ad account details"""
    
    serializer_class = MetaAdAccountSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'account_id'
    
    def get_queryset(self):
        return MetaAdAccount.objects.filter(user=self.request.user)


class ConnectAdAccountView(APIView):
    """Get OAuth URL to connect Meta Ad Account"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Generate OAuth URL for Meta Ads"""
        from django.conf import settings
        import secrets
        import base64
        import json
        
        app_id = settings.META_APP_ID
        
        if not app_id:
            return Response({
                'error': 'Meta Ads integration not configured',
                'details': 'META_APP_ID is missing in server configuration.'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Generate state with user ID
        random_token = secrets.token_urlsafe(16)
        state_data = {
            'user_id': str(request.user.id),
            'token': random_token,
            'type': 'meta_ads'
        }
        state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
        
        # Meta Ads requires specific permissions
        backend_url = settings.BACKEND_URL
        redirect_uri = f"{backend_url}/api/meta-ads/callback/"
        
        # Required scopes for Meta Ads API
        # ads_management, ads_read: for managing and reading ads
        # business_management: for managing business accounts
        # read_insights: for reading analytics and insights (optional but recommended)
        scopes = 'ads_management,ads_read,business_management,read_insights'
        
        auth_url = (
            f"https://www.facebook.com/v18.0/dialog/oauth?"
            f"client_id={app_id}&"
            f"redirect_uri={redirect_uri}&"
            f"state={state}&"
            f"scope={scopes}&"
            f"response_type=code"
        )
        
        return Response({
            'auth_url': auth_url,
            'state': state
        })


class AdAccountCallbackView(APIView):
    """Handle OAuth callback for Meta Ad Account"""
    
    permission_classes = []  # No auth required for callback
    
    def get(self, request):
        """Handle OAuth callback"""
        from django.conf import settings
        from django.shortcuts import redirect
        import base64
        import json
        import requests
        
        code = request.GET.get('code')
        state = request.GET.get('state')
        error = request.GET.get('error')
        
        if error:
            return redirect(f"{settings.FRONTEND_URL}/meta-ads?error={error}")
        
        if not code:
            return redirect(f"{settings.FRONTEND_URL}/meta-ads?error=no_code")
        
        # Decode state
        try:
            state_json = base64.urlsafe_b64decode(state.encode()).decode()
            state_data = json.loads(state_json)
            user_id = state_data.get('user_id')
            
            if not user_id:
                return redirect(f"{settings.FRONTEND_URL}/meta-ads?error=invalid_state")
                
        except Exception as e:
            logger.error(f"State decode error: {e}")
            return redirect(f"{settings.FRONTEND_URL}/meta-ads?error=invalid_state")
        
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return redirect(f"{settings.FRONTEND_URL}/meta-ads?error=user_not_found")
        
        # Exchange code for access token
        app_id = settings.META_APP_ID
        app_secret = settings.META_APP_SECRET
        backend_url = settings.BACKEND_URL
        redirect_uri = f"{backend_url}/api/meta-ads/callback/"
        
        token_url = "https://graph.facebook.com/v18.0/oauth/access_token"
        token_params = {
            'client_id': app_id,
            'client_secret': app_secret,
            'redirect_uri': redirect_uri,
            'code': code
        }
        
        try:
            token_response = requests.get(token_url, params=token_params)
            token_response.raise_for_status()
            token_data = token_response.json()
            access_token = token_data.get('access_token')
            
            if not access_token:
                return redirect(f"{settings.FRONTEND_URL}/meta-ads?error=no_token")
            
            # Get long-lived token (60 days)
            long_token_url = "https://graph.facebook.com/v18.0/oauth/access_token"
            long_token_params = {
                'grant_type': 'fb_exchange_token',
                'client_id': app_id,
                'client_secret': app_secret,
                'fb_exchange_token': access_token
            }
            
            long_token_response = requests.get(long_token_url, params=long_token_params)
            if long_token_response.status_code == 200:
                long_token_data = long_token_response.json()
                access_token = long_token_data.get('access_token', access_token)
            
            # Get ad accounts
            api_service = MetaAPIService(access_token)
            ad_accounts = api_service.get_ad_accounts()
            
            # Save ad accounts to database
            created_count = 0
            for account_data in ad_accounts:
                account_id = account_data.get('id', '').replace('act_', '')
                account_name = account_data.get('name', 'Unknown')
                currency = account_data.get('currency', 'USD')
                timezone_name = account_data.get('timezone_name', 'UTC')
                account_status = account_data.get('account_status', 1)
                
                # Only save active accounts
                if account_status == 1:  # 1 = ACTIVE
                    account, created = MetaAdAccount.objects.update_or_create(
                        account_id=account_id,
                        user=user,
                        defaults={
                            'name': account_name,
                            'currency': currency,
                            'timezone': timezone_name,
                            'status': 'ACTIVE',
                            'is_active': True
                        }
                    )
                    
                    # Set encrypted access token
                    account.set_access_token(access_token)
                    account.save()
                    
                    if created:
                        created_count += 1
            
            return redirect(f"{settings.FRONTEND_URL}/meta-ads?success=true&count={created_count}")
            
        except Exception as e:
            logger.error(f"Error in Meta Ads callback: {e}")
            return redirect(f"{settings.FRONTEND_URL}/meta-ads?error=callback_failed")


class SyncAdAccountsView(APIView):
    """Sync ad accounts from Meta API"""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Sync ad accounts for user"""
        try:
            # Get user's Facebook social account for access token
            from social_accounts.models import SocialAccount
            
            facebook_account = SocialAccount.objects.filter(
                user=request.user,
                platform='facebook',
                is_active=True
            ).first()
            
            if not facebook_account:
                return Response({
                    'error': 'Facebook hesabı bağlı deyil. Əvvəlcə Facebook hesabınızı qoşun.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            access_token = facebook_account.get_access_token()
            
            # Get ad accounts from Meta API
            api_service = MetaAPIService(access_token)
            ad_accounts = api_service.get_ad_accounts()
            
            # Sync to database
            created_count = 0
            updated_count = 0
            
            for account_data in ad_accounts:
                account_id = account_data.get('id', '').replace('act_', '')
                account_name = account_data.get('name', 'Unknown')
                currency = account_data.get('currency', 'USD')
                timezone_name = account_data.get('timezone_name', 'UTC')
                account_status = account_data.get('account_status', 1)
                
                # Only sync active accounts
                if account_status == 1:  # 1 = ACTIVE
                    account, created = MetaAdAccount.objects.update_or_create(
                        account_id=account_id,
                        user=request.user,
                        defaults={
                            'name': account_name,
                            'currency': currency,
                            'timezone': timezone_name,
                            'status': 'ACTIVE',
                            'is_active': True
                        }
                    )
                    
                    # Update access token
                    account.set_access_token(access_token)
                    account.save()
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
            
            return Response({
                'message': 'Ad accounts synced successfully',
                'created': created_count,
                'updated': updated_count,
                'total': len(ad_accounts)
            })
            
        except Exception as e:
            logger.error(f"Error syncing ad accounts: {e}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# CAMPAIGNS
# ============================================================================

class CampaignListView(generics.ListAPIView):
    """List campaigns"""
    
    serializer_class = MetaCampaignSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        account_id = self.request.query_params.get('account_id')
        queryset = MetaCampaign.objects.filter(account__user=self.request.user)
        
        if account_id:
            queryset = queryset.filter(account__account_id=account_id)
        
        return queryset.order_by('-created_at')


class CampaignCreateView(APIView):
    """Create new campaign"""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = CampaignCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            account_id = serializer.validated_data['account_id']
            account = get_object_or_404(MetaAdAccount, account_id=account_id, user=request.user)
            
            # Call Meta API
            api_service = MetaAPIService(account.get_access_token())
            meta_campaign = api_service.create_campaign(
                account_id=account.account_id,
                name=serializer.validated_data['name'],
                objective=serializer.validated_data['objective'],
                status=serializer.validated_data.get('status', 'PAUSED'),
                daily_budget=serializer.validated_data.get('daily_budget'),
                lifetime_budget=serializer.validated_data.get('lifetime_budget'),
            )
            
            # Save to database
            campaign = MetaCampaign.objects.create(
                account=account,
                campaign_id=meta_campaign.get('id'),
                name=serializer.validated_data['name'],
                status=serializer.validated_data.get('status', 'PAUSED'),
                objective=serializer.validated_data['objective'],
                daily_budget=serializer.validated_data.get('daily_budget'),
                lifetime_budget=serializer.validated_data.get('lifetime_budget'),
            )
            
            return Response(
                MetaCampaignSerializer(campaign).data,
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            logger.error(f"Error creating campaign: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CampaignDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete campaign"""
    
    serializer_class = MetaCampaignSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'campaign_id'
    
    def get_queryset(self):
        return MetaCampaign.objects.filter(account__user=self.request.user)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pause_campaign(request, campaign_id):
    """Pause a campaign"""
    try:
        campaign = get_object_or_404(MetaCampaign, campaign_id=campaign_id, account__user=request.user)
        
        api_service = MetaAPIService(campaign.account.get_access_token())
        api_service.update_campaign(campaign.campaign_id, status='PAUSED')
        
        campaign.status = 'PAUSED'
        campaign.save()
        
        return Response({'message': 'Kampaniya dayandırıldı', 'campaign': MetaCampaignSerializer(campaign).data})
    except Exception as e:
        logger.error(f"Error pausing campaign: {e}")
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def resume_campaign(request, campaign_id):
    """Resume a campaign"""
    try:
        campaign = get_object_or_404(MetaCampaign, campaign_id=campaign_id, account__user=request.user)
        
        api_service = MetaAPIService(campaign.account.get_access_token())
        api_service.update_campaign(campaign.campaign_id, status='ACTIVE')
        
        campaign.status = 'ACTIVE'
        campaign.save()
        
        return Response({'message': 'Kampaniya aktivləşdirildi', 'campaign': MetaCampaignSerializer(campaign).data})
    except Exception as e:
        logger.error(f"Error resuming campaign: {e}")
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# AD SETS
# ============================================================================

class AdSetListView(generics.ListAPIView):
    """List ad sets"""
    
    serializer_class = MetaAdSetSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        campaign_id = self.request.query_params.get('campaign_id')
        account_id = self.request.query_params.get('account_id')
        queryset = MetaAdSet.objects.filter(campaign__account__user=self.request.user)
        
        if campaign_id:
            queryset = queryset.filter(campaign__campaign_id=campaign_id)
        elif account_id:
            queryset = queryset.filter(campaign__account__account_id=account_id)
        
        return queryset.order_by('-created_at')


class AdSetDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete ad set"""
    
    serializer_class = MetaAdSetSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'ad_set_id'
    
    def get_queryset(self):
        return MetaAdSet.objects.filter(campaign__account__user=self.request.user)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pause_ad_set(request, ad_set_id):
    """Pause an ad set"""
    try:
        ad_set = get_object_or_404(MetaAdSet, ad_set_id=ad_set_id, campaign__account__user=request.user)
        
        api_service = MetaAPIService(ad_set.campaign.account.get_access_token())
        api_service.update_ad_set(ad_set.ad_set_id, status='PAUSED')
        
        ad_set.status = 'PAUSED'
        ad_set.save()
        
        return Response({'message': 'Reklam qrupu dayandırıldı', 'ad_set': MetaAdSetSerializer(ad_set).data})
    except Exception as e:
        logger.error(f"Error pausing ad set: {e}")
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def resume_ad_set(request, ad_set_id):
    """Resume an ad set"""
    try:
        ad_set = get_object_or_404(MetaAdSet, ad_set_id=ad_set_id, campaign__account__user=request.user)
        
        api_service = MetaAPIService(ad_set.campaign.account.get_access_token())
        api_service.update_ad_set(ad_set.ad_set_id, status='ACTIVE')
        
        ad_set.status = 'ACTIVE'
        ad_set.save()
        
        return Response({'message': 'Reklam qrupu aktivləşdirildi', 'ad_set': MetaAdSetSerializer(ad_set).data})
    except Exception as e:
        logger.error(f"Error resuming ad set: {e}")
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# ADS
# ============================================================================

class AdListView(generics.ListAPIView):
    """List ads"""
    
    serializer_class = MetaAdSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        ad_set_id = self.request.query_params.get('ad_set_id')
        account_id = self.request.query_params.get('account_id')
        queryset = MetaAd.objects.filter(ad_set__campaign__account__user=self.request.user)
        
        if ad_set_id:
            queryset = queryset.filter(ad_set__ad_set_id=ad_set_id)
        elif account_id:
            queryset = queryset.filter(ad_set__campaign__account__account_id=account_id)
        
        return queryset.order_by('-created_at')


class AdDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete ad"""
    
    serializer_class = MetaAdSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'ad_id'
    
    def get_queryset(self):
        return MetaAd.objects.filter(ad_set__campaign__account__user=self.request.user)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pause_ad(request, ad_id):
    """Pause an ad"""
    try:
        ad = get_object_or_404(MetaAd, ad_id=ad_id, ad_set__campaign__account__user=request.user)
        
        api_service = MetaAPIService(ad.ad_set.campaign.account.get_access_token())
        api_service.update_ad(ad.ad_id, status='PAUSED')
        
        ad.status = 'PAUSED'
        ad.save()
        
        return Response({'message': 'Reklam dayandırıldı', 'ad': MetaAdSerializer(ad).data})
    except Exception as e:
        logger.error(f"Error pausing ad: {e}")
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def resume_ad(request, ad_id):
    """Resume an ad"""
    try:
        ad = get_object_or_404(MetaAd, ad_id=ad_id, ad_set__campaign__account__user=request.user)
        
        api_service = MetaAPIService(ad.ad_set.campaign.account.get_access_token())
        api_service.update_ad(ad.ad_id, status='ACTIVE')
        
        ad.status = 'ACTIVE'
        ad.save()
        
        return Response({'message': 'Reklam aktivləşdirildi', 'ad': MetaAdSerializer(ad).data})
    except Exception as e:
        logger.error(f"Error resuming ad: {e}")
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# ANALYTICS
# ============================================================================

class InsightsView(APIView):
    """Get insights/analytics"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        GET /api/meta-ads/insights/
        Query params: account_id, campaign_id, ad_set_id, ad_id, date_preset
        """
        serializer = InsightsRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Get access token from appropriate object
            account_id = serializer.validated_data.get('account_id')
            campaign_id = serializer.validated_data.get('campaign_id')
            
            if account_id:
                account = get_object_or_404(MetaAdAccount, account_id=account_id, user=request.user)
                access_token = account.get_access_token()
                object_id = f"act_{account_id}"
            elif campaign_id:
                campaign = get_object_or_404(MetaCampaign, campaign_id=campaign_id, account__user=request.user)
                access_token = campaign.account.get_access_token()
                object_id = campaign_id
            else:
                return Response({'error': 'account_id or campaign_id required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Get insights from Meta API
            api_service = MetaAPIService(access_token)
            insights = api_service.get_insights(
                object_id=object_id,
                date_preset=serializer.validated_data.get('date_preset', 'last_7d')
            )
            
            if insights:
                insight_data = insights[0]
                return Response({
                    'impressions': int(insight_data.get('impressions', 0)),
                    'reach': int(insight_data.get('reach', 0)),
                    'clicks': int(insight_data.get('clicks', 0)),
                    'spend': float(insight_data.get('spend', 0)),
                    'cpm': float(insight_data.get('cpm', 0)) if insight_data.get('cpm') else None,
                    'cpc': float(insight_data.get('cpc', 0)) if insight_data.get('cpc') else None,
                    'ctr': float(insight_data.get('ctr', 0)) if insight_data.get('ctr') else None,
                    'conversions': int(insight_data.get('conversions', 0)),
                    'date_start': insight_data.get('date_start'),
                    'date_stop': insight_data.get('date_stop'),
                })
            
            return Response({
                'impressions': 0,
                'reach': 0,
                'clicks': 0,
                'spend': 0,
            })
            
        except Exception as e:
            logger.error(f"Error getting insights: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
