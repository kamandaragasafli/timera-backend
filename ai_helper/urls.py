from django.urls import path
from . import views

urlpatterns = [
    path('generate-content/', views.GenerateContentView.as_view(), name='generate_content'),
    path('optimize-platform/', views.OptimizeForPlatformView.as_view(), name='optimize_platform'),
    path('analyze-logo/', views.AnalyzeLogoView.as_view(), name='analyze_logo'),
    path('generate-complementary-colors/', views.GenerateComplementaryColorsView.as_view(), name='generate_complementary_colors'),
    path('generate-slogan/', views.GenerateSloganView.as_view(), name='generate_slogan'),
    path('generate-hashtags/', views.GenerateHashtagsView.as_view(), name='generate_hashtags'),
    path('optimize-caption/', views.OptimizeCaptionView.as_view(), name='optimize_caption'),
    path('analyze-trends/', views.AnalyzeTrendsView.as_view(), name='analyze_trends'),
    path('competitor-analysis/', views.CompetitorAnalysisView.as_view(), name='competitor_analysis'),
    path('generate-smart-prompt/', views.GenerateSmartPromptView.as_view(), name='generate_smart_prompt'),
    path('wask/generate-logo-slogan/', views.generate_logo_slogan, name='wask_generate_logo_slogan'),
    path('create-ad-creative/', views.create_ad_creative, name='create_ad_creative'),
    # Fal.ai endpoints
    path('fal-ai/image-to-video/', views.image_to_video, name='fal_ai_image_to_video'),
    path('fal-ai/edit-image/', views.edit_image, name='fal_ai_edit_image'),
    # Nano Banana endpoints
    path('fal-ai/nano-banana/text-to-image/', views.nano_banana_text_to_image, name='nano_banana_text_to_image'),
    path('fal-ai/nano-banana/image-to-image/', views.nano_banana_image_to_image, name='nano_banana_image_to_image'),
    # Kling Video endpoints
    path('fal-ai/kling-video/text-to-video/', views.kling_video_text_to_video, name='kling_video_text_to_video'),
    # Product Post Creation
    path('product-post/', views.create_product_post, name='create_product_post'),
    # Product Post from URL (NEW)
    path('product-post-from-url/', views.create_product_post_from_url, name='create_product_post_from_url'),
    # Social Media Analysis
    path('instagram-analysis/', views.analyze_instagram_profile, name='analyze_instagram_profile'),
    path('facebook-analysis/', views.analyze_facebook_profile, name='analyze_facebook_profile'),
    path('linkedin-analysis/', views.analyze_linkedin_profile, name='analyze_linkedin_profile'),
    path('analyze-profile/', views.analyze_profile_from_url, name='analyze_profile_from_url'),
    path('saved-profiles/', views.get_saved_profiles, name='get_saved_profiles'),
    # Translation
    path('translate/', views.translate_text, name='translate_text'),
]

