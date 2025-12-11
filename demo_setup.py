"""
Demo setup script to create sample data for testing
Run this script to populate the database with sample data
"""

import os
import django
import sys
from datetime import datetime, timedelta

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialai_backend.settings')
django.setup()

from accounts.models import User, CompanyProfile, BrandVoice
from posts.models import Post, AIGeneratedContent

def create_demo_data():
    """Create demo data for testing"""
    
    print("Creating demo data...")
    
    # Create demo user if not exists
    email = "demo@socialai.com"
    try:
        user = User.objects.get(email=email)
        print(f"Demo user already exists: {email}")
    except User.DoesNotExist:
        user = User.objects.create_user(
            email=email,
            username="demo_user",
            password="demo123",
            first_name="Demo",
            last_name="User",
            company_name="Demo Tech Company"
        )
        print(f"Created demo user: {email}")
    
    # Create company profile
    company_profile, created = CompanyProfile.objects.get_or_create(
        user=user,
        defaults={
            'company_name': 'Demo Tech Company',
            'industry': 'technology',
            'company_size': '11-50',
            'website': 'https://demo-tech.com',
            'location': 'Bakı, Azərbaycan',
            'business_description': 'Biz texnologiya sahəsində innovativ həllər təklif edən şirkətik. Müştərilərimizə ən son texnologiyalardan istifadə edərək keyfiyyətli xidmətlər göstəririk.',
            'target_audience': 'Kiçik və orta biznes sahibləri, texnologiya həvəskarları, gənc peşəkarlar',
            'unique_selling_points': 'AI əsaslı həllər, 24/7 dəstək, fərdiləşdirilmiş yanaşma, sürətli həllər',
            'social_media_goals': 'Brend məlumatlılığını artırmaq, müştəri bazasını genişləndirmək, ekspert kimi tanınmaq',
            'preferred_tone': 'professional',
            'content_topics': ['texnologiya', 'innovasiya', 'AI', 'biznes həlləri', 'rəqəmsal transformasiya'],
            'keywords': ['AI', 'texnologiya', 'innovasiya', 'həllər', 'avtomatlaşdırma'],
            'avoid_topics': ['siyasət', 'mübahisəli mövzular'],
            'primary_language': 'az'
        }
    )
    
    if created:
        print("Created demo company profile")
    else:
        print("Demo company profile already exists")
    
    # Create brand voice
    brand_voice, created = BrandVoice.objects.get_or_create(
        user=user,
        name="Professional Azerbaijani",
        defaults={
            'tone': 'professional',
            'industry': 'Technology',
            'target_audience': 'Azerbaijani business professionals',
            'custom_instructions': 'Use professional Azerbaijani language, include relevant business terms, focus on innovation and technology',
            'is_default': True
        }
    )
    
    if created:
        print("Created demo brand voice")
    else:
        print("Demo brand voice already exists")
    
    # Create sample AI generated content batch
    ai_batch, created = AIGeneratedContent.objects.get_or_create(
        user=user,
        defaults={
            'company_info': {
                'company_name': company_profile.company_name,
                'industry': company_profile.industry,
                'business_description': company_profile.business_description
            },
            'generation_prompt': 'Generate professional social media posts in Azerbaijani',
            'language': 'az',
            'status': 'pending_approval',
            'total_posts': 3,
            'approved_posts': 0
        }
    )
    
    if created:
        print("Created demo AI batch")
    
    # Create sample posts
    sample_posts = [
        {
            'title': 'Texnologiya sahəsində yeniliklər',
            'content': '🚀 Texnologiya dünyasında hər gün yeni imkanlar yaranır!\n\nBizim şirkət olaraq, müştərilərimizə ən müasir AI həllərini təqdim edirik. Rəqəmsal transformasiya prosesində sizin yanınızdayıq.\n\n✨ Nə təklif edirik:\n• AI əsaslı avtomatlaşdırma\n• Fərdiləşdirilmiş həllər\n• 24/7 texniki dəstək\n\nGələcəyi birlikdə quraq! 💪\n\n#AI #Texnologiya #İnnovasiya #RəqəmsalTransformasiya',
            'description': 'Şirkətin AI həlləri haqqında məlumat verici post',
            'hashtags': ['#AI', '#Texnologiya', '#İnnovasiya', '#RəqəmsalTransformasiya']
        },
        {
            'title': 'Müştəri uğur hekayəsi',
            'content': '🌟 Müştəri Uğur Hekayəsi\n\nBu həftə Demo Tech Company ilə işləyən müştərilərimizdən biri böyük uğur əldə etdi!\n\n📈 Nəticələr:\n• 50% vaxt qənaəti\n• 30% məhsuldarlıq artımı\n• Tam avtomatlaşdırılmış proseslər\n\n"Demo Tech Company bizim işimizi tamamilə dəyişdi. İndi daha səmərəli və sürətli işləyirik!" - Müştərimiz\n\nSizin də uğur hekayənizi yazmağa hazırsınız? 🚀\n\n#MüştəriUğuru #Nəticələr #Texnologiya',
            'description': 'Müştəri təcrübəsi və uğur nəticələri',
            'hashtags': ['#MüştəriUğuru', '#Nəticələr', '#Texnologiya']
        },
        {
            'title': 'Həftəlik texnologiya məsləhətləri',
            'content': '💡 Həftəlik Texnologiya Məsləhəti\n\nBu həftə sizinlə AI avtomatlaşdırmasının 5 əsas faydası barədə danışaq:\n\n1️⃣ Vaxt qənaəti - rutinləri avtomatlaşdırın\n2️⃣ Xəta azalması - insan xətalarını minimuma endirin\n3️⃣ 24/7 işləmə - fasiləsiz xidmət\n4️⃣ Məlumat analizi - dəqiq qərarlar\n5️⃣ Miqyas artırma - böyümə üçün hazır olun\n\nHansı sahədə avtomatlaşdırma istəyirsiniz? Şərhlədə yazın! 👇\n\n#AIAvtomatlaşdırma #Məsləhət #Texnologiya #Səmərəlilik',
            'description': 'Texnologiya məsləhətləri və AI faydaları',
            'hashtags': ['#AIAvtomatlaşdırma', '#Məsləhət', '#Texnologiya', '#Səmərəlilik']
        }
    ]
    
    for i, post_data in enumerate(sample_posts):
        post, created = Post.objects.get_or_create(
            user=user,
            title=post_data['title'],
            defaults={
                'content': post_data['content'],
                'description': post_data['description'],
                'hashtags': post_data['hashtags'],
                'ai_generated': True,
                'ai_content_batch': ai_batch,
                'brand_voice': brand_voice,
                'status': 'pending_approval',
                'requires_approval': True,
                'scheduled_time': datetime.now() + timedelta(days=i+1, hours=10)
            }
        )
        
        if created:
            print(f"Created demo post: {post_data['title']}")
    
    print("\n✅ Demo data creation complete!")
    print(f"Demo user: {email} / password: demo123")
    print("You can now test the AI content generation workflow!")

if __name__ == '__main__':
    create_demo_data()






