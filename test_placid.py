#!/usr/bin/env python
"""
Test Placid API Integration
This script tests the Placid API connection and template structure
"""

import requests
import json

# Your Placid credentials
PLACID_API_KEY = "placid-sqwemacv5a66owi2-gh5coisg2xzmtcuy"
PLACID_TEMPLATE = "xiu3ycxggcmja"
BASE_URL = "https://api.placid.app/api/rest"

headers = {
    'Authorization': f'Bearer {PLACID_API_KEY}',
    'Content-Type': 'application/json'
}

print("🧪 Testing Placid API Integration\n")
print("=" * 60)

# Test 1: Check API connection
print("\n1️⃣  Testing API Connection...")
try:
    response = requests.get(
        f"{BASE_URL}/templates",
        headers=headers,
        timeout=10
    )
    
    if response.status_code == 200:
        print("✅ API connection successful!")
        templates = response.json().get('data', [])
        print(f"📋 Found {len(templates)} templates in your account")
    else:
        print(f"❌ API Error: {response.status_code}")
        print(f"Response: {response.text}")
except Exception as e:
    print(f"❌ Connection failed: {e}")

# Test 2: Get template details
print(f"\n2️⃣  Getting template details for: {PLACID_TEMPLATE}")
try:
    response = requests.get(
        f"{BASE_URL}/templates/{PLACID_TEMPLATE}",
        headers=headers,
        timeout=10
    )
    
    if response.status_code == 200:
        template = response.json()
        print("✅ Template found!")
        print(f"\n📝 Template Details:")
        print(f"   Name: {template.get('name', 'N/A')}")
        print(f"   UUID: {template.get('uuid', 'N/A')}")
        
        # Show available layers
        layers = template.get('layers', [])
        print(f"\n🎨 Available Layers ({len(layers)}):")
        for layer in layers:
            layer_name = layer.get('name', 'unnamed')
            layer_type = layer.get('type', 'unknown')
            print(f"   • {layer_name} (type: {layer_type})")
        
        # Show template JSON structure
        print(f"\n📄 Full Template Structure:")
        print(json.dumps(template, indent=2))
    else:
        print(f"❌ Template Error: {response.status_code}")
        print(f"Response: {response.text}")
except Exception as e:
    print(f"❌ Failed to get template: {e}")

# Test 3: Try to create a test design
print(f"\n3️⃣  Creating a test design...")
try:
    # First, let's try with a simple request
    design_data = {
        "template_uuid": PLACID_TEMPLATE,
        "create_now": True,
        "layers": {
            # We'll populate this based on what we found
            # For now, using generic names
        }
    }
    
    print(f"📤 Sending request to create design...")
    print(f"Request data: {json.dumps(design_data, indent=2)}")
    
    response = requests.post(
        f"{BASE_URL}/images",
        headers=headers,
        json=design_data,
        timeout=20
    )
    
    print(f"📡 Response status: {response.status_code}")
    
    if response.status_code in [200, 201]:
        result = response.json()
        print("✅ Design created successfully!")
        print(f"\n🖼️  Design Details:")
        print(f"   Image URL: {result.get('image_url', 'N/A')}")
        print(f"   Polling URL: {result.get('polling_url', 'N/A')}")
        print(f"\n📄 Full Response:")
        print(json.dumps(result, indent=2))
    else:
        print(f"⚠️  Design creation response: {response.status_code}")
        print(f"Response: {response.text}")
except Exception as e:
    print(f"❌ Failed to create design: {e}")

print("\n" + "=" * 60)
print("✅ Test complete!")
print("\nNext steps:")
print("1. Check the layer names from the template details above")
print("2. Update the code in services.py with the correct layer names")
print("3. Test post generation with real data")





