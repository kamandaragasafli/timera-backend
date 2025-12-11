#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test Ideogram.ai Integration
Generates test images with Azerbaijani text
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialai_backend.settings')
django.setup()

from posts.services import IdeogramService

print("🎨 Testing Ideogram.ai Integration\n")
print("=" * 70)

# Create service
ideogram_service = IdeogramService(user=None)

# Test with Azerbaijani text
test_posts = [
    "Müştərilərimizə ən yaxşı xidmət göstəririk!",
    "Öyrənmək və inkişaf etmək üçün buradayıq",
    "Şirkətimiz çox peşəkar və etibarlıdır"
]

print(f"\n🧪 Generating {len(test_posts)} test images...\n")
print("⚠️  NOTE: Images will have NO TEXT - just backgrounds!")
print("   Text will be overlaid by frontend later\n")

for idx, text in enumerate(test_posts, 1):
    print(f"{'='*70}")
    print(f"TEST {idx}/{len(test_posts)}")
    print(f"{'='*70}")
    print(f"\n📝 Post text (for reference): {text}")
    print("   (This text will NOT appear in the image)")
    
    try:
        result = ideogram_service.create_design_for_post(text)
        
        if result.get('thumbnail_url'):
            print(f"\n✅ SUCCESS!")
            print(f"\n📸 Generated Image:")
            print(f"   {result['thumbnail_url']}")
            print(f"\n👉 Open this URL to see the image with text overlay!")
        else:
            print(f"\n⚠️  No image generated (using fallback)")
            print(f"   URL: {result.get('thumbnail_url', 'N/A')}")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    print()

print("=" * 70)
print("\n✅ Test Complete!")
print("\n📋 What to check:")
print("   ✅ Each image should have NO TEXT (just backgrounds)")
print("   ✅ Images should be abstract/gradient/geometric patterns")
print("   ✅ Professional colors (blue, purple, orange gradients)")
print("   ✅ Clean, minimal design suitable for text overlay")
print("   ✅ Each image should look DIFFERENT from others")
print("\n💡 Text will be added by frontend as overlay, NOT in the image!")
print("\n" + "=" * 70)

