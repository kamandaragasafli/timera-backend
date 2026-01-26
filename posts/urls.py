from django.urls import path
from . import views

urlpatterns = [
    # 1. Root endpoint
    path('', views.PostListCreateView.as_view(), name='posts'),
    
    # 2. Spesifik string pattern-lər (UUID-dən ƏVVƏL - yuxarıdan aşağı işləyir!)
    path('generate/', views.GeneratePostsView.as_view(), name='generate_posts'),
    path('pending/', views.PendingPostsView.as_view(), name='pending_posts'),
    path('approve/', views.PostApprovalView.as_view(), name='post_approval'),
    path('templates/', views.ContentTemplateListCreateView.as_view(), name='content_templates'),
    path('stats/', views.post_stats, name='post_stats'),
    path('proxy-image/', views.proxy_image, name='proxy_image'),
    path('ai-batches/', views.AIGeneratedContentListView.as_view(), name='ai_batches'),
    path('optimal-timing/', views.OptimalTimingView.as_view(), name='optimal_timing'),
    path('performance/', views.PostPerformanceListView.as_view(), name='post_performance_list'),
    path('<uuid:post_id>/schedule/', views.SchedulePostView.as_view(), name='schedule_post'),
    path('<uuid:post_id>/performance/', views.PostPerformanceView.as_view(), name='post_performance'),
    
    # 3. UUID ilə spesifik pattern-lər (Generic <uuid:pk>/ pattern-dən ƏVVƏL)
    path('<uuid:post_id>/publish/', views.PublishPostView.as_view(), name='publish_post'),
    path('<uuid:post_id>/publish-facebook/', views.PublishToFacebookView.as_view(), name='publish_facebook'),
    path('<uuid:post_id>/publish-instagram/', views.PublishToInstagramView.as_view(), name='publish_instagram'),
    path('<uuid:post_id>/publish-linkedin/', views.PublishToLinkedInView.as_view(), name='publish_linkedin'),
    path('<uuid:post_id>/upload-image/', views.UploadCustomImageView.as_view(), name='upload_image'),
    path('<uuid:post_id>/apply-branding/', views.ApplyBrandingView.as_view(), name='apply_branding'),
    path('<uuid:post_id>/regenerate-design/', views.regenerate_canva_design, name='regenerate_design'),
    
    # 4. Templates ilə UUID pattern-lər
    path('templates/<uuid:pk>/', views.ContentTemplateDetailView.as_view(), name='content_template_detail'),
    
    # 5. Generic UUID pattern-lər (ƏN SONDA - spesifik pattern-lər match olmadıqda)
    path('<uuid:pk>/', views.PostDetailView.as_view(), name='post_detail'),
    
    # DEPRECATED: Canva OAuth endpoints (Replaced with Placid.app)
    # path('canva/connect/', views.canva_oauth_initiate, name='canva_connect'),
    # path('canva/callback/', views.canva_oauth_callback, name='canva_callback'),
    # path('canva/status/', views.canva_connection_status, name='canva_status'),
]

