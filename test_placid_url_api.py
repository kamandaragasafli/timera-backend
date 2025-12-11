#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test Placid URL API - Much Simpler!
No POST requests, no auth issues, just URLs!
"""

from urllib.parse import quote

PLACID_TEMPLATE = "sxaa11eh8z4tf"

print("🎨 Testing Placid URL API")
print("=" * 70)
print("✨ This is MUCH simpler - just construct a URL!")
print("=" * 70)

# Test cases with Azerbaijani text
test_cases = [
    {
        "text": "Müştərilərimizə ən yaxşı xidmət göstəririk!",
        "image": "https://source.unsplash.com/1200x1200/?business,office"
    },
    {
        "text": "Öyrənmək və inkişaf etmək üçün buradayıq",
        "image": "https://source.unsplash.com/1200x1200/?technology,modern"
    },
    {
        "text": "Şirkətimiz çox peşəkar və etibarlıdır",
        "image": "https://source.unsplash.com/1200x1200/?team,success"
    },
]

print("\n🧪 Generating 3 test images...\n")

for idx, test_data in enumerate(test_cases, 1):
    print(f"{'='*70}")
    print(f"TEST {idx}/3")
    print(f"{'='*70}")
    
    print(f"\n📝 Text: {test_data['text']}")
    print(f"🖼️  Background: {test_data['image'][:50]}...")
    
    # URL encode
    encoded_text = quote(test_data['text'], safe='')
    encoded_image = quote(test_data['image'], safe='')
    
    # Build Placid URL
    placid_url = (
        f"https://api.placid.app/u/{PLACID_TEMPLATE}"
        f"?text[text]={encoded_text}"
        f"&image[image]={encoded_image}"
    )
    
    print(f"\n✅ Placid URL Generated:")
    print(f"   {placid_url}")
    print(f"\n📸 This URL IS the image - just open it in browser!")
    print(f"   Or use in <img src=\"...\"> tag")
    print()

print("=" * 70)
print("\n🎉 DONE! Copy any URL above and open in browser!")
print("\n✨ Benefits of URL API:")
print("   ✅ No authentication needed")
print("   ✅ No POST requests")
print("   ✅ No 'modifiable' settings required")
print("   ✅ Works immediately")
print("   ✅ Just construct URL with query params")
print("\n💡 Each URL will generate a DIFFERENT image!")
print("=" * 70)





