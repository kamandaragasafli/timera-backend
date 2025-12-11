#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test Placid with Azerbaijani Characters
Tests: ö ğ ü ç ş ə
"""

import requests
import json

# Your Placid credentials
PLACID_API_KEY = "placid-sqwemacv5a66owi2-gh5coisg2xzmtcuy"
PLACID_TEMPLATE = "xiu3ycxggcmja"
BASE_URL = "https://api.placid.app/api/rest"

headers = {
    'Authorization': f'Bearer {PLACID_API_KEY}',
    'Content-Type': 'application/json; charset=utf-8'
}

print("🇦🇿 Testing Azerbaijani Characters in Placid\n")
print("=" * 70)

# Test text with ALL Azerbaijani special characters
test_quotes = [
    "Müştərilərimizə ən yaxşı xidmət göstəririk",  # ü ş ə ə ı ş ö ö
    "Öyrənmək və inkişaf etmək üçün buradayıq",   # Ö ə ş ü ı
    "Şirkətimiz çox peşəkar və etibarlıdır",      # Ş ə ş ə
    "Biznesdə uğur əldə etməyiniz üçün",          # ə ə ü ü
    "Gələcək üçün böyük planlarımız var",         # ə ü ö ü
]

print("\n📝 Testing 5 different Azerbaijani texts...")
print("\nSpecial characters to test: ö ğ ü ç ş ə ı")
print("=" * 70)

for idx, quote_text in enumerate(test_quotes, 1):
    print(f"\n🧪 Test {idx}/5")
    print(f"Text: {quote_text}")
    
    # Check what characters are in the text
    special_chars = []
    for char in 'öğüçşəı':
        if char in quote_text.lower():
            special_chars.append(char)
    
    print(f"Contains: {', '.join(special_chars) if special_chars else 'no special chars'}")
    
    try:
        design_data = {
            "template_uuid": PLACID_TEMPLATE,
            "create_now": True,
            "layers": {
                "quote": quote_text,
                "author": "Azərbaycan Şirkəti",  # Also with special chars
            }
        }
        
        print(f"📤 Sending to Placid API...")
        
        response = requests.post(
            f"{BASE_URL}/images",
            headers=headers,
            json=design_data,
            timeout=20
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            image_url = result.get('image_url', '')
            
            if image_url:
                print(f"✅ SUCCESS! Image generated!")
                print(f"🖼️  URL: {image_url}")
                print(f"\n📸 OPEN THIS URL to verify characters display correctly:")
                print(f"   {image_url}")
                
                if idx == 1:
                    print(f"\n⭐ IMPORTANT: Open this image and check:")
                    print(f"   - Are ö, ğ, ü, ç, ş, ə, ı visible?")
                    print(f"   - Do they look correct?")
                    print(f"   - Or do you see � (question marks/boxes)?")
            else:
                print(f"⚠️  No image URL returned")
                print(f"Response: {result}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text[:200]}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("-" * 70)

print("\n" + "=" * 70)
print("\n✅ TEST COMPLETE!")
print("\n📋 WHAT TO DO NEXT:")
print("\n1. Open the image URLs above in your browser")
print("2. Check if you see: ö ğ ü ç ş ə ı")
print("3. Tell me:")
print("   ✅ If characters look correct → We're good!")
print("   ❌ If you see ?, □, or � → We need to fix fonts")
print("\n" + "=" * 70)

print("\n🔍 ADDITIONAL INFO:")
print("\nAzerbaijani alphabet uses:")
print("- Standard Latin: a-z")
print("- Special characters: ə, ğ, ı, ö, ü, ç, ş")
print("\nThese are part of:")
print("- ✅ Unicode (UTF-8)")
print("- ✅ Latin Extended-A")
print("- ✅ Should work in most fonts")
print("\nIf they DON'T display:")
print("- Option 1: Change Placid template font to one that supports them")
print("- Option 2: Use font fallback in template")
print("- Option 3: Contact Placid support about font support")





