#!/usr/bin/env python
"""
Create Company Profile for Testing
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialai_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import CompanyProfile

User = get_user_model()


def main():
    print("\n" + "="*70)
    print("CREATE COMPANY PROFILE")
    print("="*70)
    
    # Get first user
    user = User.objects.first()
    
    if not user:
        print("❌ No users found. Create a user first.")
        return
    
    print(f"\n👤 User: {user.email}")
    
    # Check if profile already exists
    existing = CompanyProfile.objects.filter(user=user).first()
    if existing:
        print(f"\n⚠️  Company profile already exists: {existing.company_name}")
        print("   Deleting old profile...")
        existing.delete()
    
    # Create new company profile
    print("\n🏢 Creating company profile...")
    
    profile = CompanyProfile.objects.create(
        user=user,
        company_name="Timera",
        industry="technology",
        company_size="1-10",
        website="https://timera.az",
        location="Azerbaijan",
        business_description="Timera is an AI-powered social media management platform that helps businesses create and publish engaging content across multiple social media platforms.",
        target_audience="Small and medium-sized businesses looking to improve their social media presence",
        unique_selling_points="AI-powered content generation, Multi-platform publishing, Automated branding, Smart scheduling",
        social_media_goals="Help businesses increase their social media engagement and reach",
        preferred_tone="professional",
        content_topics=["social media", "marketing", "AI", "business growth"],
        keywords=["social media", "AI", "automation", "marketing"],
        avoid_topics=["politics", "religion"],
        primary_language="az",
        posts_to_generate=10,
        # Branding settings
        slogan="Transform Your Social Media",
        branding_enabled=True,
        branding_mode="standard",
        logo_position="bottom-right",
        logo_size_percent=5
    )
    
    print(f"\n✅ Company profile created successfully!")
    print(f"   ID: {profile.id}")
    print(f"   Name: {profile.company_name}")
    print(f"   Industry: {profile.industry}")
    print(f"   Branding Mode: {profile.branding_mode}")
    print(f"   Slogan: {profile.slogan}")
    
    print("\n🎉 Now you can generate posts!")
    print("   Try generating posts from your frontend or run:")
    print("   python test_post_generation.py")


if __name__ == '__main__':
    main()

