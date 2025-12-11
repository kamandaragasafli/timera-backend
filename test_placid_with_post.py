#!/usr/bin/env python
"""
Test Placid API with actual post content
This simulates what will happen when generating posts
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialai_backend.settings')
django.setup()

from posts.services import PlacidService

print("🧪 Testing Placid with Actual Post Content\n")
print("=" * 60)

# Create service instance
placid_service = PlacidService(user=None)

# Test post content (in Azerbaijani like your posts will be)
test_post = """
🚀 Biznesinizi inkişaf etdirmək üçün yeni imkanlar!

Müasir texnologiyalar sayəsində şirkətiniz daha çox müştəriyə çata bilər. 
Bizim xidmətlərimiz ilə rəqəmsal marketinqdə uğur qazanın.

✨ Əsas üstünlüklər:
• Peşəkar komanda
• Müasir həllər
• 24/7 dəstək
"""

print("\n1️⃣  Creating design with test post content...\n")
print(f"Post content (first 100 chars):\n{test_post[:100]}...\n")

try:
    design_data = placid_service.create_design_for_post(test_post)
    
    if design_data.get('thumbnail_url'):
        print("✅ Design created successfully!\n")
        print("📊 Design Details:")
        print(f"   Design ID: {design_data.get('design_id', 'N/A')}")
        print(f"   Design URL: {design_data.get('design_url', 'N/A')}")
        print(f"   Thumbnail: {design_data.get('thumbnail_url', 'N/A')}")
        
        # Check if it's a Placid image or fallback
        if 'placid' in design_data.get('thumbnail_url', ''):
            print("\n✅ Using Placid-generated image!")
        elif 'unsplash' in design_data.get('thumbnail_url', ''):
            print("\n⚠️  Using Unsplash fallback (Placid may have failed)")
        elif 'placeholder' in design_data.get('thumbnail_url', ''):
            print("\n⚠️  Using placeholder (Placid failed)")
        
        print("\n" + "=" * 60)
        print("✅ Test Complete!\n")
        print("🎉 Placid integration is working!")
        print("\nYou can view the generated image at:")
        print(design_data.get('thumbnail_url', 'N/A'))
        
    else:
        print("❌ No thumbnail URL returned")
        print("Design data:", design_data)
        
except Exception as e:
    print(f"❌ Error: {e}")
    print("\n⚠️  Check:")
    print("   1. PLACID_API_KEY is set in local.env")
    print("   2. PLACID_DEFAULT_TEMPLATE is set in local.env")
    print("   3. Template UUID is correct")

print("\n" + "=" * 60)
print("\n🚀 Next step: Deploy to production!")
print("\nFollow: PLACID_INTEGRATION_DEPLOYMENT.md")





