from django.contrib import admin
from .models import ProfileAnalysis


@admin.register(ProfileAnalysis)
class ProfileAnalysisAdmin(admin.ModelAdmin):
    list_display = ['profile_username', 'platform', 'profile_url', 'access_count', 'last_accessed', 'created_at']
    list_filter = ['platform', 'created_at', 'last_accessed']
    search_fields = ['profile_url', 'profile_username']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_accessed', 'access_count']
    
    fieldsets = (
        ('Profil Məlumatları', {
            'fields': ('profile_url', 'profile_username', 'platform', 'user')
        }),
        ('Cache Məlumatları', {
            'fields': ('preview_data', 'smm_analysis')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at', 'last_accessed', 'access_count')
        }),
    )

