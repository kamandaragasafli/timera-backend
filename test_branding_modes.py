#!/usr/bin/env python
"""
Test Branding Modes: Standard vs Custom
Tests the new branding mode functionality
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialai_backend.settings')
django.setup()

from accounts.models import CompanyProfile
from posts.branding import ImageBrandingService
from PIL import Image


def test_branding_modes():
    """Test Standard vs Custom branding modes"""
    print("\n" + "="*70)
    print("BRANDING MODES TEST: Standard vs Custom")
    print("="*70)
    
    profile = CompanyProfile.objects.first()
    
    if not profile:
        print("\n⚠️  No company profile found. Please create one first.")
        return False
    
    print(f"\n📋 Testing with profile: {profile.company_name}")
    
    # Test Standard Mode
    print("\n" + "-"*70)
    print("TEST 1: STANDARD MODE")
    print("-"*70)
    
    profile.branding_mode = 'standard'
    profile.logo_position = 'top-left'  # Should be ignored
    profile.logo_size_percent = 20  # Should be ignored
    profile.save()
    
    service = ImageBrandingService(profile)
    
    print(f"✅ Mode: {service.branding_mode}")
    print(f"✅ Position (should be bottom-right): {service.logo_position}")
    print(f"✅ Size (should be 5): {service.logo_size_percent}%")
    print(f"✅ Padding (should be 28): {service.padding}px")
    
    assert service.branding_mode == 'standard', "Mode should be standard"
    assert service.logo_position == 'bottom-right', "Standard mode should force bottom-right"
    assert service.logo_size_percent == 5, "Standard mode should force 5%"
    assert service.padding == 28, "Standard mode should use 28px padding"
    
    print("\n✅ PASS: Standard mode applies fixed settings correctly")
    
    # Test Custom Mode
    print("\n" + "-"*70)
    print("TEST 2: CUSTOM MODE")
    print("-"*70)
    
    profile.branding_mode = 'custom'
    profile.logo_position = 'middle-top'
    profile.logo_size_percent = 12
    profile.save()
    
    service = ImageBrandingService(profile)
    
    print(f"✅ Mode: {service.branding_mode}")
    print(f"✅ Position (should be middle-top): {service.logo_position}")
    print(f"✅ Size (should be 12): {service.logo_size_percent}%")
    print(f"✅ Padding (should be 40): {service.padding}px")
    
    assert service.branding_mode == 'custom', "Mode should be custom"
    assert service.logo_position == 'middle-top', "Custom mode should use configured position"
    assert service.logo_size_percent == 12, "Custom mode should use configured size"
    assert service.padding == 40, "Custom mode should use 40px padding"
    
    print("\n✅ PASS: Custom mode uses configured settings")
    
    # Test Size Clamping
    print("\n" + "-"*70)
    print("TEST 3: SIZE CLAMPING (Custom Mode)")
    print("-"*70)
    
    profile.branding_mode = 'custom'
    profile.logo_size_percent = 50  # Too large
    profile.save()
    
    service = ImageBrandingService(profile)
    print(f"✅ Input size: 50% → Clamped to: {service.logo_size_percent}%")
    assert service.logo_size_percent == 25, "Size should be clamped to max 25%"
    
    profile.logo_size_percent = 1  # Too small
    profile.save()
    
    service = ImageBrandingService(profile)
    print(f"✅ Input size: 1% → Clamped to: {service.logo_size_percent}%")
    assert service.logo_size_percent == 2, "Size should be clamped to min 2%"
    
    print("\n✅ PASS: Size clamping works correctly")
    
    # Test Backward Compatibility
    print("\n" + "-"*70)
    print("TEST 4: BACKWARD COMPATIBILITY (NULL mode)")
    print("-"*70)
    
    profile.branding_mode = None
    profile.save()
    
    service = ImageBrandingService(profile)
    print(f"✅ NULL mode treated as: {service.branding_mode}")
    assert service.branding_mode == 'standard', "NULL should default to standard"
    assert service.logo_position == 'bottom-right', "Should apply standard defaults"
    
    print("\n✅ PASS: Backward compatibility maintained")
    
    # Test New Positions
    print("\n" + "-"*70)
    print("TEST 5: NEW POSITION OPTIONS")
    print("-"*70)
    
    test_positions = ['middle-top', 'middle', 'bottom-left', 'top-right']
    
    for pos in test_positions:
        profile.branding_mode = 'custom'
        profile.logo_position = pos
        profile.save()
        
        service = ImageBrandingService(profile)
        
        # Test position calculation
        base_size = (1000, 1000)
        logo_size = (100, 50)
        x, y = service._calculate_logo_position(base_size, logo_size, pos, 40)
        
        print(f"✅ Position '{pos}': x={x}, y={y}")
        
        # Verify calculations
        if pos == 'middle-top':
            assert x == 450, f"middle-top X should be centered: {x}"
            assert y == 40, f"middle-top Y should be at top padding: {y}"
        elif pos == 'middle':
            assert x == 450, f"middle X should be centered: {x}"
            assert y == 475, f"middle Y should be centered: {y}"
    
    print("\n✅ PASS: All position options work correctly")
    
    return True


def test_api_compatibility():
    """Test that new fields are in serializer"""
    print("\n" + "="*70)
    print("API COMPATIBILITY TEST")
    print("="*70)
    
    from accounts.serializers import CompanyProfileSerializer
    
    serializer = CompanyProfileSerializer()
    fields = serializer.get_fields()
    
    required_fields = ['branding_mode', 'logo_position', 'logo_size_percent', 'slogan', 'branding_enabled']
    
    print("\n📋 Checking serializer fields...")
    for field in required_fields:
        if field in fields:
            print(f"✅ {field}: Present")
        else:
            print(f"❌ {field}: MISSING")
            return False
    
    print("\n✅ PASS: All branding fields in serializer")
    return True


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("BRANDING MODES V2 TEST SUITE")
    print("="*70)
    
    results = {
        'Branding Modes': test_branding_modes(),
        'API Compatibility': test_api_compatibility(),
    }
    
    print("\n" + "="*70)
    print("TEST RESULTS SUMMARY")
    print("="*70)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r)
    
    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\n🎉 All tests passed! Branding V2 is ready to use.")
    
    print("\n" + "="*70)
    print("USAGE EXAMPLES")
    print("="*70)
    print("""
📋 Standard Mode (Default):
   profile.branding_mode = 'standard'
   profile.save()
   # Logo: bottom-right, 5% size, 28px padding
   # Ignores logo_position and logo_size_percent settings

🎨 Custom Mode:
   profile.branding_mode = 'custom'
   profile.logo_position = 'middle-top'  # or 'middle', 'bottom-left', etc.
   profile.logo_size_percent = 12  # 2-25% range
   profile.save()
   # Uses configured position and size

🔄 Via API:
   PATCH /api/auth/company-profile/
   {
     "branding_mode": "custom",
     "logo_position": "middle-top",
     "logo_size_percent": 15
   }

📍 Available Positions:
   - bottom-left, bottom-right (corners)
   - top-left, top-right (corners)  
   - middle-top (centered horizontally, top)
   - middle (full center)

💡 Size Constraints:
   - Custom mode: 2-25%
   - Standard mode: Always 5% (ignored if configured differently)
    """)


if __name__ == '__main__':
    main()

