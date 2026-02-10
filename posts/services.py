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
            # For 15+ posts, use batch generation to avoid timeout
            if num_posts >= 15:
                logger.info(f"📦 Large batch detected ({num_posts} posts). Using batch generation strategy...")
                posts_data = self._generate_posts_in_batches(company_profile, num_posts, custom_prompt)
            else:
                # Generate posts using ChatGPT (single request)
                logger.info(f"🤖 Calling OpenAI API for {num_posts} posts...")
                posts_data = self._generate_posts_with_chatgpt(company_profile, num_posts, custom_prompt)
                logger.info(f"✅ OpenAI returned {len(posts_data)} posts")
            
            # Check if we got fewer posts than requested
            if len(posts_data) < num_posts:
                missing_count = num_posts - len(posts_data)
                logger.warning(f"⚠️ OpenAI returned only {len(posts_data)} posts, but {num_posts} were requested. Generating {missing_count} additional posts...")
                
                # Generate additional posts to reach the requested count
                additional_posts = self._generate_additional_posts(
                    company_profile, 
                    missing_count, 
                    existing_posts=posts_data,
                    custom_prompt=custom_prompt
                )
                posts_data.extend(additional_posts)
                logger.info(f"✅ Added {len(additional_posts)} additional posts. Total: {len(posts_data)} posts")
            
            # Ensure we don't exceed the requested count (in case OpenAI returned more)
            if len(posts_data) > num_posts:
                logger.warning(f"⚠️ OpenAI returned {len(posts_data)} posts, but only {num_posts} were requested. Truncating to {num_posts} posts.")
                posts_data = posts_data[:num_posts]
            
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
Sən peşəkar sosial media məzmun yaradıcısısan. Aşağıdakı ŞİRKƏT HAQQINDA BÜTÜN MƏLUMATLARI DİQQƏTLƏ OXUYUB, şirkətin brend identifikasiyasına, rənglərinə, stilinə və səsləşməsinə uyğun DƏQİQ {num_posts} ədəd sosial media postu yarat.

⚠️ VACİB: JSON array-də DƏQİQ {num_posts} ədəd post olmalıdır. Nə az, nə də çox! Əgər {num_posts} post yarada bilmirsənsə, yenidən cəhd et.
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
⚠️ VACİB: JSON array-də DƏQİQ {num_posts} ədəd post olmalıdır. Hər post üçün DIZAYN SPESIFIKASIYALARI DA ƏLAVƏ ET:

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
  }},
  ... (DƏQİQ {num_posts} ədəd post yarat)
]

🎨 DIZAYN QAYDALARI:
- Brendin rəng paletindən istifadə et
- Dizayn şirkətin stilinə uyğun olsun
- Hər post üçün fərqli və yaradıcı layout seç
- Şəkil promptu ingiliscə və dəqiq olsun
"""
        return prompt
    
    def _generate_posts_in_batches(self, company_profile, num_posts, custom_prompt=''):
        """Generate posts in batches for large counts (15+ posts)"""
        
        logger.info(f"🔄 Starting batch generation for {num_posts} posts...")
        
        # Determine batch size (10 posts per batch is optimal)
        batch_size = 10
        num_batches = (num_posts + batch_size - 1) // batch_size  # Ceiling division
        
        all_posts = []
        
        for batch_num in range(num_batches):
            # Calculate how many posts to generate in this batch
            remaining_posts = num_posts - len(all_posts)
            current_batch_size = min(batch_size, remaining_posts)
            
            logger.info(f"📦 Batch {batch_num + 1}/{num_batches}: Generating {current_batch_size} posts...")
            
            try:
                # Generate posts for this batch
                batch_posts = self._generate_posts_with_chatgpt(
                    company_profile, 
                    current_batch_size, 
                    custom_prompt,
                    existing_posts=all_posts  # Pass existing posts to avoid duplicates
                )
                
                all_posts.extend(batch_posts)
                logger.info(f"✅ Batch {batch_num + 1} completed: {len(batch_posts)} posts generated. Total: {len(all_posts)}/{num_posts}")
                
                # Small delay between batches to avoid rate limiting
                if batch_num < num_batches - 1:
                    import time
                    time.sleep(1)
                    
            except ValueError as ve:
                # If it's a timeout error, try with smaller batch
                if "timeout" in str(ve).lower():
                    logger.warning(f"⚠️ Batch {batch_num + 1} timed out. Trying with smaller batch size (5 posts)...")
                    try:
                        # Try with smaller batch (5 posts)
                        smaller_batch_posts = self._generate_posts_with_chatgpt(
                            company_profile, 
                            5, 
                            custom_prompt,
                            existing_posts=all_posts
                        )
                        all_posts.extend(smaller_batch_posts)
                        logger.info(f"✅ Smaller batch completed: {len(smaller_batch_posts)} posts. Total: {len(all_posts)}/{num_posts}")
                    except Exception as e2:
                        logger.error(f"❌ Smaller batch also failed: {str(e2)}")
                        # Continue with next batch
                        continue
                else:
                    logger.error(f"❌ Batch {batch_num + 1} failed: {str(ve)}")
                    # Continue with next batch even if one fails
                    continue
            except Exception as e:
                logger.error(f"❌ Batch {batch_num + 1} failed: {str(e)}")
                # Continue with next batch even if one fails
                continue
        
        logger.info(f"✅ Batch generation complete: {len(all_posts)}/{num_posts} posts generated")
        return all_posts
    
    def _generate_posts_with_chatgpt(self, company_profile, num_posts=5, custom_prompt='', existing_posts=None):
        """Generate posts using ChatGPT API"""
        
        logger.debug(f"📋 Building prompt for company: {company_profile.company_name}")
        
        # If existing posts provided, mention them in prompt to avoid duplicates
        existing_context = ""
        if existing_posts and len(existing_posts) > 0:
            existing_titles = [p.get('title', '') for p in existing_posts[:5]]
            existing_context = f"\n\n⚠️ VACİB: Artıq yaradılmış postlar var. Bu postlardan FƏRQLİ olmalısan:\n" + "\n".join([f"- {title}" for title in existing_titles])
        
        prompt = self._build_generation_prompt(company_profile, num_posts, custom_prompt)
        
        # Add existing posts context if provided
        if existing_context:
            # Insert existing context after the main instruction
            prompt = prompt.replace(
                "⚠️ VACİB: JSON array-də DƏQİQ",
                f"⚠️ VACİB: JSON array-də DƏQİQ{existing_context}\n\n⚠️ VACİB: JSON array-də DƏQİQ"
            )
        
        try:
            logger.info(f"🔄 Sending request to OpenAI (model: gpt-4o-mini) for {num_posts} posts")
            # Increase timeout and max_tokens for larger post counts
            # For 20+ posts, use even more generous timeouts
            if num_posts >= 20:
                timeout_duration = max(600, num_posts * 40)  # At least 40 seconds per post for 20+
                max_tokens_value = max(16000, num_posts * 700)  # At least 700 tokens per post for 20+
            elif num_posts >= 10:
                timeout_duration = max(300, num_posts * 30)  # At least 30 seconds per post for 10+
                max_tokens_value = max(8000, num_posts * 600)  # At least 600 tokens per post for 10+
            else:
                timeout_duration = max(120, num_posts * 15)  # At least 15 seconds per post
                max_tokens_value = max(4000, num_posts * 500)  # At least 500 tokens per post
            
            logger.info(f"⏱️  Timeout set to {timeout_duration}s, max_tokens={max_tokens_value}")
            
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
            if num_posts >= 20:
                logger.error(f"   Large batch ({num_posts} posts) timed out. System will retry with batch generation.")
                raise ValueError(f"OpenAI API timeout. Generating {num_posts} posts took too long. The system will automatically retry with batch generation. Please wait...")
            else:
                logger.error(f"   This might be due to generating too many posts ({num_posts}). Try generating fewer posts at once.")
                raise ValueError(f"OpenAI API timeout. Generating {num_posts} posts took too long. Please try generating fewer posts (5-7) at once or try again later.")
        except openai.APIError as e:
            logger.error(f"❌ OpenAI API Error: {str(e)}", exc_info=True)
            raise ValueError(f"OpenAI API error: {str(e)}. Please check your API key and try again.")
        except Exception as e:
            logger.error(f"❌ Unexpected error in OpenAI API call: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to generate posts: {str(e)}")
    
    def _generate_additional_posts(self, company_profile, missing_count, existing_posts=None, custom_prompt=''):
        """Generate additional posts if OpenAI didn't return enough"""
        
        logger.info(f"🔄 Generating {missing_count} additional posts to reach target count...")
        
        # Build a focused prompt for additional posts
        existing_titles = [p.get('title', '') for p in (existing_posts or [])]
        existing_types = [p.get('post_type', '') for p in (existing_posts or [])]
        
        # Determine which post types we need more of
        post_types = ["announcement", "educational", "promotional", "engagement", "company_culture", "tips"]
        used_types = [t for t in existing_types if t in post_types]
        needed_types = [t for t in post_types if t not in used_types] or post_types
        
        additional_prompt = f"""
Sən peşəkar sosial media məzmun yaradıcısısan. Aşağıdakı şirkət haqqında {missing_count} ədəd ƏLAVƏ sosial media postu yarat.

⚠️ VACİB: Bu postlar ƏVVƏL yaradılmış postlardan FƏRQLİ olmalıdır. Mövcud postların başlıqları:
{', '.join(existing_titles[:5]) if existing_titles else 'Yoxdur'}

ŞİRKƏT MƏLUMATLARI:
🏢 Şirkət: {company_profile.company_name}
🏭 Sənaye: {company_profile.get_industry_display()}
📝 Biznes: {company_profile.business_description[:200]}...
🎯 Auditoriya: {company_profile.target_audience[:200]}...
✨ Üstünlüklər: {company_profile.unique_selling_points[:200]}...

TƏLİMATLAR:
1. Mövcud postlardan FƏRQLİ başlıq və məzmun yarat
2. Azərbaycan dilində (latın əlifbası)
3. 150-300 söz
4. 3-5 hashtag
5. Müxtəlif post növləri: {', '.join(needed_types[:missing_count])}
6. Emojilər istifadə et

JSON formatında cavab ver:
[
  {{
    "title": "Başlıq",
    "content": "Məzmun",
    "description": "Təsvir",
    "hashtags": ["#tag1", "#tag2"],
    "post_type": "announcement/educational/promotional/engagement/company_culture/tips",
    "design_specs": {{
      "background_prompt": "image prompt in English",
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
    }}
  }}
]
"""
        
        try:
            logger.info(f"🤖 Requesting {missing_count} additional posts from OpenAI...")
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Sən peşəkar Azərbaycan dilində sosial media məzmun yaradıcısısan. Həmişə JSON formatında cavab verirsən."
                    },
                    {"role": "user", "content": additional_prompt}
                ],
                max_tokens=max(4000, missing_count * 500),
                temperature=0.8,  # Slightly higher temperature for more variety
                timeout=120
            )
            
            content = response.choices[0].message.content.strip()
            
            # Strip markdown code blocks
            if content.startswith('```json'):
                content = content[7:]
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            # Parse JSON
            additional_posts = json.loads(content)
            logger.info(f"✅ Generated {len(additional_posts)} additional posts")
            
            # Ensure we return exactly the missing count
            if len(additional_posts) > missing_count:
                additional_posts = additional_posts[:missing_count]
            elif len(additional_posts) < missing_count:
                # If still not enough, create fallback posts
                logger.warning(f"⚠️ Only got {len(additional_posts)} additional posts, creating {missing_count - len(additional_posts)} fallback posts")
                fallback_posts = self._create_fallback_posts(company_profile)
                additional_posts.extend(fallback_posts[:missing_count - len(additional_posts)])
            
            return additional_posts
            
        except Exception as e:
            logger.error(f"❌ Failed to generate additional posts: {str(e)}")
            # Return fallback posts if generation fails
            fallback_posts = self._create_fallback_posts(company_profile)
            return fallback_posts[:missing_count]
    
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
            },
            {
                "title": "Müştəri Təcrübəsi və Dəyər",
                "content": f"💎 {company_profile.company_name} olaraq, hər müştəri bizim üçün dəyərlidir.\n\n🎯 Bizim missiyamız:\n• Keyfiyyətli xidmət\n• Müştəri məmnuniyyəti\n• Davamlı inkişaf\n\n📞 Bizimlə əlaqə saxlayın və fərqi hiss edin!",
                "description": "Müştəri məmnuniyyəti və dəyər",
                "hashtags": ["#müştəri", "#keyfiyyət", "#dəyər"],
                "post_type": "engagement",
                "design_specs": {
                    "background_prompt": "happy customers and professional service team interaction",
                    "layout_style": "elegant",
                    "primary_color": "#10B981",
                    "accent_color": "#3B82F6",
                    "title_position": "top",
                    "title_size": 70,
                    "content_position": "center",
                    "content_size": 38,
                    "overlay_color": "#000000",
                    "overlay_opacity": 0.25,
                    "mood": "calm"
                }
            },
            {
                "title": "Şirkət Mədəniyyəti və Komanda",
                "content": f"👥 {company_profile.company_name} komandası olaraq, birgə işləməkdən qürur duyuruq.\n\n🌟 Bizim dəyərlərimiz:\n• Komanda ruhu\n• İnnovasiya\n• Davamlı təhsil\n• Müştəri fokusu\n\n💼 Bizimlə işləmək istəyirsiniz? Bizimlə əlaqə saxlayın!",
                "description": "Şirkət mədəniyyəti və komanda",
                "hashtags": ["#komanda", "#mədəniyyət", "#iş"],
                "post_type": "company_culture",
                "design_specs": {
                    "background_prompt": "diverse team of professionals collaborating in modern workspace",
                    "layout_style": "minimal",
                    "primary_color": "#6366F1",
                    "accent_color": "#EC4899",
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
                "title": "Məsləhət və Fikirlər",
                "content": f"💡 {company_profile.get_industry_display()} sahəsində uğur üçün məsləhətlər:\n\n✅ Daim yenilikləri izləyin\n✅ Müştəri geri bildirimlərini dinləyin\n✅ Komanda ilə birgə işləyin\n✅ Keyfiyyətə fokuslanın\n\n🎯 Bu prinsiplər {company_profile.company_name} üçün də vacibdir!",
                "description": "Sənayə üzrə məsləhətlər",
                "hashtags": ["#məsləhət", "#uğur", "#biznes"],
                "post_type": "tips",
                "design_specs": {
                    "background_prompt": "lightbulb ideas and professional business tips concept",
                    "layout_style": "creative",
                    "primary_color": "#F59E0B",
                    "accent_color": "#8B5CF6",
                    "title_position": "top",
                    "title_size": 68,
                    "content_position": "center",
                    "content_size": 40,
                    "overlay_color": "#000000",
                    "overlay_opacity": 0.35,
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
        """Generate image using Fal.ai NANO BANANA"""
        
        logger.info("🍌 Using Fal.ai NANO BANANA for AI image generation")
        
        try:
            # Get Fal.ai API key from settings
            fal_api_key = getattr(settings, 'FAL_AI_API_KEY', None)
            
            if not fal_api_key or fal_api_key == 'your-fal-api-key-here':
                logger.warning("⚠️  Fal.ai API key not configured, using fallback")
                return self._create_fallback_design(post_content)
            
            # Build a prompt for image generation
            if custom_prompt:
                prompt = custom_prompt
            else:
                # Clean and format text to extract keywords
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
                
                # Build image prompt from content
                prompt = f"Professional social media image: {clean_content[:200]}"
                
                # Add industry context if available
                if company_profile:
                    industry = company_profile.get_industry_display() if hasattr(company_profile, 'get_industry_display') else company_profile.industry
                    if industry and industry != 'N/A':
                        prompt = f"{industry} style. {prompt}"
            
            logger.info(f"🔍 Generating image with NANO BANANA")
            logger.info(f"📝 Full prompt (first 300 chars): {prompt[:300]}")
            logger.info(f"📝 Full prompt length: {len(prompt)} characters")
            
            # Call Fal.ai NANO BANANA API
            fal_url = "https://fal.run/fal-ai/nano-banana"
            headers = {
                'Authorization': f'Key {fal_api_key}',
                'Content-Type': 'application/json'
            }
            payload = {
                "prompt": prompt,
                "image_size": "landscape_16_9",
                "num_images": 1
            }
            
            logger.info(f"📤 Sending request to NANO BANANA API...")
            # Timeout set to 60 seconds - Fal.ai can be slow
            response = requests.post(fal_url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                
                # Get image URL from response
                if result.get('images') and len(result['images']) > 0:
                    image_data = result['images'][0]
                    image_url = image_data.get('url')
                    
                    if image_url:
                        logger.info(f"✅ NANO BANANA API success! Image URL: {image_url}")
                        return {
                            'design_id': result.get('request_id', ''),
                            'design_url': image_url,
                            'edit_url': '',
                            'thumbnail_url': image_url
                        }
                else:
                    logger.warning(f"⚠️  NANO BANANA API returned no images")
            else:
                logger.warning(f"⚠️  NANO BANANA API returned status {response.status_code}: {response.text}")
            
            # Fallback if Nano Banana fails
            return self._create_fallback_design(post_content)
                
        except requests.Timeout:
            logger.warning(f"⏱️  NANO BANANA API timeout (60s). Using fallback image.")
            return self._create_fallback_design(post_content)
        except Exception as e:
            logger.error(f"❌ Error in NANO BANANA image generation: {e}", exc_info=True)
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
    
    def _create_fallback_design(self, post_content, search_query=None):
        """Create fallback design using Picsum Photos (free, no API key needed)"""
        
        # Unsplash Source API is deprecated (503 errors)
        # Use Picsum Photos instead - free, reliable, no API key needed
        import random
        
        # Generate random image ID for variety (1-1000)
        image_id = random.randint(1, 1000)
        
        # Picsum Photos - free random images, reliable service
        # Format: 1080x1350 (Instagram portrait format)
        # Use seed for consistent images per post
        picsum_url = f'https://picsum.photos/seed/{image_id}/1080/1350'
        
        logger.info(f"🖼️  Using Picsum Photos (fallback): image_id={image_id}")
        
        return {
            'design_id': str(image_id),
            'design_url': picsum_url,
            'edit_url': '',
            'thumbnail_url': picsum_url
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
        # For 30+ posts, skip image generation to avoid timeout - images can be generated later
        # Limit increased to allow image generation for batches up to 30 posts
        skip_images = len(posts) >= 30
        if skip_images:
            logger.info(f"⚠️  Skipping image generation for {len(posts)} posts to avoid timeout. Images can be generated later.")
        
        for idx, post in enumerate(posts, 1):
            try:
                logger.info(f"🖼️  Processing design for post {idx}/{len(posts)} (ID: {post.id})")
                
                # Skip image generation for large batches
                if skip_images:
                    logger.info(f"⏭️  Skipping image generation for post {idx}/{len(posts)}")
                    post.design_thumbnail = 'https://via.placeholder.com/800x800/3b82f6/ffffff?text=Image+Will+Be+Generated+Later'
                    post.save()
                    continue
                
                # Use AI-generated background prompt if available
                custom_prompt = None
                if post.design_specs and post.design_specs.get('background_prompt'):
                    custom_prompt = post.design_specs['background_prompt']
                    logger.info(f"🎨 Using AI-generated prompt: {custom_prompt}")
                
                logger.info(f"🔄 Starting image generation for post {idx}/{len(posts)}...")
                design_data = self.ideogram_service.create_design_for_post(
                    post.content, 
                    company_profile,
                    custom_prompt=custom_prompt
                )
                logger.info(f"✅ Image generation completed for post {idx}/{len(posts)}")
                
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
            
            # Data retention policy: Check user preference or default to immediate deletion
            # For now, we'll mark as cancelled and let a cleanup task handle deletion
            # This allows for data retention policy configuration
            post.status = 'cancelled'
            post.save()
            
            # Note: Actual deletion should be handled by a scheduled task
            # based on data retention policy (immediately or after X days)
            
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


