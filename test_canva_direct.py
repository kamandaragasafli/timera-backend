#!/usr/bin/env python
"""
Test Canva API Direct Connection
Tests if Canva credentials work for server-to-server API calls
"""

import requests
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Load Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialai_backend.settings')
import django
django.setup()

from django.conf import settings

def test_canva_api():
    """Test Canva API with direct credentials"""
    
    print("🧪 Testing Canva API Connection")
    print("=" * 60)
    
    CLIENT_ID = settings.CANVA_CLIENT_ID
    CLIENT_SECRET = settings.CANVA_CLIENT_SECRET
    
    print(f"📋 Client ID: {CLIENT_ID[:15]}...")
    print(f"🔐 Client Secret: {CLIENT_SECRET[:20]}...")
    print()
    
    # Test 1: User Info Endpoint
    print("Test 1: Get User Info (OAuth endpoint)")
    print("-" * 60)
    
    headers = {
        'Authorization': f'Bearer {CLIENT_ID}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(
            'https://api.canva.com/rest/v1/users/me',
            headers=headers,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        
        if response.status_code == 200:
            print("✅ User info retrieved successfully!")
        else:
            print(f"⚠️  Got {response.status_code} - This might be expected")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print()
    
    # Test 2: Create Design Endpoint
    print("Test 2: Create Design")
    print("-" * 60)
    
    design_data = {
        "title": "Test Design from SocialAI",
        "design_type": "SocialMediaPost",
        "dimensions": {
            "width": 1080,
            "height": 1080,
            "unit": "px"
        }
    }
    
    try:
        response = requests.post(
            'https://api.canva.com/rest/v1/designs',
            headers=headers,
            json=design_data,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        if response.status_code in [200, 201]:
            print("✅ Design created successfully!")
            design = response.json()
            print(f"Design ID: {design.get('design', {}).get('id', 'N/A')}")
        else:
            print(f"⚠️  Got {response.status_code}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print()
    
    # Test 3: Get Templates
    print("Test 3: Get Templates")
    print("-" * 60)
    
    try:
        response = requests.get(
            'https://api.canva.com/rest/v1/templates',
            headers=headers,
            params={'search': 'social media', 'limit': 5},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        if response.status_code == 200:
            print("✅ Templates retrieved successfully!")
        else:
            print(f"⚠️  Got {response.status_code}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print()
    print("=" * 60)
    print("🏁 Testing Complete")
    print()
    print("📊 Summary:")
    print("  - If you see 401/403: Credentials might need OAuth flow")
    print("  - If you see 200: API is working! ✅")
    print("  - If you see 404: Endpoint might be different")
    print()
    print("💡 Note: Even if tests fail, the app works with placeholders!")

if __name__ == '__main__':
    test_canva_api()





