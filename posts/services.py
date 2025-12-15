import openai
import requests
import json
import logging
import os
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from .models import Post, AIGeneratedContent
from accounts.models import CompanyProfile

# Get logger for this module
logger = logging.getLogger(__name__)


class OpenAIService:
    """Service for OpenAI ChatGPT integration"""
    
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    
    def generate_monthly_posts(self, user, company_profile, num_posts=None, custom_prompt=''):
        """Generate posts in Azerbaijani language using company settings"""
        
        # Use posts_to_generate from company profile, fallback to 10 if not set
        if num_posts is None:
            num_posts = getattr(company_profile, 'posts_to_generate', 10)
        
        logger.info(f"📝 Starting post generation for user={user.email}, num_posts={num_posts}")
        if custom_prompt:
            logger.info(f"✨ Using custom instructions: {custom_prompt}")
        
        # Create AI content batch
        ai_batch = AIGeneratedContent.objects.create(
            user=user,
            company_info={
                'company_name': company_profile.company_name,
                'industry': company_profile.industry,
                'company_size': company_profile.company_size,
                'location': company_profile.location,
                'website': company_profile.website,
                'business_description': company_profile.business_description,
                'target_audience': company_profile.target_audience,
                'unique_selling_points': company_profile.unique_selling_points,
                'social_media_goals': company_profile.social_media_goals,
                'preferred_tone': company_profile.preferred_tone,
                'content_topics': company_profile.content_topics,
                'keywords': company_profile.keywords,
                'avoid_topics': company_profile.avoid_topics,
                'posts_to_generate': num_posts,
                'brand_analysis': company_profile.brand_analysis if company_profile.brand_analysis else None,
                'custom_prompt': custom_prompt if custom_prompt else None,
            },
            generation_prompt=self._build_generation_prompt(company_profile, num_posts, custom_prompt),
            language='az',
            status='generating'
        )
        
        try:
            # Generate posts using ChatGPT
            logger.info(f"🤖 Calling OpenAI API for {num_posts} posts...")
            posts_data = self._generate_posts_with_chatgpt(company_profile, num_posts, custom_prompt)
            logger.info(f"✅ OpenAI returned {len(posts_data)} posts")
            
            # Create Post objects
            created_posts = []
            for i, post_data in enumerate(posts_data):
                # Calculate scheduled time (spread across the month)
                base_date = timezone.now().date()
                days_offset = (i * 3) + 1  # Every 3 days
                scheduled_date = base_date + timedelta(days=days_offset)
                
                # Vary posting times
                posting_hours = [9, 12, 15, 18]  # 9AM, 12PM, 3PM, 6PM
                hour = posting_hours[i % len(posting_hours)]
                
                scheduled_time = timezone.make_aware(
                    datetime.combine(scheduled_date, datetime.min.time().replace(hour=hour))
                )
                
                post = Post.objects.create(
                    user=user,
                    ai_content_batch=ai_batch,
                    title=post_data['title'],
                    content=post_data['content'],
                    description=post_data['description'],
                    hashtags=post_data['hashtags'],
                    design_specs=post_data.get('design_specs', {}),  # Save AI-generated design specs
                    ai_generated=True,
                    ai_prompt=self._build_generation_prompt(company_profile, num_posts, custom_prompt),
                    scheduled_time=scheduled_time,
                    status='pending_approval',
                    requires_approval=True
                )
                created_posts.append(post)
            
            # Validate that we created posts
            if not created_posts or len(created_posts) == 0:
                logger.error(f"❌ No posts were created")
                ai_batch.status = 'generating'
                ai_batch.save()
                raise ValueError("Failed to generate posts. No posts were created. Please try again.")
            
            # Update batch status
            ai_batch.status = 'pending_approval'
            ai_batch.save()
            
            logger.info(f"✅ Successfully created {len(created_posts)} post objects")
            return ai_batch, created_posts
            
        except ValueError as ve:
            # Re-raise ValueError as-is (these are user-friendly messages)
            logger.error(f"❌ ValueError in post generation: {str(ve)}")
            ai_batch.status = 'failed'
            ai_batch.save()
            raise ve
        except Exception as e:
            logger.error(f"❌ Failed to generate posts: {str(e)}", exc_info=True)
            ai_batch.status = 'failed'
            ai_batch.save()
            raise ValueError(f"Failed to generate posts: {str(e)}")
    
    def _build_generation_prompt(self, company_profile, num_posts=5, custom_prompt=''):
        """Build comprehensive prompt for ChatGPT with ALL company information"""
        
        # Build custom instructions section if provided
        custom_instructions = ""
        if custom_prompt:
            custom_instructions = f"""
═══════════════════════════════════════════════════════════════
⭐ ƏLAVƏ XÜSUSI TƏLİMATLAR (İSTİFADƏÇİDƏN):
═══════════════════════════════════════════════════════════════
{custom_prompt}

👉 Bu xüsusi təlimatları MÜTLƏQİYYƏTLƏ nəzərə al və əsas götür!

"""
        
        # Build brand analysis section if available
        brand_info = ""
        if company_profile.brand_analysis:
            ba = company_profile.brand_analysis
            brand_info = f"""
BREND MƏLUMATLARI (Loqodan Əldə Edilib):
- Əsas Rəng: {ba.get('primary_color', 'N/A')}
- Rəng Palitrası: {', '.join(ba.get('color_palette', [])) if ba.get('color_palette') else 'N/A'}
- Dizayn Stili: {ba.get('design_style', 'N/A')}
- Brend Şəxsiyyəti: {', '.join(ba.get('brand_personality', [])) if ba.get('brand_personality') else 'N/A'}
- Emosional Ton: {ba.get('emotional_tone', 'N/A')}
- Brend Açar Sözləri: {', '.join(ba.get('brand_keywords', [])) if ba.get('brand_keywords') else 'N/A'}
"""
        
        # Build avoid topics section if specified
        avoid_info = ""
        if company_profile.avoid_topics:
            avoid_info = f"\n⚠️ QAÇINILACAQ MÖVZULAR: {', '.join(company_profile.avoid_topics)}"
        
        # Build location info if available
        location_info = f" ({company_profile.location})" if company_profile.location else ""
        
        prompt = f"""
Sən peşəkar sosial media məzmun yaradıcısısan. Aşağıdakı ŞİRKƏT HAQQINDA BÜTÜN MƏLUMATLARI DİQQƏTLƏ OXUYUB, şirkətin brend identifikasiyasına, rənglərinə, stilinə və səsləşməsinə uyğun {num_posts} ədəd sosial media postu yarat.
{custom_instructions}
═══════════════════════════════════════════════════════════════
ŞİRKƏT ƏSAS MƏLUMATLARI:
═══════════════════════════════════════════════════════════════
🏢 Şirkət Adı: {company_profile.company_name}
🏭 Sənaye: {company_profile.get_industry_display()}
👥 Şirkət Ölçüsü: {company_profile.get_company_size_display()}
📍 Yer: {company_profile.location if company_profile.location else 'Qeyd edilməyib'}{location_info}
🌐 Veb Sayt: {company_profile.website if company_profile.website else 'Yoxdur'}
{brand_info}
═══════════════════════════════════════════════════════════════
BİZNES TƏSVİRİ:
═══════════════════════════════════════════════════════════════
{company_profile.business_description}

═══════════════════════════════════════════════════════════════
HƏDƏF AUDİTORİYA:
═══════════════════════════════════════════════════════════════
{company_profile.target_audience}

═══════════════════════════════════════════════════════════════
UNİKAL SATIŞ TƏKLİFLƏRİ:
═══════════════════════════════════════════════════════════════
{company_profile.unique_selling_points}

═══════════════════════════════════════════════════════════════
SOSİAL MEDİA MƏQSƏDLƏRİ:
═══════════════════════════════════════════════════════════════
{company_profile.social_media_goals}

═══════════════════════════════════════════════════════════════
MƏZMUN STRATEGİYASI:
═══════════════════════════════════════════════════════════════
🎯 Məzmun Mövzuları: {', '.join(company_profile.content_topics) if company_profile.content_topics else 'Ümumi biznes məzmunu, sənaye yenilikləri, məhsul/xidmət təqdimatları'}
🔑 Vacib Açar Sözlər: {', '.join(company_profile.keywords) if company_profile.keywords else 'Sənayə üzrə ümumi açar sözlər'}
🎭 Üstünlük Verilən Üslub: {company_profile.get_preferred_tone_display()}
🌍 Əsas Dil: {company_profile.primary_language}{avoid_info}

═══════════════════════════════════════════════════════════════
VACİB TƏLİMATLAR:
═══════════════════════════════════════════════════════════════
1. 📝 Hər post üçün YARADICI və CƏLBEDİCİ başlıq yarat
2. 🇦🇿 Məzmun MÜTLƏQİYYƏTLƏ Azərbaycan dilində olmalıdır (latın əlifbası)
3. 📏 Hər post 150-300 söz arasında olmalıdır
4. #️⃣ Uyğun və TREND hashtaglar əlavə et (3-5 ədəd)
5. 💬 Hər post üçün qısa və dəqiq təsvir yaz
6. 🎨 Müxtəlif post növləri yarat:
   - 📢 Elanlar (announcements)
   - 📚 Təhsil və məlumat (educational)
   - 🎯 Reklam və promosyon (promotional)
   - 💬 Müzakirə və cəlb etmə (engagement)
   - 🏢 Şirkət mədəniyyəti (company culture)
   - 💡 Məsləhət və fikirlər (tips & insights)
7. 😊 Emojilər istifadə et, lakin balansda saxla (hər cümlədə yox)
8. 🎯 Hədəf auditoriyaya uyğun dil və ton istifadə et
9. 🌟 Şirkətin brend identifikasiyası, rəngləri və dizayn stilinə UYĞUN məzmun yarat
10. ✨ Şirkətin unikal satış təkliflərini və güclü tərəflərini vurğula
11. 🚫 Qaçınılacaq mövzulara toxunma
12. 📊 Hər postda dəyər təqdim et (məlumat, həll yolu, ilham, məsləhət)

JSON formatında cavab ver (markdown yox, təmiz JSON).
HƏR POST ÜÇÜN DIZAYN SPESIFIKASIYALARI DA ƏLAVƏ ET:
[
  {{
    "title": "Cəlbedici post başlığı",
    "content": "Tam post məzmunu (150-300 söz, emojilər ilə, paraqraflar şəklində)",
    "description": "Qısa təsvir (20-30 söz)",
    "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"],
    "post_type": "announcement/educational/promotional/engagement/company_culture/tips",
    "design_specs": {{
      "background_prompt": "Şəkil generasiyası üçün prompt (ingilis dilində): 'modern office with people collaborating'",
      "layout_style": "center_bold/minimal/elegant/creative/professional",
      "primary_color": "#HEXCODE (brendin əsas rəngini istifadə et)",
      "accent_color": "#HEXCODE (vurğu rəngi)",
      "title_position": "top/center/bottom",
      "title_size": 72,
      "content_position": "top/center/bottom",
      "content_size": 36,
      "overlay_color": "#000000",
      "overlay_opacity": 0.3,
      "mood": "energetic/calm/professional/playful"
    }}
  }}
]

🎨 DIZAYN QAYDALARI:
- Brendin rəng paletindən istifadə et
- Dizayn şirkətin stilinə uyğun olsun
- Hər post üçün fərqli və yaradıcı layout seç
- Şəkil promptu ingiliscə və dəqiq olsun
"""
        return prompt
    
    def _generate_posts_with_chatgpt(self, company_profile, num_posts=5, custom_prompt=''):
        """Generate posts using ChatGPT API"""
        
        logger.debug(f"📋 Building prompt for company: {company_profile.company_name}")
        prompt = self._build_generation_prompt(company_profile, num_posts, custom_prompt)
        
        try:
            logger.info(f"🔄 Sending request to OpenAI (model: gpt-4o-mini) for {num_posts} posts")
            # Increase timeout and max_tokens for larger post counts
            timeout_duration = max(120, num_posts * 15)  # At least 15 seconds per post
            max_tokens_value = max(4000, num_posts * 500)  # At least 500 tokens per post
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Using faster, cheaper model
                messages=[
                    {
                        "role": "system", 
                        "content": "Sən peşəkar Azərbaycan dilində sosial media məzmun yaradıcısısan. Həmişə JSON formatında cavab verirsən."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens_value,
                temperature=0.7,
                timeout=timeout_duration  # Dynamic timeout based on post count
            )
            
            content = response.choices[0].message.content
            logger.debug(f"📥 Received response from OpenAI: {len(content)} chars")
            
            # Strip markdown code blocks if present
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]  # Remove ```json
            if content.startswith('```'):
                content = content[3:]  # Remove ```
            if content.endswith('```'):
                content = content[:-3]  # Remove trailing ```
            content = content.strip()
            
            # Parse JSON response
            try:
                posts_data = json.loads(content)
                logger.info(f"✅ Successfully parsed {len(posts_data)} posts from JSON")
                return posts_data
            except json.JSONDecodeError as je:
                logger.error(f"❌ JSON parsing failed: {str(je)}")
                logger.debug(f"Response content: {content[:500]}")
                # If JSON parsing fails, create fallback posts
                return self._create_fallback_posts(company_profile)
                
        except openai.APITimeoutError as e:
            logger.error(f"❌ OpenAI API Timeout Error: {str(e)}")
            logger.error(f"   This might be due to generating too many posts ({num_posts}). Try generating fewer posts at once.")
            raise ValueError(f"OpenAI API timeout. Generating {num_posts} posts took too long. Please try generating fewer posts (5-7) at once or try again later.")
        except openai.APIError as e:
            logger.error(f"❌ OpenAI API Error: {str(e)}", exc_info=True)
            raise ValueError(f"OpenAI API error: {str(e)}. Please check your API key and try again.")
        except Exception as e:
            logger.error(f"❌ Unexpected error in OpenAI API call: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to generate posts: {str(e)}")
    
    def _create_fallback_posts(self, company_profile):
        """Create fallback posts if AI generation fails"""
        
        return [
            {
                "title": f"{company_profile.company_name} - Yeni Xidmətlərimiz",
                "content": f"🚀 {company_profile.company_name} olaraq, müştərilərimizə ən yaxşı xidməti təqdim etmək üçün daim inkişaf edirik.\n\n✨ Bizim üstünlüklərimiz:\n• {company_profile.unique_selling_points[:100]}...\n\nDaha ətraflı məlumat üçün bizimlə əlaqə saxlayın! 📞",
                "description": "Şirkət xidmətləri haqqında məlumat",
                "hashtags": ["#biznes", "#xidmət", "#keyfiyyət"],
                "post_type": "promotional",
                "design_specs": {
                    "background_prompt": "professional business team working together in modern office",
                    "layout_style": "professional",
                    "primary_color": "#3B82F6",
                    "accent_color": "#10B981",
                    "title_position": "center",
                    "title_size": 72,
                    "content_position": "bottom",
                    "content_size": 36,
                    "overlay_color": "#000000",
                    "overlay_opacity": 0.3,
                    "mood": "professional"
                }
            },
            {
                "title": "Sənayə Trendləri və Yeniliklər",
                "content": f"📊 {company_profile.get_industry_display()} sahəsində son trendlər:\n\n🔍 Bu həftə diqqət çəkən yeniliklər\n📈 Statistikalar göstərir ki, innovativ yanaşma 40% daha yaxşı nəticələr verir\n\n💡 Bizim rəyimiz: Gələcək artıq burada! Siz də bu dəyişikliklərin bir hissəsi olun.\n\n{company_profile.social_media_goals[:100]}...",
                "description": "Sənayə trendləri və analiz",
                "hashtags": ["#trend", "#innovasiya", "#analiz"],
                "post_type": "educational",
                "design_specs": {
                    "background_prompt": "modern technology and innovation concept with graphs and data",
                    "layout_style": "creative",
                    "primary_color": "#8B5CF6",
                    "accent_color": "#F59E0B",
                    "title_position": "top",
                    "title_size": 68,
                    "content_position": "center",
                    "content_size": 40,
                    "overlay_color": "#000000",
                    "overlay_opacity": 0.4,
                    "mood": "energetic"
                }
            }
        ]


class IdeogramService:
    """Service for Ideogram.ai image generation with text"""
    
    def __init__(self, user=None):
        self.user = user
        self.base_url = "https://api.ideogram.ai/generate"
        
        # Get Ideogram API key from settings
        self.api_key = getattr(settings, 'IDEOGRAM_API_KEY', None)
        
        # Set up headers for API requests
        self.headers = {
            'Api-Key': self.api_key,
            'Content-Type': 'application/json'
        }
        
        logger.debug(f"🎨 Ideogram service initialized with API key: {'*' * 10 if self.api_key else 'NOT SET'}")
    
    def create_design_for_post(self, post_content, company_profile=None, custom_prompt=None):
        """Generate image with Nano Banana (Fal AI) using company brand information or custom AI prompt"""
        
        # TEMPORARY: Using Nano Banana instead of Ideogram (Ideogram limit reached)
        # Ideogram code is preserved below for future use
        try:
            logger.info("🎨 Using Nano Banana (Fal AI) for image generation (Ideogram temporarily disabled)")
            
            # Import Fal AI service
            from ai_helper.fal_ai_service import FalAIService
            fal_service = FalAIService(user=self.user)
            
            # Check if Fal AI is available
            fal_api_key = getattr(settings, 'FAL_AI_API_KEY', None)
            if not fal_api_key or fal_api_key == 'your-fal-ai-api-key-here':
                logger.warning("⚠️  Fal AI API key not configured, using fallback")
                return self._create_fallback_design(post_content)
            
            # Clean and format text
            import re
            
            # Remove emojis for cleaner prompt
            emoji_pattern = re.compile("["
                                       u"\U0001F600-\U0001F64F"
                                       u"\U0001F300-\U0001F5FF"
                                       u"\U0001F680-\U0001F6FF"
                                       u"\U0001F1E0-\U0001F1FF"
                                       u"\U00002702-\U000027B0"
                                       u"\U000024C2-\U0001F251"
                                       "]+", flags=re.UNICODE)
            
            clean_content = emoji_pattern.sub('', post_content)
            clean_content = re.sub(r'\n+', ' ', clean_content)
            clean_content = re.sub(r'\s+', ' ', clean_content).strip()
            
            # Limit text for image (100 chars works best)
            if len(clean_content) > 100:
                display_text = clean_content[:97] + "..."
            else:
                display_text = clean_content
            
            logger.debug(f"📝 Post content (for context): {display_text[:50]}...")
            
            # Build brand-aware prompt using company information
            brand_style = ""
            color_palette = ""
            
            if company_profile and company_profile.brand_analysis:
                ba = company_profile.brand_analysis
                
                # Get design style
                if ba.get('design_style'):
                    brand_style = f", {ba.get('design_style')} style"
                
                # Get color scheme
                colors = []
                if ba.get('primary_color'):
                    colors.append(ba.get('primary_color'))
                if ba.get('color_palette'):
                    colors.extend(ba.get('color_palette')[:3])  # Top 3 colors
                
                if colors:
                    color_palette = f", color scheme: {' and '.join(colors)}"
                
                # Get emotional tone for better image generation
                emotional_tone = ba.get('emotional_tone', '')
                if emotional_tone:
                    brand_style += f", {emotional_tone} mood"
            
            # Get industry context
            industry_context = ""
            if company_profile:
                industry_context = f" for {company_profile.industry} industry"
            
            # Use custom AI-generated prompt if provided, otherwise create comprehensive prompt
            if custom_prompt:
                # AI already provided the perfect prompt
                prompt = (
                    f"{custom_prompt}, "
                    f"Style: photorealistic, high quality photography{brand_style}, "
                    f"professional, clean composition, modern{color_palette}, "
                    f"NO TEXT, no words, no letters anywhere in the image, "
                    f"text-free design, empty space for text overlay, "
                    f"portrait format 4:5 (1080x1350), Instagram portrait format, social media ready, "
                    f"visually appealing, engaging composition"
                )
                logger.info(f"✨ Using AI-generated prompt: {custom_prompt}")
            else:
                # Fallback to automatic prompt
                prompt = (
                    f"Create a professional social media background image about: {display_text}{industry_context}. "
                    f"Style: photorealistic, high quality photography{brand_style}, "
                    f"professional, clean composition, modern{color_palette}, "
                    f"attractive colors, well-lit, premium quality, "
                    f"NO TEXT, no words, no letters anywhere in the image, "
                    f"text-free design, empty space for text overlay, "
                    f"portrait format 4:5 (1080x1350), Instagram portrait format, social media ready, "
                    f"visually appealing, engaging composition"
                )
            
            # ==================== DETAILED LOGGING ====================
            logger.info(f"")
            logger.info(f"{'='*80}")
            logger.info(f"🎨 NANO BANANA (FAL AI) API REQUEST")
            logger.info(f"{'='*80}")
            logger.info(f"📝 Post Content: {display_text}")
            logger.info(f"")
            logger.info(f"🎯 FULL PROMPT:")
            logger.info(f"{prompt}")
            logger.info(f"{'='*80}")
            logger.info(f"📤 Sending request to Nano Banana API...")
            # =========================================================
            
            # Use Fal AI Nano Banana for text-to-image
            # Portrait format: 1080x1350 (4:5 ratio for Instagram)
            result = fal_service.text_to_image(
                prompt=prompt,
                width=1080,
                height=1350,
                num_images=1
            )
            
            if result and result.get('image_url'):
                image_url = result['image_url']
                logger.info(f"✅ SUCCESS! Image URL: {image_url}")
                logger.info(f"{'='*80}")
                logger.info(f"")
                return {
                    'design_id': result.get('job_id', ''),
                    'design_url': image_url,
                    'edit_url': '',
                    'thumbnail_url': image_url
                }
            else:
                logger.warning(f"⚠️  Nano Banana returned no image URL")
                return self._create_fallback_design(post_content)
                
        except Exception as e:
            logger.error(f"❌ Nano Banana API Error: {e}", exc_info=True)
            return self._create_fallback_design(post_content)
        
        # ========== IDEOGRAM CODE (PRESERVED FOR FUTURE USE) ==========
        # Uncomment below when Ideogram API key is available again
        """
        # ORIGINAL IDEOGRAM API CODE - PRESERVED FOR FUTURE USE
        # To use Ideogram again, replace the Nano Banana code above with this:
        
        # Check if we have API key
        if not self.api_key or self.api_key == 'your-ideogram-api-key-here':
            logger.warning("⚠️  Ideogram API key not configured, using fallback")
            return self._create_fallback_design(post_content)
        
        # Request payload for Ideogram API
        request_data = {
            "image_request": {
                "prompt": prompt,
                "aspect_ratio": "ASPECT_3_4",  # Portrait format 3:4 (1080x1440)
                "model": "V_2",  # Latest model
                "magic_prompt_option": "AUTO",  # Enhance prompt
                "style_type": "DESIGN",  # Design style (good for text)
            }
        }
        
        logger.info(f"📤 Sending request to Ideogram API...")
        
        response = requests.post(
            self.base_url,
            headers=self.headers,
            json=request_data,
            timeout=45
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('data') and len(result['data']) > 0:
                image_url = result['data'][0].get('url')
                if image_url:
                    return {
                        'design_id': result['data'][0].get('id', ''),
                        'design_url': image_url,
                        'edit_url': '',
                        'thumbnail_url': image_url
                    }
        
        return self._create_fallback_design(post_content)
        """
    
    def _create_fallback_design(self, post_content):
        """Create fallback design data when Canva API fails"""
        
        # Use Unsplash for random business/social media images
        # These are free, high-quality stock photos
        keywords = ['business', 'office', 'technology', 'team', 'success', 'growth']
        import random
        keyword = random.choice(keywords)
        
        # Unsplash Source API - free, no auth needed
        unsplash_url = f'https://source.unsplash.com/1080x1350/?{keyword},professional'
        
        logger.info(f"🖼️  Using Unsplash image: {keyword}")
        
        return {
            'design_id': '',
            'design_url': '',
            'edit_url': '',
            'thumbnail_url': unsplash_url
        }
    


class PostGenerationService:
    """Main service for generating posts with AI and Ideogram design integration"""
    
    def __init__(self, user=None):
        self.user = user
        self.openai_service = OpenAIService()
        self.ideogram_service = IdeogramService(user=user)
    
    def generate_monthly_content(self, user, custom_prompt=''):
        """Generate complete monthly content with AI and images"""
        
        logger.info(f"🎬 Starting monthly content generation for user: {user.email}")
        if custom_prompt:
            logger.info(f"📝 Custom instructions provided: {custom_prompt[:50]}...")
        
        try:
            # Get company profile
            company_profile = CompanyProfile.objects.get(user=user)
            logger.info(f"✅ Found company profile: {company_profile.company_name}")
        except CompanyProfile.DoesNotExist:
            logger.error(f"❌ No company profile found for user: {user.email}")
            raise ValueError("Company profile not found. Please complete your company information first.")
        
        # Generate posts with AI
        ai_batch, posts = self.openai_service.generate_monthly_posts(user, company_profile, custom_prompt=custom_prompt)
        logger.info(f"🎨 Starting design generation for {len(posts)} posts with Ideogram.ai")
        
        # Update ideogram service with user if not set during init
        if not self.ideogram_service.user:
            self.ideogram_service = IdeogramService(user=user)
        
        # Check if Ideogram API is configured
        ideogram_configured = bool(self.ideogram_service.api_key and 
                                   self.ideogram_service.api_key != 'your-ideogram-api-key-here')
        logger.info(f"🎨 Ideogram API status: {'Configured ✅' if ideogram_configured else 'Not configured ❌'}")
        
        # Generate Ideogram designs for each post using AI-generated design specs
        for idx, post in enumerate(posts, 1):
            try:
                logger.debug(f"🖼️  Processing design for post {idx}/{len(posts)} (ID: {post.id})")
                
                # Use AI-generated background prompt if available
                custom_prompt = None
                if post.design_specs and post.design_specs.get('background_prompt'):
                    custom_prompt = post.design_specs['background_prompt']
                    logger.info(f"🎨 Using AI-generated prompt: {custom_prompt}")
                
                design_data = self.ideogram_service.create_design_for_post(
                    post.content, 
                    company_profile,
                    custom_prompt=custom_prompt
                )
                
                # Always set at least the thumbnail (fallback or real)
                post.canva_design_id = design_data.get('design_id', '')
                post.design_url = design_data.get('design_url', '')
                post.design_thumbnail = design_data.get('thumbnail_url', '')
                
                # If no thumbnail, use a default placeholder
                if not post.design_thumbnail:
                    post.design_thumbnail = 'https://via.placeholder.com/800x800/3b82f6/ffffff?text=Click+to+Upload+Image'
                    logger.debug(f"  └─ Using placeholder image for post {post.id}")
                else:
                    logger.debug(f"  └─ Thumbnail set: {post.design_thumbnail[:60]}...")
                
                # Apply branding if enabled and image was generated
                if company_profile.branding_enabled and (post.design_url or post.design_thumbnail) and company_profile.logo:
                    try:
                        logger.info(f"🎨 Applying branding to post {post.id}")
                        logger.info(f"   Logo path: {company_profile.logo.path}")
                        logger.info(f"   Logo exists: {os.path.exists(company_profile.logo.path)}")
                        logger.info(f"   Branding mode: {company_profile.branding_mode}")
                        logger.info(f"   Design URL: {post.design_url or post.design_thumbnail}")
                        
                        from .branding import ImageBrandingService
                        from django.core.files.base import ContentFile
                        import os
                        
                        branding_service = ImageBrandingService(company_profile)
                        
                        # Use design_url if available, fallback to thumbnail
                        image_url = post.design_url or post.design_thumbnail
                        branded_image = branding_service.apply_branding(image_url)
                        output = branding_service.save_branded_image(branded_image, format='PNG')
                        
                        # Save branded image as custom_image
                        filename = f"branded_{post.id}.png"
                        post.custom_image.save(filename, ContentFile(output.read()), save=False)
                        logger.info(f"✅ Branding applied successfully to post {post.id}")
                        logger.info(f"   Branded image saved: {post.custom_image.name}")
                    except Exception as e:
                        logger.error(f"❌ BRANDING FAILED for post {post.id}: {str(e)}")
                        import traceback
                        logger.error(traceback.format_exc())
                        # Continue without branding - don't fail the whole generation
                elif company_profile.branding_enabled and not company_profile.logo:
                    logger.warning(f"⚠️  Branding enabled but no logo uploaded for user {user.email}")
                elif not company_profile.branding_enabled:
                    logger.info(f"ℹ️  Branding disabled for user {user.email}")
                
                post.save()
                
            except Exception as e:
                logger.error(f"❌ Error creating design for post {post.id}: {e}")
                # Set a fallback image even on error
                post.design_thumbnail = 'https://via.placeholder.com/800x800/3b82f6/ffffff?text=Upload+Image'
                post.save()
                continue
        
        logger.info(f"🎉 Content generation complete! Generated {len(posts)} posts")
        return ai_batch, posts
    
    def approve_post(self, post_id, user):
        """Approve a generated post"""
        
        try:
            post = Post.objects.get(id=post_id, user=user)
            post.status = 'approved'
            post.approved_by = user
            post.approved_at = timezone.now()
            post.requires_approval = False
            post.save()
            
            # Update batch statistics
            if post.ai_content_batch:
                batch = post.ai_content_batch
                batch.approved_posts = Post.objects.filter(
                    ai_content_batch=batch, 
                    status='approved'
                ).count()
                batch.save()
            
            return post
            
        except Post.DoesNotExist:
            raise ValueError("Post not found")
    
    def reject_post(self, post_id, user):
        """Reject a generated post"""
        
        try:
            post = Post.objects.get(id=post_id, user=user)
            post.status = 'cancelled'
            post.save()
            return post
            
        except Post.DoesNotExist:
            raise ValueError("Post not found")
    
    def update_post_content(self, post_id, user, updated_data):
        """Update post content after generation"""
        
        try:
            post = Post.objects.get(id=post_id, user=user)
            
            # Update fields
            if 'title' in updated_data:
                post.title = updated_data['title']
            if 'content' in updated_data:
                post.content = updated_data['content']
            if 'description' in updated_data:
                post.description = updated_data['description']
            if 'hashtags' in updated_data:
                post.hashtags = updated_data['hashtags']
            if 'scheduled_time' in updated_data:
                post.scheduled_time = updated_data['scheduled_time']
            
            post.save()
            return post
            
        except Post.DoesNotExist:
            raise ValueError("Post not found")
    
    def upload_custom_image(self, post_id, user, image_file):
        """Upload custom image for a post and auto-apply branding"""
        
        try:
            post = Post.objects.get(id=post_id, user=user)
            
            # Save image first without branding
            post.custom_image = image_file
            post.design_url = ''  # Clear Canva design when custom image is uploaded
            post.canva_design_id = ''
            post.save()  # Save first to get the file path
            
            # Auto-apply branding after upload if enabled
            try:
                from accounts.models import CompanyProfile
                company_profile = CompanyProfile.objects.get(user=user)
                
                if company_profile.branding_enabled and company_profile.logo:
                    logger.info(f"🎨 Auto-applying branding to manually uploaded image for post {post_id}")
                    from .branding import ImageBrandingService
                    from django.core.files.base import ContentFile
                    import os
                    
                    # Check if logo file exists
                    if not os.path.exists(company_profile.logo.path):
                        logger.warning(f"⚠️  Logo file not found at {company_profile.logo.path}")
                        return post
                    
                    # Check if uploaded image file exists
                    if not post.custom_image or not hasattr(post.custom_image, 'path'):
                        logger.warning(f"⚠️  Uploaded image file not found for post {post_id}")
                        return post
                    
                    try:
                        branding_service = ImageBrandingService(company_profile)
                        # Use the saved image path
                        image_path = post.custom_image.path
                        logger.info(f"   Applying branding to image: {image_path}")
                        
                        branded_image = branding_service.apply_branding(image_path)
                        output = branding_service.save_branded_image(branded_image, format='PNG')
                        
                        # Replace with branded version
                        filename = f"branded_{post.id}.png"
                        post.custom_image.save(filename, ContentFile(output.read()), save=True)
                        logger.info(f"✅ Branding auto-applied to manually uploaded image")
                    except Exception as branding_error:
                        logger.error(f"❌ Failed to apply branding: {str(branding_error)}")
                        import traceback
                        logger.error(traceback.format_exc())
                        # Continue without branding - image is still uploaded
                else:
                    logger.info(f"ℹ️  Branding skipped (enabled: {company_profile.branding_enabled}, has_logo: {bool(company_profile.logo)})")
            except CompanyProfile.DoesNotExist:
                logger.warning(f"⚠️  No company profile found for user {user.email}")
            except Exception as e:
                logger.error(f"❌ Failed to auto-apply branding: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                # Continue without branding - image is still uploaded
            
            return post
            
        except Post.DoesNotExist:
            raise ValueError("Post not found")
        except Exception as e:
            logger.error(f"❌ Error uploading custom image: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise ValueError(f"Failed to upload image: {str(e)}")


