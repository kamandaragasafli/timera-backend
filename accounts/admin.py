from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, BrandVoice, CompanyProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'username', 'first_name', 'last_name', 'company_name', 'subscription_plan', 'is_active', 'created_at')
    list_filter = ('subscription_plan', 'is_active', 'is_email_verified', 'created_at')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'company_name')
    ordering = ('-created_at',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('company_name', 'brand_voice_settings', 'timezone', 'subscription_plan', 'is_email_verified')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('email', 'first_name', 'last_name', 'company_name')
        }),
    )


@admin.register(BrandVoice)
class BrandVoiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'tone', 'industry', 'is_default', 'created_at')
    list_filter = ('tone', 'is_default', 'created_at')
    search_fields = ('name', 'user__email', 'industry', 'target_audience')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {
            'fields': ('user', 'name', 'tone', 'is_default')
        }),
        ('Configuration', {
            'fields': ('industry', 'target_audience', 'custom_instructions')
        }),
    )


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'user', 'industry', 'company_size', 'preferred_tone', 'created_at')
    list_filter = ('industry', 'company_size', 'preferred_tone', 'primary_language', 'created_at')
    search_fields = ('company_name', 'user__email', 'business_description')
    ordering = ('-created_at',)
    readonly_fields = ('logo_preview',)
    
    def logo_preview(self, obj):
        if obj.logo:
            return f'<img src="{obj.logo.url}" width="150" height="150" style="object-fit: contain;" />'
        return "No logo"
    logo_preview.allow_tags = True
    logo_preview.short_description = 'Logo Preview'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'company_name', 'industry', 'company_size', 'website', 'location', 'logo', 'logo_preview')
        }),
        ('AI Brand Analysis', {
            'fields': ('brand_analysis',),
            'classes': ('collapse',),
            'description': 'AI-generated brand information from logo'
        }),
        ('Business Description', {
            'fields': ('business_description', 'target_audience', 'unique_selling_points')
        }),
        ('Social Media Strategy', {
            'fields': ('social_media_goals', 'preferred_tone', 'primary_language')
        }),
        ('Content Preferences', {
            'fields': ('content_topics', 'keywords', 'avoid_topics')
        }),
        ('AI Generation Settings', {
            'fields': ('posts_to_generate',)
        }),
    )
