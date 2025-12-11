#!/usr/bin/env python
"""
Quick OAuth Configuration Checker
Run this to verify your OAuth credentials are properly configured
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialai_backend.settings')
django.setup()

from django.conf import settings


def check_credential(name, value, required=True):
    """Check if a credential is configured"""
    if value:
        masked = value[:8] + '...' if len(value) > 8 else '***'
        print(f"  ✅ {name}: {masked}")
        return True
    else:
        status = "❌ REQUIRED" if required else "⚠️  Optional"
        print(f"  {status} {name}: NOT SET")
        return not required


def main():
    print("\n" + "="*60)
    print("OAUTH CREDENTIALS CHECK")
    print("="*60)
    
    all_good = True
    
    # LinkedIn
    print("\n📱 LINKEDIN (Required for LinkedIn integration)")
    all_good &= check_credential("LINKEDIN_CLIENT_ID", settings.LINKEDIN_CLIENT_ID, required=True)
    all_good &= check_credential("LINKEDIN_CLIENT_SECRET", settings.LINKEDIN_CLIENT_SECRET, required=True)
    
    # Meta (Facebook/Instagram)
    print("\n📘 META / FACEBOOK / INSTAGRAM")
    all_good &= check_credential("META_APP_ID", settings.META_APP_ID, required=False)
    all_good &= check_credential("META_APP_SECRET", settings.META_APP_SECRET, required=False)
    
    # URLs
    print("\n🌐 BACKEND & FRONTEND URLS")
    all_good &= check_credential("BACKEND_URL", settings.BACKEND_URL, required=True)
    all_good &= check_credential("FRONTEND_URL", settings.FRONTEND_URL, required=True)
    
    # Other services
    print("\n🤖 AI SERVICES")
    check_credential("OPENAI_API_KEY", settings.OPENAI_API_KEY, required=False)
    check_credential("IDEOGRAM_API_KEY", settings.IDEOGRAM_API_KEY, required=False)
    
    # Summary
    print("\n" + "="*60)
    if all_good:
        print("✅ ALL REQUIRED CREDENTIALS CONFIGURED!")
        print("\nYou can now test LinkedIn integration:")
        print("  python test_linkedin.py")
    else:
        print("❌ SOME REQUIRED CREDENTIALS ARE MISSING")
        print("\n📝 Next steps:")
        print("  1. Read: SETUP_OAUTH_CREDENTIALS.md")
        print("  2. Get LinkedIn credentials from: https://www.linkedin.com/developers/")
        print("  3. Add them to local.env file")
        print("  4. Restart your server")
        print("  5. Run this script again to verify")
    print("="*60 + "\n")
    
    return 0 if all_good else 1


if __name__ == '__main__':
    sys.exit(main())

