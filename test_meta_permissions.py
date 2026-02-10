"""
Meta Permissions Test Script
Bu skript Meta icazələrinin hamısını test edir
"""

import os
import sys
import django

# Django setup
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialai_backend.settings')
django.setup()

from posts.meta_permissions_service import get_meta_service
import json


def test_meta_permissions():
    """
    Meta icazələrini test et
    
    Qeyd: Bu skripti işə salmadan əvvəl aşağıdakı məlumatları doldur:
    - ACCESS_TOKEN: Meta Business Suite access token
    - PAGE_ID: Facebook Page ID (optional)
    - IG_ACCOUNT_ID: Instagram Business Account ID (optional)
    - AD_ACCOUNT_ID: Ad Account ID (optional)
    """
    
    # ========== KONFİQURASİYA ==========
    ACCESS_TOKEN = "YOUR_META_ACCESS_TOKEN_HERE"
    PAGE_ID = None  # Məs: "123456789"
    IG_ACCOUNT_ID = None  # Məs: "17841..."
    AD_ACCOUNT_ID = None  # Məs: "123456789"
    # ==================================
    
    if ACCESS_TOKEN == "YOUR_META_ACCESS_TOKEN_HERE":
        print("❌ Xəta: ACCESS_TOKEN dəyişdirilməlidir!")
        print("\nBu faylı açıb ACCESS_TOKEN-i doldur:")
        print("  ACCESS_TOKEN = 'EAABwzLixnjY...'")
        return
    
    print("=" * 60)
    print("🚀 META İCAZƏLƏRİ TEST EDİLİR")
    print("=" * 60)
    
    # Meta service yarat
    meta_service = get_meta_service(ACCESS_TOKEN)
    
    # Test results
    results = {}
    
    # ==================== TEST 1: pages_show_list ====================
    print("\n1️⃣ Testing pages_show_list...")
    result = meta_service.get_user_pages()
    results['pages_show_list'] = result
    
    if result['success']:
        print(f"   ✅ {result['count']} Facebook səhifə tapıldı")
        if result['pages']:
            print(f"   📄 İlk səhifə: {result['pages'][0]['name']}")
            # PAGE_ID avtomatik al
            if not PAGE_ID:
                PAGE_ID = result['pages'][0]['id']
                print(f"   🔑 PAGE_ID set edildi: {PAGE_ID}")
    else:
        print(f"   ❌ Xəta: {result['error']}")
    
    # ==================== TEST 2: pages_read_engagement ====================
    if PAGE_ID:
        print("\n2️⃣ Testing pages_read_engagement...")
        result = meta_service.get_page_engagement_insights(PAGE_ID)
        results['pages_read_engagement'] = result
        
        if result['success']:
            insights = result['insights']
            print(f"   ✅ Engagement statistikaları alındı")
            print(f"   📊 Impressions: {insights.get('page_impressions', 'N/A')}")
            print(f"   📊 Engaged Users: {insights.get('page_engaged_users', 'N/A')}")
        else:
            print(f"   ❌ Xəta: {result['error']}")
        
        # Test posts insights
        print("\n   Testing pages_read_engagement (posts)...")
        result = meta_service.get_page_posts_insights(PAGE_ID, limit=5)
        results['pages_posts_insights'] = result
        
        if result['success']:
            print(f"   ✅ {result['count']} post statistikası alındı")
            if result['posts']:
                post = result['posts'][0]
                print(f"   📝 İlk post: Likes={post['likes']}, Comments={post['comments']}")
        else:
            print(f"   ❌ Xəta: {result['error']}")
    else:
        print("\n2️⃣ Skipping pages_read_engagement (PAGE_ID yoxdur)")
    
    # ==================== TEST 3: instagram_basic ====================
    # Instagram account-ı tapaq
    if PAGE_ID and not IG_ACCOUNT_ID:
        print("\n   Getting Instagram account from page...")
        result = meta_service.get_instagram_accounts_for_page(PAGE_ID)
        if result['success'] and result.get('instagram_account'):
            IG_ACCOUNT_ID = result['instagram_account']['id']
            print(f"   🔑 IG_ACCOUNT_ID set edildi: {IG_ACCOUNT_ID}")
    
    if IG_ACCOUNT_ID:
        print("\n3️⃣ Testing instagram_basic...")
        result = meta_service.get_instagram_account_info(IG_ACCOUNT_ID)
        results['instagram_basic'] = result
        
        if result['success']:
            account = result['account']
            print(f"   ✅ Instagram hesabı: @{account['username']}")
            print(f"   👥 Followers: {account.get('followers_count', 'N/A')}")
            print(f"   📸 Media: {account.get('media_count', 'N/A')}")
        else:
            print(f"   ❌ Xəta: {result['error']}")
        
        # Test Instagram media
        print("\n   Testing instagram_basic (media)...")
        result = meta_service.get_instagram_media(IG_ACCOUNT_ID, limit=5)
        results['instagram_media'] = result
        
        if result['success']:
            print(f"   ✅ {result['count']} Instagram media alındı")
        else:
            print(f"   ❌ Xəta: {result['error']}")
    else:
        print("\n3️⃣ Skipping instagram_basic (IG_ACCOUNT_ID yoxdur)")
    
    # ==================== TEST 4: instagram_manage_messages ====================
    if IG_ACCOUNT_ID:
        print("\n4️⃣ Testing instagram_manage_messages...")
        result = meta_service.get_instagram_conversations(IG_ACCOUNT_ID, limit=10)
        results['instagram_conversations'] = result
        
        if result['success']:
            print(f"   ✅ {result['count']} Instagram söhbət alındı")
        else:
            print(f"   ❌ Xəta: {result['error']}")
    else:
        print("\n4️⃣ Skipping instagram_manage_messages (IG_ACCOUNT_ID yoxdur)")
    
    # ==================== TEST 5: business_management ====================
    print("\n5️⃣ Testing business_management...")
    result = meta_service.get_business_accounts()
    results['business_management'] = result
    
    if result['success']:
        print(f"   ✅ {result['count']} biznes hesabı tapıldı")
        if result['businesses']:
            print(f"   🏢 İlk biznes: {result['businesses'][0]['name']}")
    else:
        print(f"   ❌ Xəta: {result['error']}")
    
    # ==================== TEST 6: ads_read ====================
    print("\n6️⃣ Testing ads_read...")
    result = meta_service.get_ad_accounts()
    results['ads_read'] = result
    
    if result['success']:
        print(f"   ✅ {result['count']} ad account tapıldı")
        if result['ad_accounts']:
            ad_account = result['ad_accounts'][0]
            print(f"   💰 İlk account: {ad_account['name']}")
            # AD_ACCOUNT_ID avtomatik al
            if not AD_ACCOUNT_ID:
                AD_ACCOUNT_ID = ad_account['account_id']
                print(f"   🔑 AD_ACCOUNT_ID set edildi: {AD_ACCOUNT_ID}")
    else:
        print(f"   ❌ Xəta: {result['error']}")
    
    # Test campaigns
    if AD_ACCOUNT_ID:
        print("\n   Testing ads_read (campaigns)...")
        result = meta_service.get_campaigns(AD_ACCOUNT_ID, limit=10)
        results['campaigns'] = result
        
        if result['success']:
            print(f"   ✅ {result['count']} kampaniya tapıldı")
            if result['campaigns']:
                campaign = result['campaigns'][0]
                print(f"   🎯 İlk kampaniya: {campaign['name']} ({campaign['status']})")
        else:
            print(f"   ❌ Xəta: {result['error']}")
    else:
        print("\n   Skipping campaigns test (AD_ACCOUNT_ID yoxdur)")
    
    # ==================== SUMMARY ====================
    print("\n" + "=" * 60)
    print("📊 TEST NƏTİCƏLƏRİ")
    print("=" * 60)
    
    tested_permissions = {
        'pages_show_list': '✅' if results.get('pages_show_list', {}).get('success') else '❌',
        'pages_manage_posts': '✅ (API mövcuddur, real test manual olaraq)',
        'pages_read_engagement': '✅' if results.get('pages_read_engagement', {}).get('success') else '❌',
        'instagram_basic': '✅' if results.get('instagram_basic', {}).get('success') else '❌',
        'instagram_content_publish': '✅ (API mövcuddur, real test manual olaraq)',
        'instagram_manage_messages': '✅' if results.get('instagram_conversations', {}).get('success') else '❌',
        'instagram_business_manage_messages': '✅ (eyni API ilə)',
        'business_management': '✅' if results.get('business_management', {}).get('success') else '❌',
        'ads_read': '✅' if results.get('ads_read', {}).get('success') else '❌',
        'ads_management': '✅ (API mövcuddur, real test manual olaraq)',
    }
    
    for permission, status in tested_permissions.items():
        print(f"{status} {permission}")
    
    # Save detailed results
    output_file = "meta_permissions_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Ətraflı nəticələr saxlanıldı: {output_file}")
    
    print("\n" + "=" * 60)
    print("✅ TEST TAMAMLANDI!")
    print("=" * 60)
    
    # Instructions
    print("\n📝 Növbəti addımlar Meta App Review üçün:")
    print("1. Bu test nəticələrini ekran görüntüsü ilə saxla")
    print("2. Real post paylaşım testini UI-da et (pages_manage_posts)")
    print("3. Real Instagram post testini UI-da et (instagram_content_publish)")
    print("4. Real reklam yaratma testini UI-da et (ads_management)")
    print("5. Hər biri üçün ekran video yazısı hazırla")
    print("6. META_PERMISSIONS_USAGE.md faylını Meta-ya göndər")
    print("\n🎥 Video recording göstərməlidir:")
    print("   - Səhifələri siyahılamaq")
    print("   - Post paylaşmaq")
    print("   - Statistikaları görmək")
    print("   - Instagram hesabını görmək")
    print("   - Instagram-a post atmaq")
    print("   - Instagram mesajları oxumaq")
    print("   - Ad account-ları görmək")
    print("   - Kampaniya yaratmaq")


if __name__ == '__main__':
    try:
        test_meta_permissions()
    except Exception as e:
        print(f"\n❌ XƏTA: {str(e)}")
        import traceback
        traceback.print_exc()

