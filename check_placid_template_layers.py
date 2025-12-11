#!/usr/bin/env python
"""
Check Placid Template Layers
Shows all layers in your template including image layers
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

print("🔍 Checking Placid Template Layers\n")
print("=" * 70)

# Get template details
try:
    response = requests.get(
        f"{BASE_URL}/templates/{PLACID_TEMPLATE}",
        headers=headers,
        timeout=10
    )
    
    if response.status_code == 200:
        template = response.json()
        
        print(f"\n📝 Template: {template.get('title', 'N/A')}")
        print(f"🆔 UUID: {template.get('uuid', 'N/A')}")
        print(f"📐 Size: {template.get('width')}x{template.get('height')}")
        
        layers = template.get('layers', [])
        print(f"\n🎨 Total Layers: {len(layers)}")
        print("\n" + "=" * 70)
        
        text_layers = []
        image_layers = []
        other_layers = []
        
        for idx, layer in enumerate(layers, 1):
            layer_name = layer.get('name', 'unnamed')
            layer_type = layer.get('type', 'unknown')
            
            print(f"\n{idx}. Layer Name: '{layer_name}'")
            print(f"   Type: {layer_type}")
            
            if layer_type == 'text':
                text_layers.append(layer_name)
                print(f"   ✍️  TEXT LAYER - Can replace with dynamic text")
            elif layer_type == 'image':
                image_layers.append(layer_name)
                print(f"   🖼️  IMAGE LAYER - Can replace with dynamic image URL! ⭐")
            else:
                other_layers.append(layer_name)
                print(f"   🔷 {layer_type.upper()} LAYER")
            
            # Show more details if available
            if 'text' in layer:
                print(f"   Current text: {layer.get('text', '')[:50]}...")
            if 'src' in layer:
                print(f"   Current image: {layer.get('src', '')[:60]}...")
        
        print("\n" + "=" * 70)
        print("\n📊 SUMMARY:")
        print(f"\n✍️  Text Layers ({len(text_layers)}):")
        for name in text_layers:
            print(f"   - {name}")
        
        print(f"\n🖼️  Image Layers ({len(image_layers)}):")
        if image_layers:
            for name in image_layers:
                print(f"   - {name} ⭐ YOU CAN USE THIS!")
        else:
            print("   ⚠️  No image layers found!")
            print("   → You need to ADD an image layer to your template")
        
        if other_layers:
            print(f"\n🔷 Other Layers ({len(other_layers)}):")
            for name in other_layers:
                print(f"   - {name}")
        
        print("\n" + "=" * 70)
        print("\n💡 WHAT TO DO NEXT:\n")
        
        if image_layers:
            print("✅ GREAT! Your template HAS image layers!")
            print(f"\n📝 Update your code in services.py line ~290:")
            print("\n   layers = {")
            print('       "quote": quote_text,')
            print('       "author": author_text,')
            for img_layer in image_layers:
                print(f'       "{img_layer}": background_image_url,  # ⭐ ADD THIS!')
            print("   }")
        else:
            print("⚠️  NO image layers found in your template!")
            print("\n📝 Two options:")
            print("\n   Option A: Add image layer to existing template")
            print("   1. Go to: https://placid.app/templates")
            print("   2. Edit template: xiu3ycxggcmja")
            print("   3. Add an 'Image' element")
            print("   4. Name it 'background' or 'photo'")
            print("   5. Make it a placeholder")
            print("   6. Position behind text")
            print("\n   Option B: Create new template with image placeholder")
            print("   1. Create new template")
            print("   2. Add image element as background")
            print("   3. Add text elements for quote/author")
            print("   4. Make all dynamic")
            print("   5. Use new template UUID")
        
        print("\n" + "=" * 70)
        
    else:
        print(f"❌ API Error: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")

print("\n✅ Check complete!")





