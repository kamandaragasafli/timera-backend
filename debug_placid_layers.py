#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Debug Placid Layer Replacement
Shows exactly what we're sending and what we're getting back
"""

import requests
import json
import time

# Your Placid credentials
PLACID_API_KEY = "placid-sqwemacv5a66owi2-gh5coisg2xzmtcuy"
PLACID_TEMPLATE = "xiu3ycxggcmja"
BASE_URL = "https://api.placid.app/api/rest"

headers = {
    'Authorization': f'Bearer {PLACID_API_KEY}',
    'Content-Type': 'application/json; charset=utf-8'
}

print("🔍 Debugging Placid Layer Replacement\n")
print("=" * 70)

# First, let's check the template again
print("\n1️⃣  STEP 1: Checking template structure...")
try:
    response = requests.get(
        f"{BASE_URL}/templates/{PLACID_TEMPLATE}",
        headers=headers,
        timeout=10
    )
    
    if response.status_code == 200:
        template = response.json()
        print(f"✅ Template: {template.get('title', 'N/A')}")
        
        layers = template.get('layers', [])
        print(f"\n📋 Layers in template:")
        for layer in layers:
            print(f"   - Name: '{layer.get('name')}' | Type: {layer.get('type')}")
            # Check if there's any indication of placeholder status
            if 'placeholder' in layer:
                print(f"     Placeholder: {layer.get('placeholder')}")
            if 'editable' in layer:
                print(f"     Editable: {layer.get('editable')}")
    else:
        print(f"❌ Error fetching template: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 70)

# Now let's try sending data with different formats
test_cases = [
    {
        "name": "Test A: Standard format",
        "data": {
            "template_uuid": PLACID_TEMPLATE,
            "create_now": True,
            "layers": {
                "quote": "TEST A - This is test number ONE",
                "author": "Author A"
            }
        }
    },
    {
        "name": "Test B: Different structure",
        "data": {
            "template_uuid": PLACID_TEMPLATE,
            "layers": {
                "quote": {
                    "text": "TEST B - This is test number TWO"
                },
                "author": {
                    "text": "Author B"
                }
            }
        }
    },
    {
        "name": "Test C: Simple text only",
        "data": {
            "template_uuid": PLACID_TEMPLATE,
            "layers": {
                "quote": "TEST C - This is test number THREE",
                "author": "Author C"
            }
        }
    },
]

print("\n2️⃣  STEP 2: Testing different API formats...\n")

for idx, test in enumerate(test_cases, 1):
    print(f"\n{'='*70}")
    print(f"🧪 {test['name']}")
    print(f"{'='*70}")
    
    print(f"\n📤 Sending to Placid:")
    print(json.dumps(test['data'], indent=2, ensure_ascii=False))
    
    try:
        response = requests.post(
            f"{BASE_URL}/images",
            headers=headers,
            json=test['data'],
            timeout=20
        )
        
        print(f"\n📡 Response Status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            result = response.json()
            
            print(f"\n📦 Response Data:")
            print(f"   ID: {result.get('id')}")
            print(f"   Status: {result.get('status')}")
            print(f"   Image URL: {result.get('image_url', 'N/A')[:80]}...")
            
            if result.get('errors'):
                print(f"\n⚠️  Errors: {result.get('errors')}")
            
            # Show the image URL
            image_url = result.get('image_url', '')
            if image_url:
                print(f"\n📸 Open this URL to check if text changed:")
                print(f"   {image_url}")
                
                print(f"\n   Expected text: \"{test['data']['layers'].get('quote', 'N/A')[:50]}...\"")
        else:
            print(f"\n❌ Error Response:")
            print(response.text[:500])
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    # Wait a bit between requests
    if idx < len(test_cases):
        print(f"\n⏳ Waiting 3 seconds before next test...")
        time.sleep(3)

print("\n" + "=" * 70)
print("\n✅ DEBUG COMPLETE!")
print("\n📋 WHAT TO CHECK:")
print("\n1. Open each image URL above")
print("2. Check if you see:")
print("   - 'TEST A - This is test number ONE'")
print("   - 'TEST B - This is test number TWO'")
print("   - 'TEST C - This is test number THREE'")
print("\n3. If ALL show the SAME text:")
print("   → The template placeholders might not be properly configured")
print("   → Or there's an API format issue")
print("\n4. If each shows DIFFERENT text:")
print("   → It's working! The issue was elsewhere")
print("\n" + "=" * 70)

# Additional diagnostic
print("\n🔍 PLACID API DOCUMENTATION CHECK:")
print("\nAccording to Placid docs, layer replacement should be:")
print("""
{
  "template_uuid": "...",
  "layers": {
    "layer_name": "text value",
    "another_layer": "another value"
  }
}
""")
print("\nOr with properties:")
print("""
{
  "template_uuid": "...",
  "layers": {
    "layer_name": {
      "text": "value",
      "color": "#000000"
    }
  }
}
""")
print("\n💡 We're using the first format (simple text values)")
print("   If that doesn't work, we'll try the second format")





