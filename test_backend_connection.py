"""
Backend Connection Test Script
Frontend ilə bağlantı problemlərini yoxlamaq üçün
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_endpoint(method, endpoint, headers=None, data=None):
    """Test endpoint və nəticəni göstər"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=5)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=5)
        else:
            print(f"❌ Naməlum method: {method}")
            return False
        
        print(f"\n{'='*60}")
        print(f"📍 {method} {endpoint}")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   ✅ OK")
            try:
                result = response.json()
                print(f"   Response: {json.dumps(result, indent=2, ensure_ascii=False)[:200]}...")
            except:
                print(f"   Response: {response.text[:200]}...")
            return True
        elif response.status_code == 401:
            print(f"   ⚠️  Unauthorized - JWT token lazımdır")
            print(f"   Response: {response.text[:200]}")
            return False
        elif response.status_code == 404:
            print(f"   ❌ Not Found - Endpoint mövcud deyil")
            print(f"   Response: {response.text[:200]}")
            return False
        elif response.status_code == 500:
            print(f"   ❌ Server Error - Backend-də xəta var")
            print(f"   Response: {response.text[:500]}")
            return False
        else:
            print(f"   ⚠️  Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"\n{'='*60}")
        print(f"📍 {method} {endpoint}")
        print(f"   ❌ Connection Error!")
        print(f"   Backend server işləmir!")
        print(f"   Server başlat: python manage.py runserver")
        return False
    except requests.exceptions.Timeout:
        print(f"\n{'='*60}")
        print(f"📍 {method} {endpoint}")
        print(f"   ❌ Timeout - Server cavab vermir")
        return False
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"📍 {method} {endpoint}")
        print(f"   ❌ Error: {str(e)}")
        return False

def main():
    print("🔍 Backend Connection Test")
    print("="*60)
    
    # Test 1: Server işləyir?
    print("\n1️⃣ Server Status Yoxlanışı:")
    test_endpoint("GET", "/api/posts/")
    
    # Test 2: CORS headers
    print("\n2️⃣ CORS Headers Yoxlanışı:")
    try:
        response = requests.options(f"{BASE_URL}/api/posts/", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        }, timeout=5)
        print(f"   CORS Preflight Status: {response.status_code}")
        cors_headers = {k: v for k, v in response.headers.items() if 'access-control' in k.lower()}
        if cors_headers:
            print(f"   ✅ CORS Headers: {cors_headers}")
        else:
            print(f"   ⚠️  CORS Headers tapılmadı")
    except Exception as e:
        print(f"   ❌ CORS test failed: {str(e)}")
    
    # Test 3: Yeni endpoint-lər
    print("\n3️⃣ Yeni Endpoint-lər Yoxlanışı:")
    
    # Test endpoints (auth olmadan 401 gözləyirik)
    endpoints = [
        ("GET", "/api/posts/"),
        ("GET", "/api/social-accounts/"),
        ("GET", "/api/meta-ads/accounts/"),
        ("GET", "/api/meta-ads/campaigns/"),
        ("POST", "/api/ai/create-ad-creative/"),
        ("POST", "/api/posts/generate/"),
    ]
    
    results = []
    for method, endpoint in endpoints:
        result = test_endpoint(method, endpoint)
        results.append((endpoint, result))
    
    # Test 4: Admin panel
    print("\n4️⃣ Admin Panel Yoxlanışı:")
    test_endpoint("GET", "/admin/")
    
    # Summary
    print("\n" + "="*60)
    print("📊 Xülasə:")
    print("="*60)
    
    for endpoint, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {endpoint}")
    
    print("\n" + "="*60)
    print("💡 Qeydlər:")
    print("   - 401 Unauthorized = Normal (JWT token lazımdır)")
    print("   - 404 Not Found = Endpoint mövcud deyil")
    print("   - Connection Error = Server işləmir")
    print("="*60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test dayandırıldı")
        sys.exit(0)

