"""
Test branding endpoint
"""
import requests
import sys

BASE_URL = "http://localhost:8000"

def test_branding_endpoint():
    """Test branding endpoint exists"""
    print("🔍 Testing branding endpoint...")
    print("="*60)
    
    # Test 1: Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/api/posts/", timeout=5)
        print(f"✅ Server işləyir (Status: {response.status_code})")
    except requests.exceptions.ConnectionError:
        print("❌ Backend server işləmir!")
        print("   Server başlat: python manage.py runserver")
        return False
    except Exception as e:
        print(f"❌ Server xətası: {e}")
        return False
    
    # Test 2: Check endpoint with OPTIONS (CORS preflight)
    test_post_id = "00000000-0000-0000-0000-000000000000"  # Fake UUID for testing
    endpoint = f"/api/posts/{test_post_id}/apply-branding/"
    
    try:
        response = requests.options(f"{BASE_URL}{endpoint}", timeout=5)
        print(f"✅ Endpoint mövcuddur (OPTIONS Status: {response.status_code})")
        print(f"   URL: {BASE_URL}{endpoint}")
        
        # Check CORS headers
        cors_headers = {k: v for k, v in response.headers.items() if 'access-control' in k.lower()}
        if cors_headers:
            print(f"   CORS Headers: {cors_headers}")
        
        return True
    except requests.exceptions.ConnectionError:
        print("❌ Endpoint-ə qoşula bilmədi")
        return False
    except Exception as e:
        print(f"⚠️  Endpoint test xətası: {e}")
        return False

if __name__ == "__main__":
    success = test_branding_endpoint()
    sys.exit(0 if success else 1)
