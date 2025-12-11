from django.urls import path
from . import views

urlpatterns = [
    path('generate-content/', views.GenerateContentView.as_view(), name='generate_content'),
    path('optimize-platform/', views.OptimizeForPlatformView.as_view(), name='optimize_platform'),
    path('analyze-logo/', views.AnalyzeLogoView.as_view(), name='analyze_logo'),
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
]

