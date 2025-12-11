from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Authentication endpoints
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    
    # JWT token endpoints
    path('token/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # User profile endpoints
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('password/change/', views.PasswordChangeView.as_view(), name='password_change'),
    path('stats/', views.user_stats, name='user_stats'),
    
    # Brand voice endpoints
    path('brand-voices/', views.BrandVoiceListCreateView.as_view(), name='brand_voices'),
    path('brand-voices/<uuid:pk>/', views.BrandVoiceDetailView.as_view(), name='brand_voice_detail'),
    
    # Company profile endpoints
    path('company-profile/', views.CompanyProfileView.as_view(), name='company_profile'),
]

