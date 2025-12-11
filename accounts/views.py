from rest_framework import generics, status, permissions, parsers, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import authenticate
import json
from .models import User, BrandVoice, CompanyProfile
from .serializers import (
    UserSerializer, 
    UserRegistrationSerializer, 
    CustomTokenObtainPairSerializer,
    LoginSerializer,
    BrandVoiceSerializer,
    PasswordChangeSerializer,
    CompanyProfileSerializer
)


class RegisterView(generics.CreateAPIView):
    """User registration endpoint"""
    
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'User registered successfully'
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """User login endpoint"""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'Login successful'
        }, status=status.HTTP_200_OK)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom JWT token view that returns user data"""
    
    serializer_class = CustomTokenObtainPairSerializer


class LogoutView(APIView):
    """User logout endpoint"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(generics.RetrieveUpdateAPIView):
    """User profile view"""
    
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class PasswordChangeView(APIView):
    """Password change endpoint"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({'message': 'Password changed successfully'}, status=status.HTTP_200_OK)


class BrandVoiceListCreateView(generics.ListCreateAPIView):
    """List and create brand voices"""
    
    serializer_class = BrandVoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return BrandVoice.objects.filter(user=self.request.user)


class BrandVoiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, and delete brand voices"""
    
    serializer_class = BrandVoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return BrandVoice.objects.filter(user=self.request.user)


class CompanyProfileView(generics.RetrieveUpdateAPIView):
    """Company profile management"""
    
    serializer_class = CompanyProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]
    
    def get_object(self):
        profile, created = CompanyProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                'company_name': self.request.user.company_name or '',
                'industry': 'other',
                'company_size': '1-10',
                'business_description': '',
                'target_audience': '',
                'unique_selling_points': '',
                'social_media_goals': '',
                'preferred_tone': 'professional',
                'content_topics': [],
                'keywords': [],
                'avoid_topics': [],
                'primary_language': 'az'
            }
        )
        return profile
    
    def update(self, request, *args, **kwargs):
        """Update company profile with better error handling"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"📥 Company profile update request from user: {request.user.email}")
        logger.info(f"   Content-Type: {request.content_type}")
        logger.info(f"   Method: {request.method}")
        logger.info(f"   Has FILES: {bool(request.FILES)}")
        logger.info(f"   FILES keys: {list(request.FILES.keys()) if request.FILES else 'None'}")
        logger.info(f"   Has logo file: {bool(request.FILES.get('logo'))}")
        logger.info(f"   Data keys: {list(request.data.keys())}")
        if request.data.get('slogan'):
            logger.info(f"   Slogan: {request.data.get('slogan')}")
        
        # Check if logo file exists
        logo_file = request.FILES.get('logo')
        if logo_file:
            logger.info(f"   Logo file details: name={logo_file.name}, size={logo_file.size}, content_type={logo_file.content_type}")
        else:
            logger.warning(f"   ⚠️ No logo file found in request.FILES")
        
        try:
            # Parse JSON fields if they come as strings
            data = request.data.copy()
            json_fields = ['content_topics', 'keywords', 'avoid_topics', 'brand_analysis']
            for field in json_fields:
                if field in data and isinstance(data[field], str):
                    try:
                        data[field] = json.loads(data[field])
                    except (json.JSONDecodeError, TypeError):
                        # If it's a string that can't be parsed, try splitting by comma
                        if data[field]:
                            data[field] = [s.strip() for s in data[field].split(',') if s.strip()]
                        else:
                            data[field] = []
            
            # Update request.data with parsed values
            request._full_data = data
            
            result = super().update(request, *args, **kwargs)
            logger.info(f"✅ Company profile updated successfully")
            return result
        except serializers.ValidationError as e:
            logger.error(f"❌ Validation error updating company profile: {e}", exc_info=True)
            error_detail = str(e)
            
            # Get detailed validation errors
            if hasattr(e, 'detail'):
                if isinstance(e.detail, dict):
                    error_detail = json.dumps(e.detail, indent=2, ensure_ascii=False)
                else:
                    error_detail = str(e.detail)
            
            return Response({
                'error': 'Validation xətası',
                'detail': error_detail,
                'message': 'Şirkət profili məlumatları düzgün deyil. Zəhmət olmasa bütün tələb olunan sahələri doldurun.'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"❌ Error updating company profile: {e}", exc_info=True)
            error_detail = str(e)
            
            # Try to get more details from validation errors
            import json
            if hasattr(e, 'detail'):
                if isinstance(e.detail, dict):
                    error_detail = json.dumps(e.detail, indent=2, ensure_ascii=False)
                else:
                    error_detail = str(e.detail)
            
            return Response({
                'error': error_detail,
                'detail': 'Company profile update failed. Please check the logs.',
                'message': 'Şirkət profili yenilənərkən xəta baş verdi. Zəhmət olmasa yenidən cəhd edin.'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def options(self, request, *args, **kwargs):
        """Handle preflight OPTIONS request for CORS"""
        from django.http import HttpResponse
        response = HttpResponse()
        response['Access-Control-Allow-Origin'] = request.META.get('HTTP_ORIGIN', '*')
        response['Access-Control-Allow-Methods'] = 'GET, PUT, PATCH, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
        response['Access-Control-Allow-Credentials'] = 'true'
        return response


class CompanyProfileCreateView(generics.CreateAPIView):
    """Create company profile"""
    
    serializer_class = CompanyProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        # Check if profile already exists
        if hasattr(request.user, 'company_profile'):
            return Response({
                'error': 'Company profile already exists. Use PUT to update.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return super().create(request, *args, **kwargs)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_stats(request):
    """Get user statistics"""
    user = request.user
    
    # Import here to avoid circular imports
    from posts.models import Post
    from social_accounts.models import SocialAccount
    
    stats = {
        'total_posts': Post.objects.filter(user=user).count(),
        'pending_approval': Post.objects.filter(user=user, status='pending_approval').count(),
        'approved_posts': Post.objects.filter(user=user, status='approved').count(),
        'published_posts': Post.objects.filter(user=user, status='published').count(),
        'scheduled_posts': Post.objects.filter(user=user, status='scheduled').count(),
        'draft_posts': Post.objects.filter(user=user, status='draft').count(),
        'connected_accounts': SocialAccount.objects.filter(user=user, is_active=True).count(),
        'brand_voices': BrandVoice.objects.filter(user=user).count(),
        'has_company_profile': hasattr(user, 'company_profile'),
    }
    
    return Response(stats)
