#!/usr/bin/env python
"""
Test Branded Visual Composer
Tests the image branding functionality
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialai_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import CompanyProfile
from posts.branding import ImageBrandingService
from PIL import Image
import io

User = get_user_model()


def test_company_profile_branding_fields():
    """Test 1: Check if branding fields exist in CompanyProfile"""
    print("\n" + "="*60)
    print("TEST 1: Company Profile Branding Fields")
    print("="*60)
    
    # Check if fields exist
    fields_to_check = ['slogan', 'branding_enabled', 'logo_position', 'logo_size_percent']
    
    try:
        # Get first company profile or create test
        profile = CompanyProfile.objects.first()
        
        if not profile:
            print("\n⚠️  No company profiles found in database")
            print("   Create a company profile first")
            return False
        
        print(f"\n✅ Found company profile: {profile.company_name}")
        
        for field in fields_to_check:
            if hasattr(profile, field):
                value = getattr(profile, field)
                print(f"   ✅ {field}: {value}")
            else:
                print(f"   ❌ {field}: MISSING")
                return False
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def test_branding_service_initialization():
    """Test 2: Check if ImageBrandingService can be initialized"""
    print("\n" + "="*60)
    print("TEST 2: ImageBrandingService Initialization")
    print("="*60)
    
    try:
        profile = CompanyProfile.objects.first()
        
        if not profile:
            print("\n⚠️  No company profiles found")
            return False
        
        service = ImageBrandingService(profile)
        
        print(f"\n✅ Service initialized successfully")
        print(f"   Company: {profile.company_name}")
        print(f"   Branding Enabled: {service.branding_enabled}")
        print(f"   Logo: {service.logo}")
        print(f"   Slogan: {service.slogan or 'None'}")
        print(f"   Position: {service.logo_position}")
        print(f"   Logo Size: {service.logo_size_percent}%")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_create_sample_branded_image():
    """Test 3: Create a sample branded image"""
    print("\n" + "="*60)
    print("TEST 3: Create Sample Branded Image")
    print("="*60)
    
    try:
        profile = CompanyProfile.objects.filter(logo__isnull=False).first()
        
        if not profile:
            print("\n⚠️  No company profile with logo found")
            print("   Upload a logo to test branding")
            return False
        
        if not profile.logo:
            print("\n⚠️  Profile has no logo")
            return False
        
        print(f"\n✅ Found profile with logo: {profile.company_name}")
        print(f"   Logo path: {profile.logo.path}")
        
        # Create a simple test image (blue square)
        print("\n🎨 Creating test base image...")
        test_img = Image.new('RGB', (800, 800), color=(59, 130, 246))  # Blue
        
        # Save temporarily
        test_path = 'test_base_image.png'
        test_img.save(test_path)
        
        # Apply branding
        print("🎨 Applying branding...")
        service = ImageBrandingService(profile)
        branded_img = service.apply_branding(test_path)
        
        # Save result
        output_path = 'test_branded_output.png'
        branded_img.save(output_path)
        
        print(f"\n✅ Branded image created successfully!")
        print(f"   Output: {output_path}")
        print(f"   Size: {branded_img.size}")
        print(f"   Logo position: {profile.logo_position}")
        print(f"   Slogan: {profile.slogan or 'None'}")
        
        # Clean up test image
        if os.path.exists(test_path):
            os.remove(test_path)
        
        print(f"\n📁 Check the file: {output_path}")
        print("   Open it to see the logo and slogan overlay!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_endpoint_exists():
    """Test 4: Check if API endpoint is registered"""
    print("\n" + "="*60)
    print("TEST 4: API Endpoint Registration")
    print("="*60)
    
    try:
        from django.urls import reverse, NoReverseMatch
        from posts.views import ApplyBrandingView
        
        print("\n✅ ApplyBrandingView imported successfully")
        
        # Try to get URL pattern
        try:
            # Note: This will fail without an actual post_id, but we just want to check the pattern exists
            url = reverse('apply_branding', kwargs={'post_id': '00000000-0000-0000-0000-000000000000'})
            print(f"✅ URL pattern registered: {url}")
        except NoReverseMatch as e:
            print(f"❌ URL pattern not found: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def test_automatic_branding_integration():
    """Test 5: Check if automatic branding is integrated with post generation"""
    print("\n" + "="*60)
    print("TEST 5: Automatic Branding Integration")
    print("="*60)
    
    try:
        # Check if the import works
        from posts.services import PostGenerationService
        
        print("\n✅ PostGenerationService imported successfully")
        
        # Check if branding import exists in services.py
        with open('posts/services.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'from .branding import ImageBrandingService' in content:
                print("✅ Branding service imported in PostGenerationService")
            else:
                print("⚠️  Branding import not found")
                return False
            
            if 'branding_service = ImageBrandingService' in content:
                print("✅ Branding application code found")
            else:
                print("⚠️  Branding application code not found")
                return False
        
        print("\n✅ Automatic branding integration verified")
        print("   Images will be automatically branded during AI generation")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("BRANDED VISUAL COMPOSER TEST SUITE")
    print("="*60)
    
    results = {
        'Branding Fields': test_company_profile_branding_fields(),
        'Service Initialization': test_branding_service_initialization(),
        'Sample Branded Image': test_create_sample_branded_image(),
        'API Endpoint': test_api_endpoint_exists(),
        'Auto Integration': test_automatic_branding_integration(),
    }
    
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r)
    
    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    
    print("\n" + "="*60)
    print("USAGE INSTRUCTIONS")
    print("="*60)
    print("""
📋 Company Profile Setup:
   1. Upload company logo in admin or via API
   2. Set slogan (optional but recommended)
   3. Configure logo position (default: bottom-left)
   4. Set logo size (default: 18% of image width)
   5. Enable branding (enabled by default)

🎨 Automatic Branding (AI Posts):
   - Generate posts with AI
   - Branding applied automatically to all generated images
   - Logo and slogan overlaid as configured

🖼️  Manual Branding (Existing Posts):
   POST /api/posts/{post_id}/apply-branding/
   - Applies branding to any post with an image
   - Returns updated post with branded image

📐 Branding Specifications:
   - Logo: 18% of image width (configurable 5-40%)
   - Position: 40px padding from edges
   - Slogan: 25% of logo height
   - Text: White with soft shadow for readability
   - Spacing: 20-30px between slogan and logo
    """)
    
    if os.path.exists('test_branded_output.png'):
        print("\n🎉 Sample branded image created: test_branded_output.png")
        print("   Open this file to see the branding effect!")


if __name__ == '__main__':
    main()

