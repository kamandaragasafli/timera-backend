from django.contrib import admin
from .models import Post, AIGeneratedContent, PostPlatform, ContentTemplate


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'status', 'ai_generated', 'scheduled_time', 'created_at')
    list_filter = ('status', 'ai_generated', 'requires_approval', 'created_at')
    search_fields = ('title', 'content', 'user__email')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'updated_at', 'published_at')
    
    fieldsets = (
        (None, {
            'fields': ('user', 'title', 'content', 'description', 'hashtags')
        }),
        ('AI Generation', {
            'fields': ('ai_generated', 'ai_content_batch', 'brand_voice', 'ai_prompt')
        }),
        ('Images & Design', {
            'fields': ('design_url', 'design_thumbnail', 'canva_design_id', 'custom_image', 'design_specs', 'imgly_scene')
        }),
        ('Approval', {
            'fields': ('status', 'requires_approval', 'approved_by', 'approved_at')
        }),
        ('Scheduling', {
            'fields': ('scheduled_time', 'published_at')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AIGeneratedContent)
class AIGeneratedContentAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'total_posts', 'approved_posts', 'language', 'created_at')
    list_filter = ('status', 'language', 'created_at')
    search_fields = ('user__email', 'generation_prompt')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(PostPlatform)
class PostPlatformAdmin(admin.ModelAdmin):
    list_display = ('post', 'social_account', 'status', 'published_at', 'retry_count')
    list_filter = ('status', 'social_account__platform', 'published_at')
    search_fields = ('post__title', 'social_account__platform_username')
    ordering = ('-created_at',)


@admin.register(ContentTemplate)
class ContentTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'category', 'usage_count', 'is_active', 'created_at')
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('name', 'user__email', 'template_content')
    ordering = ('-created_at',)
