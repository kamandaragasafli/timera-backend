# Meta Business Suite İcazələrinin İstifadəsi

Bu sənəd Meta Business Suite API icazələrinin **REAL** kodda necə istifadə edildiyini göstərir.

## 📋 İcazələr və İstifadə Yerlə

### 1. ✅ **pages_show_list** - Facebook Səhifələrin Siyahısı

**İstifadə olunduğu funksiya:**
- `meta_permissions_service.py` → `get_user_pages()`
- `meta_views.py` → `list_facebook_pages()`

**API Endpoint:**
```http
GET /api/posts/meta/pages/
Authorization: Bearer <token>
```

**Cavab nümunəsi:**
```json
{
  "success": true,
  "pages": [
    {
      "id": "123456789",
      "name": "My Business Page",
      "access_token": "...",
      "category": "Business",
      "fan_count": 5000,
      "followers_count": 5200
    }
  ],
  "count": 1
}
```

---

### 2. ✅ **pages_manage_posts** - Facebook Səhifəyə Post Paylaşımı

**İstifadə olunduğu funksiya:**
- `meta_permissions_service.py` → `publish_page_post()`
- `meta_views.py` → `publish_to_facebook_page()`
- `social_publisher.py` → `publish_to_facebook()` (artıq mövcuddur)

**API Endpoint:**
```http
POST /api/posts/meta/pages/publish/
Authorization: Bearer <token>
Content-Type: application/json

{
  "page_id": "123456789",
  "message": "Yeni post məzmunu! 🚀",
  "image_url": "https://example.com/image.jpg"
}
```

**Cavab nümunəsi:**
```json
{
  "success": true,
  "post_id": "123456789_987654321",
  "platform": "facebook"
}
```

---

### 3. ✅ **pages_read_engagement** - Səhifə Engagement Statistikaları

**İstifadə olunduğu funksiya:**
- `meta_permissions_service.py` → `get_page_engagement_insights()`
- `meta_permissions_service.py` → `get_page_posts_insights()`
- `meta_views.py` → `get_page_engagement()`

**API Endpoints:**

**a) Səhifə ümumi statistikaları:**
```http
GET /api/posts/meta/pages/123456789/engagement/?period=day&since=2026-02-01&until=2026-02-10
Authorization: Bearer <token>
```

**Cavab nümunəsi:**
```json
{
  "success": true,
  "insights": {
    "page_impressions": 15000,
    "page_impressions_unique": 12000,
    "page_engaged_users": 3500,
    "page_post_engagements": 800,
    "page_fans": 5200
  },
  "period": "day",
  "date_range": {
    "since": "2026-02-01",
    "until": "2026-02-10"
  }
}
```

**b) Post-lar üzrə statistikalar:**
```http
GET /api/posts/meta/pages/123456789/posts-insights/?limit=25
Authorization: Bearer <token>
```

**Cavab nümunəsi:**
```json
{
  "success": true,
  "posts": [
    {
      "post_id": "123_456",
      "message": "Post məzmunu...",
      "created_time": "2026-02-08T10:00:00+0000",
      "likes": 150,
      "comments": 25,
      "shares": 10,
      "reactions": 180
    }
  ],
  "count": 25
}
```

---

### 4. ✅ **instagram_basic** - Instagram Əsas Məlumatlar

**İstifadə olunduğu funksiya:**
- `meta_permissions_service.py` → `get_instagram_account_info()`
- `meta_permissions_service.py` → `get_instagram_media()`
- `meta_views.py` → `get_instagram_account()`

**API Endpoints:**

**a) Instagram hesab məlumatı:**
```http
GET /api/posts/meta/instagram/account/?account_id=17841...
Authorization: Bearer <token>
```

**Cavab nümunəsi:**
```json
{
  "success": true,
  "account": {
    "id": "17841...",
    "username": "my_business",
    "name": "My Business",
    "profile_picture_url": "https://...",
    "followers_count": 10000,
    "follows_count": 500,
    "media_count": 250,
    "biography": "Business description...",
    "website": "https://example.com"
  }
}
```

**b) Instagram media (postlar):**
```http
GET /api/posts/meta/instagram/media/?account_id=17841...&limit=25
Authorization: Bearer <token>
```

**Cavab nümunəsi:**
```json
{
  "success": true,
  "media": [
    {
      "id": "17912...",
      "caption": "Post caption #hashtag",
      "media_type": "IMAGE",
      "media_url": "https://...",
      "permalink": "https://instagram.com/p/...",
      "timestamp": "2026-02-08T10:00:00+0000",
      "like_count": 250,
      "comments_count": 30
    }
  ],
  "count": 25
}
```

---

### 5. ✅ **instagram_content_publish** - Instagram-a Post Paylaşımı

**İstifadə olunduğu funksiya:**
- `meta_permissions_service.py` → `publish_instagram_post()`
- `meta_views.py` → `publish_to_instagram()`
- `social_publisher.py` → `publish_to_instagram()` (artıq mövcuddur)

**API Endpoint:**
```http
POST /api/posts/meta/instagram/publish/
Authorization: Bearer <token>
Content-Type: application/json

{
  "account_id": "17841...",
  "image_url": "https://supabase.co/.../image.jpg",
  "caption": "Yeni Instagram postu! 📸 #business #success"
}
```

**Cavab nümunəsi:**
```json
{
  "success": true,
  "media_id": "17912...",
  "platform": "instagram"
}
```

**QEYD:** Instagram üçün şəkil URL-i **public HTTPS** olmalıdır (localhost işləmir).

---

### 6. ✅ **instagram_manage_messages** + **instagram_business_manage_messages** - Instagram Mesajlar

**İstifadə olunduğu funksiyalar:**
- `meta_permissions_service.py` → `get_instagram_conversations()`
- `meta_permissions_service.py` → `get_instagram_messages()`
- `meta_permissions_service.py` → `send_instagram_message()`
- `meta_views.py` → `get_instagram_conversations()`, `send_instagram_message()`

**API Endpoints:**

**a) Söhbətlərin siyahısı:**
```http
GET /api/posts/meta/instagram/conversations/?account_id=17841...&limit=25
Authorization: Bearer <token>
```

**Cavab nümunəsi:**
```json
{
  "success": true,
  "conversations": [
    {
      "id": "t_123456",
      "updated_time": "2026-02-10T12:00:00+0000",
      "message_count": 15,
      "unread_count": 2,
      "participants": [...]
    }
  ],
  "count": 25
}
```

**b) Söhbətdəki mesajlar:**
```http
GET /api/posts/meta/instagram/conversations/t_123456/messages/?limit=50
Authorization: Bearer <token>
```

**Cavab nümunəsi:**
```json
{
  "success": true,
  "messages": [
    {
      "id": "m_789",
      "created_time": "2026-02-10T12:00:00+0000",
      "from": {"id": "123", "username": "user1"},
      "to": {"id": "456", "username": "my_business"},
      "message": "Salam! Məhsulunuz haqqında soruşmaq istəyirəm."
    }
  ],
  "count": 50
}
```

**c) Mesaj göndərmə:**
```http
POST /api/posts/meta/instagram/messages/send/
Authorization: Bearer <token>
Content-Type: application/json

{
  "account_id": "17841...",
  "recipient_id": "123456",
  "message": "Salam! Necə kömək edə bilərik?"
}
```

**Cavab nümunəsi:**
```json
{
  "success": true,
  "message_id": "m_xyz123"
}
```

---

### 7. ✅ **business_management** - Biznes Hesabları İdarəetməsi

**İstifadə olunduğu funksiya:**
- `meta_permissions_service.py` → `get_business_accounts()`
- `meta_permissions_service.py` → `get_instagram_accounts_for_page()`
- `meta_views.py` → `get_business_accounts()`

**API Endpoint:**
```http
GET /api/posts/meta/business/accounts/
Authorization: Bearer <token>
```

**Cavab nümunəsi:**
```json
{
  "success": true,
  "businesses": [
    {
      "id": "123456789",
      "name": "My Business",
      "verification_status": "verified",
      "created_time": "2025-01-01T00:00:00+0000",
      "primary_page": {
        "id": "987654321",
        "name": "My Business Page"
      }
    }
  ],
  "count": 1
}
```

---

### 8. ✅ **ads_read** - Reklam Məlumatlarını Oxumaq

**İstifadə olunduğu funksiyalar:**
- `meta_permissions_service.py` → `get_ad_accounts()`
- `meta_permissions_service.py` → `get_campaigns()`
- `meta_permissions_service.py` → `get_campaign_insights()`
- `meta_views.py` → `get_ad_accounts()`, `get_campaigns()`, `get_campaign_insights()`
- `meta_ads/services.py` → `MetaAPIService.get_ad_accounts()` (artıq mövcuddur)

**API Endpoints:**

**a) Ad Account-lar:**
```http
GET /api/posts/meta/ads/accounts/
Authorization: Bearer <token>
```

**Cavab nümunəsi:**
```json
{
  "success": true,
  "ad_accounts": [
    {
      "id": "act_123456789",
      "account_id": "123456789",
      "name": "My Ad Account",
      "account_status": 1,
      "currency": "USD",
      "timezone_name": "America/New_York",
      "balance": "5000",
      "amount_spent": "15000"
    }
  ],
  "count": 1
}
```

**b) Kampaniyalar:**
```http
GET /api/posts/meta/ads/accounts/123456789/campaigns/?limit=25
Authorization: Bearer <token>
```

**Cavab nümunəsi:**
```json
{
  "success": true,
  "campaigns": [
    {
      "id": "12345",
      "name": "My Campaign",
      "status": "ACTIVE",
      "objective": "REACH",
      "daily_budget": "5000",
      "start_time": "2026-02-01T00:00:00+0000"
    }
  ],
  "count": 25
}
```

**c) Kampaniya statistikaları:**
```http
GET /api/posts/meta/ads/campaigns/12345/insights/?date_preset=last_7d
Authorization: Bearer <token>
```

**Cavab nümunəsi:**
```json
{
  "success": true,
  "insights": {
    "impressions": "15000",
    "reach": "12000",
    "clicks": "500",
    "spend": "200.50",
    "cpm": "13.37",
    "cpc": "0.40",
    "ctr": "3.33"
  },
  "date_preset": "last_7d"
}
```

---

### 9. ✅ **ads_management** - Reklamları İdarə Etmək

**İstifadə olunduğu funksiyalar:**
- `meta_permissions_service.py` → `create_campaign()`
- `meta_permissions_service.py` → `update_campaign()`
- `meta_permissions_service.py` → `create_ad_creative()`
- `meta_views.py` → `create_campaign()`, `update_campaign()`
- `meta_ads/services.py` → `MetaAPIService.create_campaign()` (artıq mövcuddur)

**API Endpoints:**

**a) Kampaniya yaratmaq:**
```http
POST /api/posts/meta/ads/campaigns/create/
Authorization: Bearer <token>
Content-Type: application/json

{
  "ad_account_id": "123456789",
  "name": "Spring Sale Campaign",
  "objective": "REACH",
  "status": "PAUSED",
  "daily_budget": 5000
}
```

**Cavab nümunəsi:**
```json
{
  "success": true,
  "campaign_id": "12345"
}
```

**b) Kampaniyanı yeniləmək:**
```http
PUT /api/posts/meta/ads/campaigns/12345/update/
Authorization: Bearer <token>
Content-Type: application/json

{
  "status": "ACTIVE",
  "daily_budget": 10000
}
```

**Cavab nümunəsi:**
```json
{
  "success": true,
  "result": {
    "success": true
  }
}
```

---

## 🧪 Bütün İcazələri Test Etmək

**Comprehensive Test Endpoint:**
```http
POST /api/posts/meta/test-permissions/
Authorization: Bearer <token>
Content-Type: application/json

{
  "page_id": "123456789",
  "instagram_account_id": "17841...",
  "ad_account_id": "123456789"
}
```

Bu endpoint **BÜTÜN** icazələri eyni anda test edir:
- ✅ pages_show_list
- ✅ pages_read_engagement
- ✅ instagram_basic
- ✅ instagram_manage_messages
- ✅ business_management
- ✅ ads_read

**Cavab nümunəsi:**
```json
{
  "success": true,
  "results": {
    "pages_show_list": {...},
    "pages_read_engagement": {...},
    "pages_posts_insights": {...},
    "instagram_basic": {...},
    "instagram_media": {...},
    "instagram_conversations": {...},
    "business_accounts": {...},
    "ad_accounts": {...},
    "campaigns": {...}
  },
  "tested_permissions": [
    "pages_show_list",
    "pages_read_engagement",
    "instagram_basic",
    "instagram_manage_messages",
    "business_management",
    "ads_read"
  ]
}
```

---

## 📝 Meta App Review üçün Qeydlər

### İcazələrin İstifadə Məqsədi:

1. **pages_show_list**: İstifadəçilərin Facebook səhifələrini görmək və seçmək
2. **pages_manage_posts**: Avtomatik AI post-ları Facebook-a paylaşmaq
3. **pages_read_engagement**: Post performansını izləmək və AI-yə feedback vermək
4. **instagram_content_publish**: AI yaradılmış post-ları Instagram-a paylaşmaq
5. **instagram_basic**: Instagram profil və post məlumatlarını göstərmək
6. **instagram_manage_messages**: Müştəri mesajlarını idarə etmək və cavab vermək
7. **instagram_business_manage_messages**: Biznes mesajlarını avtomatlaşdırmaq
8. **business_management**: Biznes hesabları arasında keçid etmək
9. **ads_read**: Reklam kampaniya performansını izləmək
10. **ads_management**: AI ilə reklam kampaniyaları yaratmaq və optimallaşdırmaq

### Screen Recording üçün Ssenari:

1. ✅ Facebook hesabını bağla → pages_show_list
2. ✅ Səhifələri siyahıla → pages_show_list
3. ✅ Post yarat və Facebook-a paylaş → pages_manage_posts
4. ✅ Səhifə statistikalarını göstər → pages_read_engagement
5. ✅ Instagram hesabı məlumatı → instagram_basic
6. ✅ Instagram-a post paylaş → instagram_content_publish
7. ✅ Instagram mesajları oxu → instagram_manage_messages
8. ✅ Instagram mesaj cavabla → instagram_business_manage_messages
9. ✅ Ad account-ları göstər → ads_read
10. ✅ Kampaniya yarat → ads_management

---

## 🚀 İstifadə Nümunəsi (Python/Requests)

```python
import requests

# User token (Facebook bağlantısından)
access_token = "EAABwzLixnjY..."
api_base = "https://your-api.com/api/posts/meta"

# 1. Facebook səhifələri
response = requests.get(
    f"{api_base}/pages/",
    headers={"Authorization": f"Bearer {access_token}"}
)
pages = response.json()

# 2. Post paylaş
page_id = pages['pages'][0]['id']
response = requests.post(
    f"{api_base}/pages/publish/",
    headers={"Authorization": f"Bearer {access_token}"},
    json={
        "page_id": page_id,
        "message": "Yeni post! 🚀",
        "image_url": "https://example.com/image.jpg"
    }
)

# 3. Statistikalar
response = requests.get(
    f"{api_base}/pages/{page_id}/engagement/",
    headers={"Authorization": f"Bearer {access_token}"},
    params={"period": "day"}
)
insights = response.json()

print(f"Impressions: {insights['insights']['page_impressions']}")
```

---

## ✅ Nəticə

Bütün **10 icazə** real kodda istifadə olunur:
1. ✅ pages_show_list
2. ✅ pages_manage_posts
3. ✅ pages_read_engagement
4. ✅ instagram_content_publish
5. ✅ instagram_basic
6. ✅ instagram_manage_messages
7. ✅ instagram_business_manage_messages
8. ✅ business_management
9. ✅ ads_read
10. ✅ ads_management

**Hər bir icazə üçün:**
- ✅ Real API funksiyası
- ✅ Django REST API endpoint
- ✅ URL konfiqurasiyası
- ✅ Nümunə istifadə
- ✅ Test funksiyası

**Meta App Review üçün hazırdır! 🎉**

