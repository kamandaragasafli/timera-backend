#!/usr/bin/env python
"""
Test LinkedIn Integration
This script tests the LinkedIn OAuth and posting functionality
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialai_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from social_accounts.models import SocialAccount
from posts.models import Post
import requests
from django.conf import settings

User = get_user_model()


def test_oauth_url_generation():
    """Test 1: Generate LinkedIn OAuth URL"""
    print("\n" + "="*60)
    print("TEST 1: Generate LinkedIn OAuth URL")
    print("="*60)
    
    # This should be called through the API with an authenticated user
    # For testing, we'll show what the URL would look like
    
    client_id = settings.LINKEDIN_CLIENT_ID
    backend_url = settings.BACKEND_URL
    redirect_uri = f"{backend_url}/api/social-accounts/callback/linkedin/"
    scopes = 'openid profile email w_member_social'
    
    print(f"\n✅ LinkedIn Client ID configured: {bool(client_id)}")
    print(f"✅ Redirect URI: {redirect_uri}")
    print(f"✅ Required Scopes: {scopes}")
    
    if not client_id:
        print("\n⚠️  WARNING: LINKEDIN_CLIENT_ID not set in settings")
        print("   Please add to your local.env file")
        return False
    
    print("\n📝 To test OAuth manually:")
    print("   1. Call: GET /api/social-accounts/auth-url/linkedin/")
    print("   2. Click the returned auth_url in a browser")
    print("   3. Authorize the app")
    print("   4. You'll be redirected back to the callback URL")
    
    return True


def test_linkedin_account_exists():
    """Test 2: Check if any LinkedIn accounts are connected"""
    print("\n" + "="*60)
    print("TEST 2: Check LinkedIn Account Connections")
    print("="*60)
    
    linkedin_accounts = SocialAccount.objects.filter(platform='linkedin', is_active=True)
    
    if linkedin_accounts.exists():
        print(f"\n✅ Found {linkedin_accounts.count()} LinkedIn account(s) connected:")
        for account in linkedin_accounts:
            print(f"   - {account.display_name} ({account.platform_username})")
            print(f"     User: {account.user.email}")
            print(f"     Token expires: {account.expires_at}")
        return True
    else:
        print("\n⚠️  No LinkedIn accounts connected yet")
        print("   Please connect a LinkedIn account first through the OAuth flow")
        return False


def test_create_test_post():
    """Test 3: Create a test post"""
    print("\n" + "="*60)
    print("TEST 3: Create Test Post")
    print("="*60)
    
    # Get first user with LinkedIn account
    linkedin_account = SocialAccount.objects.filter(
        platform='linkedin', 
        is_active=True
    ).first()
    
    if not linkedin_account:
        print("\n⚠️  No LinkedIn account found. Skipping test.")
        return None
    
    user = linkedin_account.user
    
    # Create a test post
    post = Post.objects.create(
        user=user,
        title="Test LinkedIn Post",
        content="Testing LinkedIn integration from Timera! 🚀\n\nThis is an automated test post to verify that our LinkedIn API integration is working correctly.",
        hashtags=["#Testing", "#LinkedIn", "#Automation"],
        status='draft',
        ai_generated=False
    )
    
    print(f"\n✅ Created test post: {post.id}")
    print(f"   Title: {post.title}")
    print(f"   Content: {post.content[:50]}...")
    print(f"   Status: {post.status}")
    
    return post


def test_linkedin_api_connection():
    """Test 4: Test LinkedIn API connection"""
    print("\n" + "="*60)
    print("TEST 4: Test LinkedIn API Connection")
    print("="*60)
    
    linkedin_account = SocialAccount.objects.filter(
        platform='linkedin',
        is_active=True
    ).first()
    
    if not linkedin_account:
        print("\n⚠️  No LinkedIn account found. Skipping test.")
        return False
    
    access_token = linkedin_account.get_access_token()
    
    # Test getting user info
    response = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={
            'Authorization': f'Bearer {access_token}',
        }
    )
    
    if response.status_code == 200:
        user_data = response.json()
        print(f"\n✅ LinkedIn API connection successful!")
        print(f"   Name: {user_data.get('name')}")
        print(f"   Email: {user_data.get('email')}")
        print(f"   User ID: {user_data.get('sub')}")
        return True
    else:
        print(f"\n❌ LinkedIn API connection failed")
        print(f"   Status: {response.status_code}")
        print(f"   Error: {response.text}")
        return False


def test_publish_to_linkedin(post_id=None):
    """Test 5: Publish a post to LinkedIn"""
    print("\n" + "="*60)
    print("TEST 5: Publish Post to LinkedIn")
    print("="*60)
    
    if not post_id:
        print("\n⚠️  No post ID provided. Creating a test post...")
        post = test_create_test_post()
        if not post:
            return False
        post_id = post.id
    else:
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            print(f"\n❌ Post with ID {post_id} not found")
            return False
    
    print(f"\n📤 Attempting to publish post {post_id} to LinkedIn...")
    print(f"   Title: {post.title}")
    print(f"   Content preview: {post.content[:100]}...")
    
    print("\n📝 To publish manually:")
    print(f"   POST /api/posts/{post_id}/publish-linkedin/")
    print("   Headers: Authorization: Bearer <your_token>")
    
    print("\n⚠️  NOTE: Actual publishing is done through the API endpoint")
    print("   This test script only validates the setup.")
    
    return True


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("LINKEDIN INTEGRATION TEST SUITE")
    print("="*60)
    
    results = {
        'OAuth URL Generation': test_oauth_url_generation(),
        'LinkedIn Accounts': test_linkedin_account_exists(),
        'API Connection': test_linkedin_api_connection(),
        'Create Test Post': test_create_test_post() is not None,
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
    print("NEXT STEPS")
    print("="*60)
    print("""
1. Set up LinkedIn Developer App:
   - Go to https://www.linkedin.com/developers/
   - Create a new app or use existing one
   - Add redirect URL: {backend_url}/api/social-accounts/callback/linkedin/
   - Request 'Sign In with LinkedIn' product
   - Copy Client ID and Client Secret to local.env

2. Update local.env:
   LINKEDIN_CLIENT_ID=your_client_id_here
   LINKEDIN_CLIENT_SECRET=your_client_secret_here

3. Test OAuth Flow:
   - Start server: python manage.py runserver
   - Call: GET /api/social-accounts/auth-url/linkedin/
   - Follow the returned auth_url
   - Authorize the app

4. Test Publishing:
   - Create a post through the API
   - Call: POST /api/posts/{post_id}/publish-linkedin/
   - Check your LinkedIn profile for the post
    """)


if __name__ == '__main__':
    main()

