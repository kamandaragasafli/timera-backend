#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

os.environ['DJANGO_SETTINGS_MODULE'] = 'socialai_backend.settings'

import django
django.setup()

from posts.models import Post

print("\n" + "="*70)
print("POST IDs")
print("="*70)

posts = Post.objects.all().order_by('-created_at')[:10]

if not posts:
    print("\nNo posts found")
else:
    print(f"\nFound {posts.count()} posts:\n")
    
    for i, post in enumerate(posts, 1):
        has_image = bool(post.custom_image or post.design_url or post.design_thumbnail)
        
        print(f"{i}. Post ID:")
        print(f"   {post.id}")
        print(f"   Content: {post.content[:50] if post.content else 'No content'}...")
        print(f"   Status: {post.status}")
        print(f"   Has Image: {'Yes' if has_image else 'No'}")
        if post.custom_image:
            print(f"   Image: {post.custom_image.name}")
        print()

print("="*70)
print("\nTest URLs (copy to browser):\n")

for post in posts[:3]:
    print(f"http://127.0.0.1:8000/api/posts/{post.id}/apply-branding/")

print("\n" + "="*70)
