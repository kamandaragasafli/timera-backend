#!/usr/bin/env python
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'socialai_backend.settings'

import django
django.setup()

from django.test import RequestFactory
from posts.views import ApplyBrandingView
from django.contrib.auth import get_user_model
from posts.models import Post
from rest_framework.test import force_authenticate

User = get_user_model()

print("\n" + "="*70)
print("DIRECT BRANDING ENDPOINT TEST")
print("="*70)

try:
    # Get user and post
    user = User.objects.first()
    post = Post.objects.filter(user=user).exclude(design_thumbnail='').first()
    
    if not user or not post:
        print("❌ User or Post not found")
        exit(1)
    
    print(f"\n✅ User: {user.email}")
    print(f"✅ Post: {post.id}")
    print(f"✅ Has image: {bool(post.custom_image or post.design_url or post.design_thumbnail)}")
    
    # Create request
    factory = RequestFactory()
    request = factory.post(f'/api/posts/{post.id}/apply-branding/')
    force_authenticate(request, user=user)
    
    # Call view
    print(f"\n📤 Calling ApplyBrandingView...")
    view = ApplyBrandingView.as_view()
    response = view(request, post_id=str(post.id))
    
    print(f"\n📥 Response:")
    print(f"   Status: {response.status_code}")
    print(f"   Data: {response.data}")
    
    if response.status_code == 200:
        print(f"\n🎉 SUCCESS! Branding applied!")
    else:
        print(f"\n⚠️  Error: {response.data.get('error')}")

except Exception as e:
    print(f"\n❌ EXCEPTION: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)

