#!/usr/bin/env python
"""
Test script for AI Helper endpoints
Run this after deployment to verify everything works
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialai_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from ai_helper.views import GenerateContentView, OptimizeForPlatformView

User = get_user_model()

def test_language_detection():
    """Test language detection function"""
    from ai_helper.views import detect_language
    
    print("🧪 Testing language detection...")
    
    # Test Azerbaijani
    az_text = "Biznesinizi təsvir edin"
    assert detect_language(az_text) == 'az', "Failed to detect Azerbaijani"
    print("✅ Azerbaijani detection works")
    
    # Test English
    en_text = "Describe your business"
    assert detect_language(en_text) == 'en', "Failed to detect English"
    print("✅ English detection works")
    
    print()


def test_generate_content_view():
    """Test the content generation endpoint"""
    print("🧪 Testing content generation endpoint...")
    
    factory = APIRequestFactory()
    
    # Create or get a test user
    user, _ = User.objects.get_or_create(
        email='test@example.com',
        defaults={'password': 'testpass123'}
    )
    
    # Test Azerbaijani request
    request = factory.post('/api/ai/generate-content/', {
        'prompt': 'Texnologiya şirkəti üçün qısa biznes təsviri yazın',
        'content_type': 'company_field_suggestion'
    }, format='json')
    request.user = user
    
    view = GenerateContentView.as_view()
    response = view(request)
    
    if response.status_code == 200:
        print(f"✅ Status: {response.status_code}")
        print(f"✅ Language detected: {response.data.get('language')}")
        print(f"✅ Content length: {response.data.get('char_count')} characters")
        print(f"✅ Sample output: {response.data.get('content')[:100]}...")
    else:
        print(f"❌ Failed with status: {response.status_code}")
        print(f"Error: {response.data}")
        return False
    
    print()
    return True


def test_optimize_platform_view():
    """Test the platform optimization endpoint"""
    print("🧪 Testing platform optimization endpoint...")
    
    factory = APIRequestFactory()
    
    # Create or get a test user
    user, _ = User.objects.get_or_create(
        email='test@example.com',
        defaults={'password': 'testpass123'}
    )
    
    # Test request
    request = factory.post('/api/ai/optimize-platform/', {
        'content': 'Yeni məhsulumuz artıq bazarda!',
        'platform': 'instagram'
    }, format='json')
    request.user = user
    
    view = OptimizeForPlatformView.as_view()
    response = view(request)
    
    if response.status_code == 200:
        print(f"✅ Status: {response.status_code}")
        print(f"✅ Language detected: {response.data.get('language')}")
        print(f"✅ Optimized content: {response.data.get('content')}")
    else:
        print(f"❌ Failed with status: {response.status_code}")
        print(f"Error: {response.data}")
        return False
    
    print()
    return True


def main():
    print("=" * 60)
    print("🤖 AI Helper Endpoint Test Suite")
    print("=" * 60)
    print()
    
    # Check OpenAI API key
    from django.conf import settings
    if not hasattr(settings, 'OPENAI_API_KEY') or not settings.OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY is not configured!")
        print("Please set OPENAI_API_KEY in your environment or local.env file")
        return
    
    print(f"✅ OpenAI API Key is configured: {settings.OPENAI_API_KEY[:20]}...")
    print()
    
    # Run tests
    test_language_detection()
    
    try:
        success1 = test_generate_content_view()
        success2 = test_optimize_platform_view()
        
        print("=" * 60)
        if success1 and success2:
            print("🎉 All tests passed! AI endpoints are working correctly.")
        else:
            print("⚠️  Some tests failed. Check the errors above.")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()



