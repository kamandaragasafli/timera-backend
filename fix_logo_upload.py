#!/usr/bin/env python
"""
Check and Fix Logo Upload Issues
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialai_backend.settings')
django.setup()

from accounts.models import CompanyProfile
from django.conf import settings


def main():
    print("\n" + "="*70)
    print("LOGO UPLOAD DIAGNOSTIC")
    print("="*70)
    
    # Check media directories
    print("\n📁 Checking media directories...")
    
    media_root = settings.MEDIA_ROOT
    print(f"   MEDIA_ROOT: {media_root}")
    print(f"   MEDIA_URL: {settings.MEDIA_URL}")
    
    company_logos_dir = os.path.join(media_root, 'company_logos')
    
    if os.path.exists(company_logos_dir):
        print(f"   ✅ company_logos directory exists: {company_logos_dir}")
        
        # List files
        files = os.listdir(company_logos_dir)
        if files:
            print(f"   ✅ Found {len(files)} file(s):")
            for f in files:
                print(f"      - {f}")
        else:
            print(f"   ⚠️  Directory empty (no logos uploaded yet)")
    else:
        print(f"   ❌ company_logos directory doesn't exist")
        print(f"   Creating: {company_logos_dir}")
        os.makedirs(company_logos_dir, exist_ok=True)
        print(f"   ✅ Created!")
    
    # Check company profiles
    print("\n📋 Checking company profiles...")
    
    profiles = CompanyProfile.objects.all()
    print(f"   Found {profiles.count()} company profile(s)")
    
    for profile in profiles:
        print(f"\n   Profile: {profile.company_name}")
        print(f"   - User: {profile.user.email}")
        print(f"   - Logo field: {profile.logo}")
        
        if profile.logo:
            print(f"   - Logo name: {profile.logo.name}")
            print(f"   - Logo path: {profile.logo.path}")
            print(f"   - Logo URL: {profile.logo.url}")
            
            # Check if file actually exists
            if os.path.exists(profile.logo.path):
                size_kb = os.path.getsize(profile.logo.path) / 1024
                print(f"   - File exists: ✅ ({size_kb:.2f} KB)")
            else:
                print(f"   - File exists: ❌ FILE NOT FOUND!")
                print(f"   - Path checked: {profile.logo.path}")
        else:
            print(f"   - Logo: ❌ NOT UPLOADED")
            print(f"\n   💡 SOLUTION:")
            print(f"      1. Go to: http://127.0.0.1:8000/admin/accounts/companyprofile/{profile.id}/change/")
            print(f"      2. Upload a logo file (PNG recommended)")
            print(f"      3. Click Save")
        
        print(f"\n   Branding Settings:")
        print(f"   - Enabled: {profile.branding_enabled}")
        print(f"   - Mode: {profile.branding_mode}")
        print(f"   - Slogan: {profile.slogan or 'Not set'}")
        print(f"   - Position: {profile.logo_position}")
        print(f"   - Size: {profile.logo_size_percent}%")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    profiles_with_logo = profiles.filter(logo__isnull=False).count()
    profiles_without_logo = profiles.filter(logo__isnull=True).count()
    
    print(f"\n   Profiles with logo: {profiles_with_logo}")
    print(f"   Profiles without logo: {profiles_without_logo}")
    
    if profiles_without_logo > 0:
        print("\n⚠️  ACTION REQUIRED:")
        print("   Upload logo via Django admin to enable branding")
        print(f"   Admin URL: http://127.0.0.1:8000/admin/accounts/companyprofile/")
    else:
        print("\n✅ All profiles have logos!")
        print("   Branding should work automatically")


if __name__ == '__main__':
    main()

