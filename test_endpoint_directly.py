"""
Direct endpoint test - check if apply-branding endpoint is accessible
"""
import requests
import sys

BASE_URL = "http://localhost:8000"

def test_endpoint_directly():
    """Test apply-branding endpoint directly"""
    print("🔍 Testing apply-branding endpoint directly...")
    print("="*60)
    
    # Use a test UUID
    test_uuid = "12345678-1234-1234-1234-123456789012"
    endpoint = f"/api/posts/{test_uuid}/apply-branding/"
    url = f"{BASE_URL}{endpoint}"
    
    print(f"📍 Testing URL: {url}")
    
    try:
        # Test with OPTIONS (CORS preflight) - doesn't require auth
        response = requests.options(url, timeout=5)
        print(f"✅ OPTIONS request successful!")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 404:
            print("❌ ENDPOINT NOT FOUND (404)")
            print("   Problem: URL pattern sırası və ya endpoint qeydiyyata alınmayıb")
            return False
        elif response.status_code in [200, 405]:  # 405 = Method Not Allowed (normal, endpoint var amma POST tələb edir)
            print("✅ ENDPOINT EXISTS!")
            print("   404 problem frontend-də URL-dir və ya backend server restart olunmayıb")
            return True
        elif response.status_code == 401:
            print("✅ ENDPOINT EXISTS! (401 = auth required, normal)")
            return True
        else:
            print(f"⚠️  Unexpected status: {response.status_code}")
            return True
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Backend server işləmir!")
        print("   Server başlat: python manage.py runserver")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_endpoint_directly()
    sys.exit(0 if success else 1)

