#!/usr/bin/env python
"""
Test Post Generation Directly
Bypasses frontend to test backend directly
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialai_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import CompanyProfile
from posts.services import PostGenerationService

User = get_user_model()


def main():
    print("\n" + "="*70)
    print("POST GENERATION DIAGNOSTIC TEST")
    print("="*70)
    
    # Check 1: Users exist
    print("\n📋 CHECK 1: Users")
    users = User.objects.all()
    if not users.exists():
        print("❌ No users found in database")
        print("   Solution: Create a user account first")
        return
    
    user = users.first()
    print(f"✅ Found user: {user.email}")
    
    # Check 2: Company Profile exists
    print("\n📋 CHECK 2: Company Profile")
    try:
        company_profile = CompanyProfile.objects.get(user=user)
        print(f"✅ Found company profile: {company_profile.company_name}")
        print(f"   Industry: {company_profile.industry}")
        print(f"   Description: {company_profile.business_description[:50]}...")
    except CompanyProfile.DoesNotExist:
        print(f"❌ No company profile for user: {user.email}")
        print("\n💡 SOLUTION: Create company profile")
        print("   Run this code:")
        print(f"""
   profile = CompanyProfile.objects.create(
       user=user,
       company_name="Test Company",
       industry="technology",
       company_size="1-10",
       business_description="We provide innovative technology solutions",
       target_audience="Small and medium businesses",
       unique_selling_points="Quality, Speed, Innovation",
       social_media_goals="Increase brand awareness",
       preferred_tone="professional"
   )
   print("✅ Profile created!")
        """)
        return
    
    # Check 3: OpenAI API Key
    print("\n📋 CHECK 3: OpenAI API Key")
    from django.conf import settings
    api_key = settings.OPENAI_API_KEY
    if api_key and api_key != '':
        print(f"✅ OpenAI API Key configured: {api_key[:10]}...")
    else:
        print("❌ OpenAI API Key NOT configured")
        print("   Solution: Add OPENAI_API_KEY to local.env")
        return
    
    # Check 4: Try generating posts
    print("\n📋 CHECK 4: Generate Posts")
    print("Attempting to generate posts...")
    
    try:
        service = PostGenerationService(user=user)
        ai_batch, posts = service.generate_monthly_content(user, custom_prompt="Generate posts about technology")
        
        print(f"\n✅ SUCCESS! Generated {len(posts)} posts")
        print(f"   Batch ID: {ai_batch.id}")
        print(f"   Posts:")
        for i, post in enumerate(posts[:3], 1):
            print(f"   {i}. {post.content[:60]}...")
        
    except ValueError as e:
        print(f"\n❌ ValueError: {str(e)}")
        print("\n💡 This is usually:")
        print("   - Missing company profile")
        print("   - Invalid company profile data")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print(f"\n📝 Error type: {type(e).__name__}")
        
        import traceback
        print("\n🔍 Full traceback:")
        traceback.print_exc()
        
        # Common issues
        print("\n💡 COMMON ISSUES:")
        print("   1. OpenAI API key invalid or expired")
        print("   2. OpenAI API quota exceeded")
        print("   3. Network connection issue")
        print("   4. Company profile has empty required fields")


if __name__ == '__main__':
    main()

