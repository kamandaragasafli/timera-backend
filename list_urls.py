#!/usr/bin/env python
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'socialai_backend.settings'

import django
django.setup()

from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver

def show_urls(urlpatterns, prefix=''):
    for pattern in urlpatterns:
        if isinstance(pattern, URLResolver):
            show_urls(pattern.url_patterns, prefix + str(pattern.pattern))
        elif isinstance(pattern, URLPattern):
            print(f"{prefix}{pattern.pattern}")

print("\n" + "="*70)
print("DJANGO URL PATTERNS")
print("="*70)

resolver = get_resolver()
show_urls(resolver.url_patterns)

# Specifically look for apply-branding
print("\n" + "="*70)
print("SEARCHING FOR 'apply-branding'")
print("="*70)

from django.urls import reverse
try:
    url = reverse('apply_branding', kwargs={'post_id': '12345678-1234-1234-1234-123456789012'})
    print(f"✅ FOUND: {url}")
except Exception as e:
    print(f"❌ NOT FOUND: {e}")

print("\n" + "="*70)

