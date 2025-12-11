#!/usr/bin/env python
"""
Test Branding - İndi Test Edin
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialai_backend.settings')
django.setup()

from accounts.models import CompanyProfile, User
from posts.models import Post
from posts.branding import ImageBrandingService
from PIL import Image


def main():
    print("\n" + "="*70)
    print("🎨 BRENDING TEST - İNDİ")
    print("="*70)
    
    # 1. Company Profile yoxla
    print("\n📋 1. Company Profile")
    profile = CompanyProfile.objects.filter(logo__isnull=False).first()
    
    if not profile:
        print("❌ Logo yüklənmiş profil tapılmadı!")
        print("\nHəll: Logo yükləyin:")
        print("  http://127.0.0.1:8000/admin/accounts/companyprofile/")
        return
    
    print(f"✅ Profil: {profile.company_name}")
    print(f"✅ Logo: {profile.logo.name}")
    print(f"✅ Logo faylı var: {os.path.exists(profile.logo.path)}")
    print(f"✅ Sloqan: {profile.slogan or 'Yoxdur'}")
    print(f"✅ Brending aktiv: {profile.branding_enabled}")
    print(f"✅ Brending mode: {profile.branding_mode}")
    
    # 2. Post yoxla
    print("\n📋 2. Postlar")
    posts = Post.objects.filter(user=profile.user).order_by('-created_at')[:5]
    
    if not posts:
        print("❌ Post tapılmadı!")
        return
    
    print(f"✅ {posts.count()} post tapıldı")
    
    for post in posts:
        has_image = bool(post.custom_image or post.design_url or post.design_thumbnail)
        is_branded = 'branded_' in (post.custom_image.name if post.custom_image else '')
        
        print(f"\n   Post {post.id}:")
        print(f"   - Şəkil var: {has_image}")
        print(f"   - Brendləşdirilib: {is_branded}")
        
        if post.custom_image:
            print(f"   - custom_image: {post.custom_image.name}")
        if post.design_url:
            print(f"   - design_url: {post.design_url[:60]}...")
    
    # 3. Test branding
    print("\n📋 3. Brending Test")
    
    test_post = posts.filter(
        custom_image__isnull=False
    ).first() or posts.filter(
        design_url__isnull=False
    ).first() or posts.filter(
        design_thumbnail__isnull=False
    ).first()
    
    if not test_post:
        print("❌ Şəkilli post tapılmadı")
        return
    
    print(f"\nTest post: {test_post.id}")
    
    try:
        print("🎨 Brending tətbiq olunur...")
        
        service = ImageBrandingService(profile)
        
        # Get image source
        if test_post.custom_image:
            image_source = test_post.custom_image.path
        elif test_post.design_url:
            image_source = test_post.design_url
        else:
            image_source = test_post.design_thumbnail
        
        print(f"   Image source: {image_source[:60] if len(str(image_source)) > 60 else image_source}")
        
        branded = service.apply_branding(image_source)
        
        print(f"\n✅ UĞURLU! Brending tətbiq olundu!")
        print(f"   Şəkil ölçüsü: {branded.size}")
        print(f"   Logo pozisiyası: {service.logo_position}")
        print(f"   Logo ölçüsü: {service.logo_size_percent}%")
        print(f"   Padding: {service.padding}px")
        
        # Test faylı yadda saxla
        test_output = "test_branded_result.png"
        branded.save(test_output)
        print(f"\n📁 Test nəticəsi: {test_output}")
        print(f"   Bu faylı açın - logo və sloqan olmalıdır!")
        
    except Exception as e:
        print(f"\n❌ XƏTA: {e}")
        import traceback
        traceback.print_exc()
        
        print("\n🔍 Yoxlamalar:")
        print(f"   - Logo faylı var: {os.path.exists(profile.logo.path)}")
        print(f"   - Logo path: {profile.logo.path}")
        print(f"   - Brending aktiv: {profile.branding_enabled}")
    
    # 4. Tövsiyələr
    print("\n" + "="*70)
    print("📋 TÖVSİYƏLƏR")
    print("="*70)
    
    branded_posts = posts.filter(custom_image__contains='branded_').count()
    
    if branded_posts == 0:
        print("\n⚠️  Heç bir post brendləşdirilməyib!")
        print("\nHəll 1: Yeni postlar yaradın")
        print("  → Avtomatik olaraq logo + sloqan əlavə olunacaq")
        print("\nHəll 2: Köhnə postlara manual tətbiq edin")
        print("  → Frontend-də 'Brending Tətbiq Et' düyməsi lazımdır")
        print("  → API: POST /api/posts/{id}/apply-branding/")
    else:
        print(f"\n✅ {branded_posts} post brendləşdirilib!")
    
    print("\n" + "="*70)


if __name__ == '__main__':
    main()

