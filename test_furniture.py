#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test Ideogram.ai with Furniture Content
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialai_backend.settings')
django.setup()

from posts.services import IdeogramService

print("🪑 Testing Ideogram.ai with Furniture Content\n")
print("=" * 70)

# Create service
ideogram_service = IdeogramService(user=None)

# Test with furniture-related content
test_posts = [
    "Yeni kolleksiyamız: modern divan və kreslo dəstləri",
    "Ofis mebeli - keyfiyyətli və rahat",
    "Yataq otağı üçün lüks mebellərimiz"
]

print(f"\n🧪 Generating {len(test_posts)} furniture images...\n")

for idx, text in enumerate(test_posts, 1):
    print(f"{'='*70}")
    print(f"TEST {idx}/{len(test_posts)}")
    print(f"{'='*70}")
    print(f"\n📝 Post: {text}\n")
    
    try:
        result = ideogram_service.create_design_for_post(text)
        
        if result.get('thumbnail_url'):
            print(f"\n✅ SUCCESS!")
            print(f"📸 Image: {result['thumbnail_url']}\n")
        else:
            print(f"\n⚠️  Fallback used\n")
    
    except Exception as e:
        print(f"\n❌ Error: {e}\n")

print("=" * 70)
print("\n✅ Check console logs above to see FULL PROMPTS sent to Ideogram!")
print("   Each request shows:")
print("   - Post content")
print("   - Full prompt sent to API")
print("   - Request parameters")
print("\n" + "=" * 70)





