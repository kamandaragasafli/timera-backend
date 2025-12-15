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
        
        logger.info(f"[INFO] Company profile update request from user: {request.user.email}")
        logger.info(f"   Content-Type: {request.content_type}")
        logger.info(f"   Method: {request.method}")
        logger.info(f"   Has FILES: {bool(request.FILES)}")
        logger.info(f"   FILES keys: {list(request.FILES.keys()) if request.FILES else 'None'}")
        logger.info(f"   Has logo file: {bool(request.FILES.get('logo'))}")
        logger.info(f"   Data keys: {list(request.data.keys())}")
        if request.data.get('slogan'):
            try:
                slogan = request.data.get('slogan')
                logger.info(f"   Slogan: {slogan}")
            except UnicodeEncodeError:
                logger.info(f"   Slogan: [contains non-ASCII characters]")
        
        # Check if logo file exists
        logo_file = request.FILES.get('logo')
        if logo_file:
            logger.info(f"   Logo file details: name={logo_file.name}, size={logo_file.size}, content_type={logo_file.content_type}")
        else:
            logger.warning(f"   [WARNING] No logo file found in request.FILES")
        
        try:
            # Parse JSON fields if they come as strings
            # Convert request.data to a regular dict for easier manipulation
            # For FormData/QueryDict, we need to properly extract values
            data = {}
            for key, value in request.data.items():
                # For QueryDict, getlist returns list, get returns single value
                # Since FormData sends single values, we use the single value
                if hasattr(request.data, 'getlist'):
                    # QueryDict - get the first value (FormData sends single values)
                    data[key] = request.data.get(key)
                else:
                    # Already a dict
                    data[key] = value
            
            json_fields = ['content_topics', 'keywords', 'avoid_topics', 'brand_analysis']
            for field in json_fields:
                if field in data:
                    field_value = data[field]
                    original_value = field_value
                    
                    # Handle string values that need JSON parsing
                    if isinstance(field_value, str):
                        # Skip empty strings
                        if not field_value.strip():
                            if field == 'brand_analysis':
                                data[field] = {}
                            else:
                                data[field] = []
                            continue
                            
                        try:
                            # Try to parse as JSON first
                            parsed_value = json.loads(field_value)
                            data[field] = parsed_value
                            logger.info(f"   Parsed {field} from JSON string: {type(parsed_value).__name__}")
                        except (json.JSONDecodeError, ValueError) as e:
                            # If JSON parsing fails, try splitting by comma for list fields
                            if field != 'brand_analysis':  # brand_analysis should be a dict
                                if field_value.strip():
                                    data[field] = [s.strip() for s in field_value.split(',') if s.strip()]
                                    logger.info(f"   Parsed {field} from comma-separated string: {len(data[field])} items")
                                else:
                                    data[field] = []
                            else:
                                # For brand_analysis, if it's not valid JSON, use empty dict
                                logger.warning(f"   Failed to parse {field} as JSON, using empty dict. Error: {e}")
                                data[field] = {}
                    # Handle list values (already parsed)
                    elif isinstance(field_value, list):
                        data[field] = field_value
                        logger.info(f"   {field} is already a list: {len(field_value)} items")
                    # Handle dict values (for brand_analysis)
                    elif isinstance(field_value, dict):
                        data[field] = field_value
                        logger.info(f"   {field} is already a dict: {len(field_value)} keys")
                    # Handle None or empty values
                    elif not field_value or field_value == '':
                        if field == 'brand_analysis':
                            data[field] = {}
                        else:
                            data[field] = []
                        logger.info(f"   {field} was empty, set to default value")
                else:
                    # Field not in data, set default
                    if field == 'brand_analysis':
                        data[field] = {}
                    else:
                        data[field] = []
            
            # Get the instance
            instance = self.get_object()
            
            # Get serializer with parsed data (pass as dict, not QueryDict)
            # Include FILES if present - merge data with FILES
            serializer_data = data.copy()
            if request.FILES:
                # FILES are already in request, serializer will get them from context
                pass
            
            # Log the data before passing to serializer for debugging
            logger.info(f"   Data before serializer (first 500 chars): {str(serializer_data)[:500]}")
            for field in ['content_topics', 'keywords', 'avoid_topics', 'brand_analysis']:
                if field in serializer_data:
                    value = serializer_data[field]
                    logger.info(f"   {field} type: {type(value).__name__}, value: {str(value)[:200]}")
            
            serializer = self.get_serializer(
                instance, 
                data=serializer_data, 
                partial=True,
                context={'request': request}
            )
            
            # Validate and log errors if any
            if not serializer.is_valid():
                logger.error(f"   Serializer validation errors: {serializer.errors}")
                raise serializers.ValidationError(serializer.errors)
            serializer.save()
            
            logger.info(f"[SUCCESS] Company profile updated successfully")
            
            if getattr(instance, '_prefetched_objects_cache', None):
                instance._prefetched_objects_cache = {}
            
            return Response(serializer.data)
        except serializers.ValidationError as e:
            logger.error(f"[ERROR] Validation error updating company profile: {e}", exc_info=True)
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
            logger.error(f"[ERROR] Error updating company profile: {e}", exc_info=True)
            error_detail = str(e)
            
            # Try to get more details from validation errors
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
