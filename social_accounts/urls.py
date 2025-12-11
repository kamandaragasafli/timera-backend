from django.urls import path
from . import views

urlpatterns = [
    # List connected accounts
    path('', views.SocialAccountListView.as_view(), name='social_accounts'),
    
    # OAuth flow
    path('auth-url/<str:platform>/', views.GetOAuthUrlView.as_view(), name='get_oauth_url'),
    path('callback/<str:platform>/', views.OAuthCallbackView.as_view(), name='oauth_callback'),
    
    # Disconnect account
    path('<uuid:pk>/', views.DisconnectAccountView.as_view(), name='disconnect_account'),
]
