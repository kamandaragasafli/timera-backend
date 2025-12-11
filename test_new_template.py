#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test New Placid Template with Correct Layer Names
Template UUID: sxaa11eh8z4tf
Layers: "text" and "image"
"""

import requests
import json

# Your Placid credentials
PLACID_API_KEY = "placid-sqwemacv5a66owi2-gh5coisg2xzmtcuy"
PLACID_TEMPLATE = "sxaa11eh8z4tf"  # NEW TEMPLATE
BASE_URL = "https://api.placid.app/api/rest"

headers = {
    'Authorization': f'Bearer {PLACID_API_KEY}',
    'Content-Type': 'application/json; charset=utf-8'
}

print("🧪 Testing New Placid Template")
print("=" * 70)
print(f"Template UUID: {PLACID_TEMPLATE}")
print(f"Layer names: 'text' and 'image'")
print("=" * 70)

# Test with 3 different Azerbaijani texts and different background images
test_cases = [
    {
        "text": "Müştərilərimizə ən yaxşı xidmət göstəririk",
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

for idx, test_data in enumerate(test_cases, 1):
    print(f"\n{'='*70}")
    print(f"🧪 TEST {idx}/3")
    print(f"{'='*70}")
    
    print(f"\n📝 Text: {test_data['text']}")
    print(f"🖼️  Image: {test_data['image'][:50]}...")
    
    request_data = {
        "template_uuid": PLACID_TEMPLATE,
        "create_now": True,
        "layers": {
            "text": test_data['text'],
            "image": test_data['image']
        }
    }
    
    print(f"\n📤 Sending to Placid API...")
    print(json.dumps(request_data, indent=2, ensure_ascii=False))
    
    try:
        response = requests.post(
            f"{BASE_URL}/images",
            headers=headers,
            json=request_data,
            timeout=20
        )
        
        print(f"\n📡 Response Status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            result = response.json()
            
            print(f"\n✅ SUCCESS!")
            print(f"   Status: {result.get('status')}")
            print(f"   Image ID: {result.get('id')}")
            
            image_url = result.get('image_url', '')
            if image_url:
                print(f"\n📸 Generated Image:")
                print(f"   {image_url}")
                print(f"\n   👉 Open this URL to verify:")
                print(f"      1. Text changed to: \"{test_data['text'][:40]}...\"")
                print(f"      2. Background is different image")
                print(f"      3. Azerbaijani characters (ö, ü, ş, ə) display correctly")
            else:
                print(f"\n⚠️  Image still processing...")
                print(f"   Polling URL: {result.get('polling_url')}")
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(f"Response: {response.text[:300]}")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")

print("\n" + "=" * 70)
print("\n✅ TEST COMPLETE!")
print("\n📋 EXPECTED RESULTS:")
print("\n   ✅ Each image should show DIFFERENT text")
print("   ✅ Each image should have DIFFERENT background")
print("   ✅ Azerbaijani characters should be visible")
print("\n🎉 If all 3 images are different → SUCCESS!")
print("❌ If images are same → Template layers not properly configured")
print("\n" + "=" * 70)





