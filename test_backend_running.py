"""
Backend server-in işlədiyini yoxla
"""
import requests
import sys

def check_backend():
    """Backend server-in işlədiyini yoxla"""
    print("🔍 Backend server yoxlanışı...")
    print("="*60)
    
    try:
        response = requests.get("http://localhost:8000/api/posts/", timeout=5)
        print(f"✅ Backend server işləyir!")
        print(f"   Status: {response.status_code}")
        print(f"   URL: http://localhost:8000")
        
        if response.status_code == 401:
            print("   ✅ Authentication tələb olunur (normal)")
        elif response.status_code == 200:
            print("   ✅ OK")
        
        return True
    except requests.exceptions.ConnectionError:
        print("❌ Backend server işləmir!")
        print("   Server başlat:")
        print("   cd C:\\Users\\User\\Desktop\\timera-backend-main")
        print("   .\\venv\\Scripts\\Activate.ps1")
        print("   python manage.py runserver")
        return False
    except Exception as e:
        print(f"❌ Xəta: {e}")
        return False

if __name__ == "__main__":
    success = check_backend()
    sys.exit(0 if success else 1)

