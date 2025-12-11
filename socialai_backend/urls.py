"""
URL configuration for socialai_backend project.

AI Social Media Management Tool API
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
# from drf_spectacular.views import (
#     SpectacularAPIView,
#     SpectacularRedocView,
#     SpectacularSwaggerView,
# )
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/auth/', include('accounts.urls')),
    path('api/posts/', include('posts.urls')),
    path('api/social-accounts/', include('social_accounts.urls')),
    path('api/ai/', include('ai_helper.urls')),
    path('api/meta-ads/', include('meta_ads.urls')),
    
    # Swagger/OpenAPI Documentation (pip install drf-spectacular==0.27.2)
    # path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Meta compliance pages (URLs must match what's in Meta App settings)
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms/', views.terms_of_service, name='terms_of_service'),
    path('user-data-deletion/', views.user_data_deletion, name='user_data_deletion'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
