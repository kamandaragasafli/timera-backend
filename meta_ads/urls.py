"""
Meta Ads URL Configuration
"""

from django.urls import path
from . import views

app_name = 'meta_ads'

urlpatterns = [
    # Ad Accounts (static routes before dynamic to avoid 404 shadowing)
    path('accounts/connect/', views.ConnectAdAccountView.as_view(), name='connect_ad_account'),
    path('accounts/sync/', views.SyncAdAccountsView.as_view(), name='sync_ad_accounts'),
    path('accounts/', views.AdAccountListView.as_view(), name='ad_account_list'),
    path('accounts/<str:account_id>/', views.AdAccountDetailView.as_view(), name='ad_account_detail'),
    path('accounts/<str:account_id>/test-permissions/', views.TestPermissionsView.as_view(), name='test_permissions'),
    path('callback/', views.AdAccountCallbackView.as_view(), name='ad_account_callback'),
    
    # Campaigns
    path('campaigns/', views.CampaignListView.as_view(), name='campaign_list'),
    path('campaigns/create/', views.CampaignCreateView.as_view(), name='campaign_create'),
    path('campaigns/<str:campaign_id>/', views.CampaignDetailView.as_view(), name='campaign_detail'),
    path('campaigns/<str:campaign_id>/pause/', views.pause_campaign, name='pause_campaign'),
    path('campaigns/<str:campaign_id>/resume/', views.resume_campaign, name='resume_campaign'),
    
    # Ad Sets
    path('ad-sets/', views.AdSetListView.as_view(), name='ad_set_list'),
    path('ad-sets/<str:ad_set_id>/', views.AdSetDetailView.as_view(), name='ad_set_detail'),
    path('ad-sets/<str:ad_set_id>/pause/', views.pause_ad_set, name='pause_ad_set'),
    path('ad-sets/<str:ad_set_id>/resume/', views.resume_ad_set, name='resume_ad_set'),
    
    # Ads
    path('ads/', views.AdListView.as_view(), name='ad_list'),
    path('ads/<str:ad_id>/', views.AdDetailView.as_view(), name='ad_detail'),
    path('ads/<str:ad_id>/pause/', views.pause_ad, name='pause_ad'),
    path('ads/<str:ad_id>/resume/', views.resume_ad, name='resume_ad'),
    
    # Analytics
    path('insights/', views.InsightsView.as_view(), name='insights'),
]

