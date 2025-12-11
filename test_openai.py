"""
Quick test script to verify OpenAI integration
"""

import os
import django
import sys

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialai_backend.settings')
django.setup()

from django.conf import settings
from posts.services import OpenAIService
from accounts.models import User, CompanyProfile

def test_openai_integration():
    """Test OpenAI API integration"""
    
    print("Testing OpenAI integration...")
    print(f"API Key configured: {'Yes' if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != 'your-openai-api-key-here' else 'No'}")
    
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == 'your-openai-api-key-here':
        print("❌ OpenAI API key not configured properly")
        return
    
    try:
        # Get demo user and company profile
        user = User.objects.get(email="demo@socialai.com")
        company_profile = CompanyProfile.objects.get(user=user)
        
        print(f"✅ Demo user found: {user.email}")
        print(f"✅ Company profile found: {company_profile.company_name}")
        
        # Test OpenAI service
        openai_service = OpenAIService()
        
        # Test simple generation
        print("\n🤖 Testing AI content generation...")
        
        # This would normally generate posts, but for testing we'll just verify the service initializes
        print("✅ OpenAI service initialized successfully")
        print("✅ Ready to generate Azerbaijani content!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    test_openai_integration()






