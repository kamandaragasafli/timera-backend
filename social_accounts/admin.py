from django.contrib import admin
from .models import SocialAccount


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ['user', 'platform', 'platform_username', 'display_name', 'is_active', 'created_at']
    list_filter = ['platform', 'is_active']
    search_fields = ['user__email', 'platform_username', 'display_name']
    readonly_fields = ['created_at', 'updated_at', 'access_token_encrypted', 'refresh_token_encrypted']
    
    fieldsets = (
        ('Account Information', {
            'fields': ('user', 'platform', 'platform_user_id', 'platform_username', 'display_name')
        }),
        ('Profile', {
            'fields': ('profile_picture_url',)
        }),
        ('Status', {
            'fields': ('is_active', 'expires_at', 'last_used')
        }),
        ('Tokens (Encrypted)', {
            'fields': ('access_token_encrypted', 'refresh_token_encrypted'),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': ('settings',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
