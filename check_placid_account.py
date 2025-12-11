#!/usr/bin/env python
"""
Check Placid Account and Template Permissions
"""

import requests
import json

PLACID_API_KEY = "placid-sqwemacv5a66owi2-gh5coisg2xzmtcuy"
BASE_URL = "https://api.placid.app/api/rest"

headers = {
    'Authorization': f'Bearer {PLACID_API_KEY}',
    'Content-Type': 'application/json'
}

print("🔍 Checking Placid Account Status\n")
print("=" * 70)

# Check if there's an account/user endpoint
print("\n1️⃣  Checking API access...")
try:
    # Try to get templates (this should work)
    response = requests.get(
        f"{BASE_URL}/templates",
        headers=headers,
        timeout=10
    )
    
    print(f"✅ API Key is valid (Status: {response.status_code})")
    
    if response.status_code == 200:
        data = response.json()
        templates = data.get('data', [])
        print(f"📋 You have {len(templates)} templates")
        
        print("\n📝 Your Templates:")
        for t in templates:
            print(f"\n   Template: {t.get('title', 'Untitled')}")
            print(f"   UUID: {t.get('uuid')}")
            print(f"   Layers: {len(t.get('layers', []))}")
            for layer in t.get('layers', []):
                print(f"      - {layer.get('name')} ({layer.get('type')})")

except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 70)
print("\n2️⃣  Checking New Template Details...")

NEW_TEMPLATE = "sxaa11eh8z4tf"

try:
    response = requests.get(
        f"{BASE_URL}/templates/{NEW_TEMPLATE}",
        headers=headers,
        timeout=10
    )
    
    if response.status_code == 200:
        template = response.json()
        
        print(f"\n✅ Template Found: {template.get('title')}")
        print(f"\n📦 Full Template JSON:")
        print(json.dumps(template, indent=2))
        
        # Check if there's any indication of editability
        layers = template.get('layers', [])
        print(f"\n🔍 Layer Analysis:")
        for layer in layers:
            print(f"\n   Layer: {layer.get('name')}")
            print(f"   Type: {layer.get('type')}")
            print(f"   All properties: {json.dumps(layer, indent=4)}")

except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 70)
print("\n3️⃣  Testing Simple Text Replacement...")

try:
    test_data = {
        "template_uuid": NEW_TEMPLATE,
        "layers": {
            "text": "SIMPLE TEST - Can you see this text?"
        }
    }
    
    print(f"\n📤 Sending minimal request:")
    print(json.dumps(test_data, indent=2))
    
    response = requests.post(
        f"{BASE_URL}/images",
        headers=headers,
        json=test_data,
        timeout=20
    )
    
    print(f"\n📡 Response: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n📦 Response Data:")
        print(json.dumps(result, indent=2))
        
        if result.get('image_url'):
            print(f"\n📸 Image URL:")
            print(f"   {result.get('image_url')}")
            print(f"\n   Expected text: 'SIMPLE TEST - Can you see this text?'")

except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 70)
print("\n💡 IMPORTANT QUESTIONS:")
print("\n1. When you created the NEW template, did you:")
print("   ☐ Add a text element")
print("   ☐ Name it exactly 'text'")
print("   ☐ Enable 'Modifiable via API' or 'Dynamic' checkbox")
print("   ☐ Save/Publish the template")
print("\n2. What plan are you on?")
print("   - Free tier")
print("   - Starter")
print("   - Growth")
print("   - Enterprise")
print("\n3. Can you see a checkbox or toggle for 'API' or 'Dynamic' or 'Modifiable'")
print("   when you click on the text layer in the editor?")
print("\n" + "=" * 70)





