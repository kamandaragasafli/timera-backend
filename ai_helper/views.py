from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view, permission_classes
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import openai
import logging
import re
import base64
import io
import uuid
import requests
import json
from datetime import datetime
from PIL import Image
import sys

logger = logging.getLogger(__name__)

# Safe logging function for Windows console
def safe_log_error(logger_func, message, *args, **kwargs):
    """Safely log error messages that may contain Unicode characters"""
    try:
        logger_func(message, *args, **kwargs)
    except UnicodeEncodeError:
        # Fallback: encode to ASCII with replacement
        safe_message = message.encode('ascii', errors='replace').decode('ascii')
        logger_func(safe_message, *args, **kwargs)

# Optional: Fal.ai service for video generation
try:
    from .fal_ai_service import FalAIService
    # Try to import FAL_CLIENT_AVAILABLE if it exists
    try:
        from .fal_ai_service import FAL_CLIENT_AVAILABLE
    except ImportError:
        FAL_CLIENT_AVAILABLE = True  # Assume available if we can import FalAIService
    FAL_AI_AVAILABLE = True
except ImportError as e:
    FAL_AI_AVAILABLE = False
    FalAIService = None
    FAL_CLIENT_AVAILABLE = False
    safe_log_error(logger.warning, f"  FalAIService import edilə bilmədi: {e}")

# Optional: BeautifulSoup for web scraping
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    BeautifulSoup = None


def detect_language(text):
    """Detect if text is in Azerbaijani or English"""
    if not text:
        return 'az'  # Default to Azerbaijani
    
    # Azerbaijani specific characters
    az_chars = ['ə', 'ı', 'ö', 'ü', 'ğ', 'ş', 'ç', 'Ə', 'İ', 'Ö', 'Ü', 'Ğ', 'Ş', 'Ç']
    
    # Common Azerbaijani words
    az_words = ['və', 'üçün', 'ilə', 'olan', 'məs', 'şirkət', 'biznes', 'şirkətiniz']
    
    # Check for Azerbaijani characters
    has_az_chars = any(char in text for char in az_chars)
    
    # Check for Azerbaijani words
    has_az_words = any(word in text.lower() for word in az_words)
    
    if has_az_chars or has_az_words:
        return 'az'
    
    return 'en'


class GenerateContentView(APIView):
    """Generate AI content using OpenAI for various purposes"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            prompt = request.data.get('prompt')
            content_type = request.data.get('content_type', 'general')
            
            if not prompt:
                return Response({
                    'error': 'Prompt is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Detect language from the prompt
            language = detect_language(prompt)
            
            # Initialize OpenAI client
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            
            logger.info(f"🤖 Generating AI content for user: {request.user.email}, type: {content_type}, language: {language}")
            
            # Set system message based on language and content type
            if language == 'az':
                system_message = """Siz peşəkar biznes məsləhətçisi və marketinq ekspertisiniz. 
Azərbaycan dilində dəqiq, professional və faydalı cavablar verirsiniz.

Qaydalar:
1. Yalnız tələb olunan məzmunu verin, əlavə izahat və ya giriş sözləri yazmayın
2. Təbii və professional ton istifadə edin
3. Konkret və dəqiq olun
4. Cavabı təmiz formatda verin (lazım olduqda vergüllə ayrılmış)

Xarakter limitləri:
- Qısa mətnlər (keywords, topics): 100-200 simvol
- Orta mətnlər (descriptions): 200-500 simvol
- Uzun mətnlər (detailed descriptions): 300-800 simvol"""
            else:
                system_message = """You are a professional business consultant and marketing expert.
You provide accurate, professional, and helpful responses in English.

Rules:
1. Provide only the requested content, no extra explanations or introductions
2. Use natural and professional tone
3. Be specific and accurate
4. Return clean formatted content (comma-separated when needed)

Character limits:
- Short texts (keywords, topics): 100-200 characters
- Medium texts (descriptions): 200-500 characters
- Long texts (detailed descriptions): 300-800 characters"""
            
            # Call OpenAI ChatGPT
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Fast and cost-effective
                messages=[
                    {
                        "role": "system",
                        "content": system_message
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,  # Balanced creativity
                max_tokens=600,  # Enough for detailed responses
                presence_penalty=0.1,  # Slight penalty for repetition
                frequency_penalty=0.1  # Encourage variety
            )
            
            generated_content = response.choices[0].message.content.strip()
            
            # Remove quotes if AI added them
            generated_content = generated_content.strip('"\'')
            
            logger.info(f" Successfully generated content for user: {request.user.email} ({len(generated_content)} chars)")
            
            return Response({
                'content': generated_content,
                'generated_content': generated_content,
                'status': 'success',
                'language': language,
                'char_count': len(generated_content)
            }, status=status.HTTP_200_OK)
            
        except openai.APIError as e:
            logger.error(f" OpenAI API error: {str(e)}")
            return Response({
                'error': 'OpenAI API error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f" Error generating content: {str(e)}", exc_info=True)
            return Response({
                'error': f'Failed to generate content: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OptimizeForPlatformView(APIView):
    """Optimize content for specific social media platforms"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            content = request.data.get('content')
            platform = request.data.get('platform', 'general')
            
            if not content:
                return Response({
                    'error': 'Content is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Detect language
            language = detect_language(content)
            
            # Initialize OpenAI client
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            
            if language == 'az':
                system_message = "Siz sosial media ekspertisiniz. Məzmunu platformalara uyğunlaşdırırsınız."
                prompt = f"""Aşağıdakı məzmunu {platform} platforması üçün optimallaşdırın.
Platform xüsusiyyətlərinə uyğun formatda yazın.

Məzmun: {content}

Cavab yalnız optimallaşdırılmış məzmun olmalıdır."""
            else:
                system_message = "You are a social media expert. You optimize content for different platforms."
                prompt = f"""Optimize the following content for {platform} platform.
Format it according to the platform's best practices.

Content: {content}

Provide only the optimized content."""
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": system_message
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=400
            )
            
            optimized_content = response.choices[0].message.content.strip()
            optimized_content = optimized_content.strip('"\'')
            
            return Response({
                'content': optimized_content,
                'status': 'success',
                'language': language
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f" Error optimizing content: {str(e)}", exc_info=True)
            return Response({
                'error': f'Failed to optimize content: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AnalyzeLogoView(APIView):
    """Analyze company logo with AI to extract brand information"""
    
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        try:
            logo_file = request.FILES.get('logo')
            
            if not logo_file:
                return Response({
                    'error': 'Logo file is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info(f" Analyzing logo for user: {request.user.email}")
            
            # Get company context if available
            company_name = request.data.get('company_name', '')
            industry = request.data.get('industry', '')
            business_desc = request.data.get('business_description', '')
            
            # Build context string
            context_info = ""
            if company_name or industry or business_desc:
                context_info = "\n\nCOMPANY CONTEXT:\n"
                if company_name:
                    context_info += f"Company Name: {company_name}\n"
                if industry:
                    context_info += f"Industry: {industry}\n"
                if business_desc:
                    context_info += f"Business: {business_desc}\n"
                context_info += "\nUse this context to provide more accurate brand analysis.\n"
            
            # Read and encode image
            image_data = logo_file.read()
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Initialize OpenAI client
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Create detailed prompt for logo analysis
            prompt = f"""You are a brand identity expert. Analyze this image (company logo, brand image, or any design) and extract brand information.
{context_info}

Even if the image is simple, abstract, or not a traditional logo, provide your best analysis based on what you see.

Return ONLY a valid JSON object with this structure (no explanations, no markdown, no code blocks):

{{
  "primary_color": "#HEXCODE of dominant color",
  "secondary_colors": ["#HEX1", "#HEX2"],
  "color_palette": ["#HEX1", "#HEX2", "#HEX3", "#HEX4"],
  "design_style": "describe the visual style (e.g., modern, minimalist, bold, elegant, playful)",
  "logo_type": "wordmark, symbol, combination, emblem, lettermark, or abstract",
  "brand_personality": ["3-5 personality traits like professional, friendly, innovative"],
  "emotional_tone": "the emotional feeling (e.g., confident, energetic, calm, playful)",
  "industry_vibe": "what industry this suggests (tech, creative, corporate, etc.)",
  "font_style": "if text visible, describe it; otherwise say 'No text visible'",
  "typography_suggestions": {{
    "headings": "recommended font style for headings",
    "body": "recommended font style for body text"
  }},
  "complementary_colors": ["#HEX1", "#HEX2", "#HEX3"],
  "brand_keywords": ["5-7 descriptive keywords about the visual identity"]
}}

IMPORTANT: 
- Analyze ANY image provided, even if it's not a perfect logo
- Always return valid JSON
- Use your best judgment to extract colors and suggest hex codes
- Be creative but professional in your analysis"""
            
            # Call OpenAI Vision API
            # Use gpt-4o which supports vision
            logger.info(f"Calling OpenAI Vision API with image size: {len(image_data)} bytes")
            
            response = client.chat.completions.create(
                model="gpt-4o",  # Supports vision
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1500,
                temperature=0.5
            )
            
            logger.info(f"Received response from OpenAI")
            
            # Check if response is valid
            if not response.choices or len(response.choices) == 0:
                raise ValueError("No response from OpenAI")
            
            # Parse the response
            analysis_text = response.choices[0].message.content
            
            if not analysis_text:
                raise ValueError("Empty response from OpenAI")
            
            analysis_text = analysis_text.strip()
            
            logger.info(f"Raw AI response length: {len(analysis_text)} chars")
            logger.info(f"Raw AI response preview: {analysis_text[:200]}...")
            
            # Remove markdown code blocks if present
            if '```' in analysis_text:
                # Extract content between ``` markers
                parts = analysis_text.split('```')
                if len(parts) >= 3:
                    analysis_text = parts[1]
                    # Remove 'json' or 'JSON' prefix if present
                    if analysis_text.lower().startswith('json'):
                        analysis_text = analysis_text[4:]
                elif len(parts) == 2:
                    analysis_text = parts[1]
            
            analysis_text = analysis_text.strip()
            
            # Parse JSON
            try:
                brand_analysis = json.loads(analysis_text)
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract JSON object manually
                import re
                json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
                if json_match:
                    analysis_text = json_match.group(0)
                    brand_analysis = json.loads(analysis_text)
                else:
                    # AI refused to analyze - create a default response
                    logger.warning(f"AI refused to analyze, creating fallback response")
                    brand_analysis = {
                        "primary_color": "#3B82F6",
                        "secondary_colors": ["#1E40AF", "#60A5FA"],
                        "color_palette": ["#3B82F6", "#1E40AF", "#60A5FA", "#DBEAFE"],
                        "design_style": "Could not analyze - please try a different image",
                        "logo_type": "Unknown",
                        "brand_personality": ["Professional", "Modern", "Trustworthy"],
                        "emotional_tone": "Professional and approachable",
                        "industry_vibe": "General business",
                        "font_style": "No text visible or unable to analyze",
                        "typography_suggestions": {
                            "headings": "Modern sans-serif like Inter or Roboto",
                            "body": "Clean sans-serif like Open Sans"
                        },
                        "complementary_colors": ["#10B981", "#F59E0B", "#8B5CF6"],
                        "brand_keywords": ["Professional", "Modern", "Business", "Clean", "Digital"],
                        "note": "This is a default analysis. Please try uploading a clearer logo image for better results."
                    }
            
            logger.info(f" Successfully analyzed logo for user: {request.user.email}")
            
            return Response({
                'brand_analysis': brand_analysis,
                'status': 'success'
            }, status=status.HTTP_200_OK)
            
        except json.JSONDecodeError as e:
            logger.error(f" JSON parsing error: {str(e)}")
            logger.error(f"Response text: {analysis_text if 'analysis_text' in locals() else 'No response'}")
            return Response({
                'error': 'Failed to parse AI response',
                'details': str(e),
                'raw_response': analysis_text[:500] if 'analysis_text' in locals() else 'No response'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except ValueError as e:
            logger.error(f" Validation error: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except openai.APIError as e:
            logger.error(f" OpenAI API error: {str(e)}")
            return Response({
                'error': f'OpenAI API error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f" Error analyzing logo: {str(e)}", exc_info=True)
            return Response({
                'error': f'Failed to analyze logo: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# WASK.CO AI LOGO & SLOGAN GENERATOR
# ============================================================================

def scrape_website_info(url):
    """Web saytdan məlumat çıxarır"""
    if not BS4_AVAILABLE:
        raise ValueError("Web scraping əlçatan deyil. beautifulsoup4 paketi install edilməyib.")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract information
        title = soup.find('title')
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        og_title = soup.find('meta', attrs={'property': 'og:title'})
        og_desc = soup.find('meta', attrs={'property': 'og:description'})
        
        # Extract main content
        h1 = soup.find('h1')
        paragraphs = soup.find_all('p')[:3]
        
        # Priority: OG tags > Meta tags > HTML tags
        product_name = ''
        if og_title:
            product_name = og_title.get('content', '')
        elif title:
            product_name = title.text.strip()
        elif h1:
            product_name = h1.text.strip()
        
        product_description = ''
        if og_desc:
            product_description = og_desc.get('content', '')
        elif meta_desc:
            product_description = meta_desc.get('content', '')
        else:
            product_description = ' '.join([p.text.strip() for p in paragraphs if p.text.strip()])[:500]
        
        if not product_name or not product_description:
            raise ValueError("Saytdan kifayət qədər məlumat çıxarıla bilmədi")
        
        return {
            'product_name': product_name[:255],  # Limit length
            'product_description': product_description,
            'url': url
        }
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Sayta müraciət edilə bilmədi: {str(e)}")
    except Exception as e:
        raise ValueError(f"Saytdan məlumat çıxarıla bilmədi: {str(e)}")


def upload_product_image(image_file, user_id):
    """Məhsul şəklini yükləyir"""
    ext = image_file.name.split('.')[-1].lower()
    filename = f"logos/user_{user_id}_{uuid.uuid4()}.{ext}"
    path = default_storage.save(filename, ContentFile(image_file.read()))
    return default_storage.url(path)


def call_wask_api(product_name, product_description, style='minimalist', color='#3B82F6', tags=None, image_url=None):
    """
    AI ilə logo və slogan yaradır (təsvir əsasında)
    """
    if tags is None:
        tags = []
    try:
        import openai
        from openai import OpenAI
        
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        if not settings.OPENAI_API_KEY:
            raise ValueError("API key konfiqurasiya edilməyib")
        
        # Generate slogan (Azərbaycan dilində)
        logger.info("📝 Slogan yaradılır (Azərbaycan dilində)...")
        slogan_prompt = f"""Bu şirkət/məhsul üçün güclü, yadda qalan slogan yarat:

Ad: {product_name}
Təsvir: {product_description}

Tələblər:
- Qısa və yadda qalan (3-7 söz)
- Professional və ilhamverici
- Azərbaycan dilində
- Brendin mahiyyətini əks etdirən

YALNIZ sloganı qaytar, başqa heç nə yazma."""

        slogan_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": slogan_prompt}],
            max_tokens=50,
            temperature=0.9
        )
        
        slogan_raw = slogan_response.choices[0].message.content.strip()
        # Remove quotes if present
        slogan = slogan_raw.strip('"').strip("'").strip()
        
        # Validate slogan
        if not slogan or len(slogan) < 3:
            logger.warning(f" Slogan çox qısadır: '{slogan}'. Default slogan istifadə olunur.")
            slogan = f"Empower Your Business"  # Fallback slogan
        
        logger.info(f" Slogan yaradıldı: '{slogan}'")
        
        # Generate logo with style and color options
        logger.info(f" Logo yaradılır ({style} stilində, {color} rəngində)...")
        
        # Style descriptions
        style_descriptions = {
            'minimalist': 'Extremely simple, minimal details, clean lines',
            'elegant': 'Refined, sophisticated, graceful design',
            'modern': 'Contemporary, dynamic, forward-thinking',
            'professional': 'Business-oriented, trustworthy, corporate',
            'playful': 'Fun, vibrant, colorful, energetic'
        }
        
        style_desc = style_descriptions.get(style, 'simple and clean')
        
        # Category-specific icon suggestions (Azərbaycan dilində)
        category_icons = {
            'Təhsil': 'book, pen, graduation cap, school, education symbol, learning icon, academic symbol',
            'Tech': 'computer, code brackets, circuit, technology symbol, digital icon, microchip, tech gear',
            'Finans': 'money symbol, dollar sign, coin, financial graph, banking icon, currency, finance symbol',
            'Sağlamlıq': 'medical cross, heart, health symbol, medicine icon, wellness symbol, healthcare',
            'E-commerce': 'shopping cart, bag, package, delivery icon, online shopping symbol, ecommerce',
            'Xidmət': 'customer service, handshake, support icon, service symbol, help icon, service badge',
            'İstehsal': 'factory, gear, manufacturing symbol, production icon, industry symbol, factory icon',
            'Daşınmaz Əmlak': 'house, building, key, real estate symbol, property icon, home symbol',
            'Marketing': 'megaphone, target, marketing symbol, advertising icon, promotion, marketing badge',
            'Dizayn': 'paint brush, palette, design tools, creative symbol, art icon, design symbol',
            'Mətbəx': 'chef hat, cooking pot, fork and knife, food icon, restaurant symbol, kitchen icon',
            'Moda': 'hanger, fashion symbol, clothing icon, style symbol, accessory, fashion badge',
            'İdman': 'ball, trophy, fitness symbol, sport icon, athletic symbol, sports icon',
            'Səyahət': 'airplane, map, compass, travel symbol, journey icon, suitcase, travel icon',
            'İncəsənət': 'paint brush, palette, art symbol, creative icon, gallery symbol, art badge'
        }
        
        # Map English category names to Azerbaijani (if needed)
        category_mapping = {
            'Tech': 'Tech',
            'Finans': 'Finans',
            'Sağlamlıq': 'Sağlamlıq',
            'Təhsil': 'Təhsil',
            'E-commerce': 'E-commerce',
            'Xidmət': 'Xidmət',
            'İstehsal': 'İstehsal',
            'Daşınmaz Əmlak': 'Daşınmaz Əmlak',
            'Marketing': 'Marketing',
            'Dizayn': 'Dizayn',
            'Mətbəx': 'Mətbəx',
            'Moda': 'Moda',
            'İdman': 'İdman',
            'Səyahət': 'Səyahət',
            'İncəsənət': 'İncəsənət'
        }
        
        # Build category-specific icon suggestions
        icon_suggestions = []
        for tag in tags:
            if tag in category_icons:
                icons = category_icons[tag]
                icon_suggestions.append(f"- {tag} category: Can incorporate elements like {icons}")
        
        tags_context = ''
        if tags:
            tags_context = f"\n\nCategories/Industries: {', '.join(tags)}"
            if icon_suggestions:
                tags_context += f"\n\nCategory Context (use as inspiration, not literal):\n"
                tags_context += "\n".join(icon_suggestions)
                tags_context += f"\n\nImportant: Create a simple, abstract icon that represents the essence of these categories. For example, if 'Təhsil' (Education) is selected, create a simple educational icon/symbol inspired by education concept - NOT literally showing books or pens as the logo shape, but a cohesive simple symbol that represents education. The logo should be relevant to the categories but remain a unified, simple icon design."
        
        # Convert hex color to descriptive name for better AI understanding
        color_names = {
            '#3B82F6': 'bright blue',
            '#8B5CF6': 'vibrant purple',
            '#EF4444': 'vivid red',
            '#10B981': 'fresh green',
            '#F59E0B': 'warm orange',
            '#6366F1': 'deep indigo',
            '#000000': 'solid black',
            '#FFFFFF': 'pure white'
        }
        color_name = color_names.get(color, 'bright blue')
        
        logo_prompt = f"""Create a {style} logo icon for {product_name} in {color_name} color. 

Company/Brand: {product_name}
Business Description: {product_description}
{tags_context}

CRITICAL DESIGN REQUIREMENTS:
1. The logo MUST visually represent the business based on the description: "{product_description}"
2. If categories are selected, the logo design should be inspired by and relevant to those categories
3. The logo should be a simple, unified icon that represents the business - NOT multiple separate objects or literal representations
4. For example, if "Təhsil" (Education) category is selected, create a simple educational icon/symbol - NOT a literal book shape, but a simple symbol that represents education/learning
5. The design should capture the essence and meaning of the categories, creating a meaningful symbol, not showing literal objects
6. Create a cohesive, simple icon that represents the business and categories conceptually

CRITICAL COLOR REQUIREMENTS:
- The entire logo icon MUST be {color_name} colored (hex code: {color})
- Use {color} as the primary and dominant color for all logo elements
- The logo should be in {color_name} color, NOT multicolor
- Background MUST be completely transparent (PNG format)
- Only the logo icon itself should be {color_name}, everything else transparent

Style: {style_desc}

Requirements:
- {style} design style
- Logo icon in {color_name} color ({color})
- Single cohesive icon design, no text
- Simple, clean design that clearly represents the business
- MUST be relevant to both the description and selected categories
- Include appropriate icons/elements from the categories if selected
- Completely transparent background (PNG format)
- Professional quality
- The logo icon itself should be {color_name} colored, background completely transparent"""

        logo_response = client.images.generate(
            model="dall-e-3",
            prompt=logo_prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )
        
        logo_url = logo_response.data[0].url
        logger.info(f" Logo yaradıldı")
        
        return {
            'logo_url': logo_url,
            'slogan': slogan,
            'request_id': f'openai_{logo_response.created}'
        }
        
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        raise Exception(f"Logo və slogan yaradıla bilmədi: {str(e)}")


def download_and_save_logo(logo_url, user_id):
    """Logo yükləyib transparent background ilə saxlayır"""
    try:
        logger.info(f"📥 Logo yüklənir: {logo_url}")
        response = requests.get(logo_url, timeout=30)
        response.raise_for_status()
        
        # Load image with PIL
        from PIL import Image
        import io
        
        logo_image = Image.open(io.BytesIO(response.content))
        
        # Convert to RGBA if not already
        if logo_image.mode != 'RGBA':
            logo_image = logo_image.convert('RGBA')
        
        # Remove white/light background and make transparent
        logger.info("🔄 Arxa fon transparent edilir...")
        
        # Get image dimensions
        width, height = logo_image.size
        
        # Create new image with transparent background
        transparent_logo = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        
        # Process each pixel
        for x in range(width):
            for y in range(height):
                r, g, b, a = logo_image.getpixel((x, y))
                
                # If pixel is white or very light (background), make it transparent
                # Threshold: if all RGB values are above 240, consider it background
                if r > 240 and g > 240 and b > 240:
                    transparent_logo.putpixel((x, y), (0, 0, 0, 0))
                else:
                    # Keep original pixel with full opacity
                    transparent_logo.putpixel((x, y), (r, g, b, 255))
        
        logo_image = transparent_logo
        
        # Save transparent logo to memory
        output = io.BytesIO()
        logo_image.save(output, format='PNG', optimize=True)
        output.seek(0)
        
        # Save to storage
        filename = f"generated_logos/user_{user_id}_{uuid.uuid4()}.png"
        path = default_storage.save(filename, ContentFile(output.read()))
        
        logger.info(f" Transparent logo saxlandı")
        return default_storage.url(path)
    except Exception as e:
        logger.error(f" Logo yüklənmədi: {e}")
        raise Exception(f"Logo yüklənə bilmədi: {str(e)}")


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_logo_slogan(request):
    """
    Wask.co AI istifadə edərək logo və slogan yaradır
    
    Modes:
    - Manual: product_name + product_description (+ optional image)
    - Link: product_link (auto-scrapes website)
    """
    user = request.user
    
    # Get inputs
    product_name = request.data.get('product_name') or request.POST.get('product_name')
    product_description = request.data.get('product_description') or request.POST.get('product_description')
    style = request.data.get('style') or request.POST.get('style', 'minimalist')
    color = request.data.get('color') or request.POST.get('color', '#3B82F6')
    tags = request.data.get('tags') or request.POST.getlist('tags') or []
    
    # Validation
    if not product_name or not product_description:
        return Response({
            "error": "product_name və product_description tələb olunur"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        logger.info(f" Logo və slogan yaratma başladı - User: {user.email}")
        logger.info(f"   Şirkət: {product_name}")
        logger.info(f"   Stil: {style}")
        logger.info(f"   Rəng: {color}")
        logger.info(f"   Tags: {tags}")
        
        # Logo və slogan yaradılır
        logger.info(f" Logo və slogan yaradılır...")
        wask_response = call_wask_api(
            product_name=product_name,
            product_description=product_description,
            style=style,
            color=color,
            tags=tags,
            image_url=None
        )
        
        # Generated logo
        wask_logo_url = wask_response.get('logo_url')
        if not wask_logo_url:
            raise ValueError("Logo yaradıla bilmədi")
        
        logger.info(f" Logo yüklənir...")
        saved_logo_url = download_and_save_logo(wask_logo_url, user.id)
        
        # Convert to absolute URL
        if not saved_logo_url.startswith('http'):
            saved_logo_url = request.build_absolute_uri(saved_logo_url)
        
        logger.info(f" Logo uğurla yaradıldı")
        logger.info(f"   Logo URL: {saved_logo_url}")
        logger.info(f"   Slogan: {wask_response.get('slogan', 'YOX')}")
        logger.info(f"   Product Name: {product_name}")
        
        # Return response
        response_data = {
            "logo_url": saved_logo_url,
            "slogan": wask_response.get('slogan', ''),
            "metadata": {
                "product_name": product_name,
                "generated_at": datetime.now().isoformat(),
                "request_id": wask_response.get('request_id', '')
            }
        }
        
        logger.info(f"📤 Response göndərilir: slogan={bool(response_data['slogan'])}, logo_url={bool(response_data['logo_url'])}")
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except ValueError as e:
        logger.error(f" Validation error: {str(e)}")
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except requests.exceptions.RequestException as e:
        logger.error(f" Wask.co API error: {str(e)}")
        return Response({
            "error": "Wask.co AI xidməti müvəqqəti olaraq əlçatan deyil",
            "wask_error": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f" Unexpected error: {str(e)}", exc_info=True)
        return Response({
            "error": "Logo və slogan yaratma zamanı xəta baş verdi",
            "details": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# AI AD CREATIVE GENERATOR
# ============================================================================

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_ad_creative(request):
    """
    AI ilə professional reklam şəkli yaradır (Fal.ai Flux + Web Scraping)
    Şirkətin mövcud logo və slogan-ını istifadə edir (yeni yaratmır!)
    
    Input:
    - product_name: Məhsul adı
    - product_description: Məhsul təsviri
    - product_link: Məhsul link-i (scraping üçün)
    - product_image: Məhsul şəkli (optional)
    - ad_format: social_square | story | landscape | portrait
    - style: modern | professional | playful | elegant
    - target_audience: Hədəf auditoriya (optional)
    - apply_branding: true/false (company logo+slogan əlavə edilsin?)
    
    Output:
    - ad_image_url: Reklam şəkli (company logo+slogan ilə)
    - ad_copy: Reklam mətni
    - headline: Başlıq
    - hashtags: Hashtag-lar
    """
    try:
        # Get inputs - support both request.data and request.POST for FormData
        product_name = request.data.get('product_name') or request.POST.get('product_name')
        product_description = request.data.get('product_description') or request.POST.get('product_description')
        product_link = request.data.get('product_link') or request.POST.get('product_link')
        product_image = request.FILES.get('product_image')
        ad_format = request.data.get('ad_format') or request.POST.get('ad_format', 'social_square')
        style = request.data.get('style') or request.POST.get('style', 'modern')
        target_audience = request.data.get('target_audience') or request.POST.get('target_audience')
        
        # Debug logging
        logger.info(f"📥 Received request data:")
        logger.info(f"   product_name: {product_name}")
        logger.info(f"   product_description: {product_description}")
        logger.info(f"   product_link: {product_link}")
        logger.info(f"   ad_format: {ad_format}")
        logger.info(f"   style: {style}")
        logger.info(f"   has_product_image: {bool(product_image)}")
        
        # Validation
        if not product_link and (not product_name or not product_description):
            logger.error(" Validation failed: Missing required fields")
            return Response({
                "error": "product_name və product_description və ya product_link tələb olunur",
                "received": {
                    "product_name": product_name,
                    "product_description": product_description,
                    "product_link": product_link
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate ad format
        from .ad_creative import AdCreativeGenerator
        if ad_format not in AdCreativeGenerator.FORMATS:
            return Response({
                "error": f"Ad format düzgün deyil. Mövcud formatlar: {', '.join(AdCreativeGenerator.FORMATS.keys())}"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info(f" Ad creative generation started")
        logger.info(f"   Product: {product_name or 'from link'}")
        logger.info(f"   Format: {ad_format}")
        logger.info(f"   Style: {style}")
        
        # Link mode: Scrape website
        if product_link:
            logger.info(f"   Scraping: {product_link}")
            if not product_link.startswith('http'):
                product_link = 'https://' + product_link
            
            scraped = scrape_website_info(product_link)
            product_name = scraped['product_name']
            product_description = scraped['product_description']
        
        # Upload product image if provided
        product_image_url = None
        if product_image:
            logger.info(f"   Uploading product image...")
            product_image_url = upload_product_image(product_image, request.user.id)
            if not product_image_url.startswith('http'):
                product_image_url = request.build_absolute_uri(product_image_url)
        
        # Generate ad creative with Fal.ai
        generator = AdCreativeGenerator(user=request.user)
        try:
            result = generator.generate_ad_creative(
                product_name=product_name,
                product_description=product_description,
                ad_format=ad_format,
                style=style,
                target_audience=target_audience,
                product_image_url=product_image_url,
                product_url=product_link  # Pass the product URL for scraping
            )
        except ValueError as ve:
            # Handle scraping failures
            logger.error(f" ValueError: {str(ve)}")
            return Response({
                "error": str(ve),
                "suggestion": "Link işləmədi. Zəhmət olmasa Manuel rejimə keçin və məhsul məlumatlarını daxil edin."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Convert relative URL to absolute
        if not result['ad_image_url'].startswith('http'):
            result['ad_image_url'] = request.build_absolute_uri(result['ad_image_url'])
        
        # Apply company branding (logo + slogan from CompanyProfile)
        apply_branding = request.data.get('apply_branding', 'true').lower() == 'true'
        
        if apply_branding:
            try:
                from accounts.models import CompanyProfile
                from posts.branding import ImageBrandingService
                from posts.models import Post
                
                company_profile = CompanyProfile.objects.get(user=request.user)
                
                if company_profile.branding_enabled and company_profile.logo:
                    logger.info(f" Applying company branding to ad creative...")
                    logger.info(f"   Company logo: {company_profile.logo.name}")
                    logger.info(f"   Company slogan: {company_profile.slogan or 'None'}")
                    
                    # Create temporary post to use existing branding system
                    temp_post = Post.objects.create(
                        user=request.user,
                        content=result['ad_copy'],
                        status='draft',
                        title='Ad Creative'
                    )
                    
                    # Download ad image and save to temp post
                    if result['ad_image_url'].startswith('http'):
                        ad_img_response = requests.get(result['ad_image_url'], timeout=10)
                        from django.core.files.base import ContentFile
                        temp_post.custom_image.save(
                            f"temp_ad_{uuid.uuid4()}.png",
                            ContentFile(ad_img_response.content),
                            save=True
                        )
                    
                    # Apply branding using existing system
                    branding_service = ImageBrandingService(company_profile)
                    branded_image = branding_service.apply_branding(temp_post.custom_image.path)
                    output = branding_service.save_branded_image(branded_image, format='PNG')
                    
                    # Save branded version
                    branded_filename = f"ad_creatives/branded_ad_{uuid.uuid4()}.png"
                    branded_path = default_storage.save(branded_filename, ContentFile(output.read()))
                    result['ad_image_url'] = request.build_absolute_uri(default_storage.url(branded_path))
                    
                    # Clean up temp post
                    temp_post.delete()
                    
                    logger.info(f" Company branding applied to ad creative!")
                else:
                    logger.info(f"Branding skipped (enabled: {company_profile.branding_enabled}, has_logo: {bool(company_profile.logo)})")
                    
            except CompanyProfile.DoesNotExist:
                logger.warning(f"  No company profile - skipping branding")
            except Exception as e:
                logger.error(f"  Failed to apply branding: {e}")
                # Continue without branding
        
        logger.info(f" Ad creative generation complete!")
        
        return Response({
            "ad_image_url": result['ad_image_url'],
            "ad_copy": result['ad_copy'],
            "headline": result.get('headline', ''),
            "hashtags": result.get('hashtags', []),
            "cta": result.get('cta', 'Learn More'),
            "metadata": {
                "product_name": product_name,
                "format": ad_format,
                "style": style,
                "branding_applied": apply_branding,
                "generated_at": datetime.now().isoformat()
            }
        }, status=status.HTTP_200_OK)
        
    except ValueError as e:
        logger.error(f" Validation error: {str(e)}")
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f" Ad creative generation error: {str(e)}", exc_info=True)
        return Response({
            "error": "Reklam şəkli yaratma zamanı xəta baş verdi",
            "details": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def image_to_video(request):
    """
    Convert image to video using Fal.ai Kling Video model
    
    POST /api/ai/fal-ai/image-to-video/
    
    Body:
    {
        "image_url": "https://example.com/image.jpg",
        "prompt": "Optional: describe the video motion",
        "duration": 5,  # Optional: video duration in seconds (default: 5)
        "fps": 24  # Optional: frames per second (default: 24)
    }
    
    Returns:
    {
        "video_url": "https://...",
        "status": "completed",
        "job_id": "..."
    }
    """
    user = request.user
    
    try:
        image_url = request.data.get('image_url')
        if not image_url:
            return Response({
                "error": "image_url tələb olunur"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        prompt = request.data.get('prompt')
        duration = request.data.get('duration', 5)
        fps = request.data.get('fps', 24)
        
        logger.info(f" Image-to-video request from user: {user.email}")
        logger.info(f"   Image URL: {image_url}")
        logger.info(f"   Prompt: {prompt}")
        
        # Check if Fal.ai service is available
        if not FAL_AI_AVAILABLE:
            return Response({
                "error": "Fal.ai service mövcud deyil. Zəhmət olmasa fal-client paketi install edin: pip install fal-client"
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Initialize Fal.ai service
        try:
            fal_service = FalAIService(user=user)
        except ImportError as import_err:
            safe_log_error(logger.error, f" FalAIService import error: {str(import_err)}")
            return Response({
                "error": f"Fal.ai service başlatıla bilmədi: {str(import_err)}"
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Convert image to video
        result = fal_service.image_to_video(
            image_url=image_url,
            prompt=prompt,
            duration=duration,
            fps=fps
        )
        
        # Optionally download and save video
        save_to_storage = request.data.get('save_to_storage', False)
        if save_to_storage:
            saved_url = fal_service.download_and_save(
                result['video_url'],
                user.id,
                prefix="fal_ai_videos"
            )
            result['saved_video_url'] = saved_url
        
        return Response({
            "success": True,
            "video_url": result['video_url'],
            "status": result['status'],
            "job_id": result['job_id'],
            "saved_video_url": result.get('saved_video_url')
        }, status=status.HTTP_200_OK)
        
    except ValueError as e:
        logger.error(f" Validation error: {str(e)}")
        return Response({
            "error": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except TimeoutError as e:
        logger.error(f"  Timeout error: {str(e)}")
        return Response({
            "error": "Video yaratma zamanı gözləmə müddəti bitdi. Zəhmət olmasa, yenidən cəhd edin."
        }, status=status.HTTP_504_GATEWAY_TIMEOUT)
    except Exception as e:
        logger.error(f" Image-to-video error: {str(e)}", exc_info=True)
        return Response({
            "error": "Video yaratma zamanı xəta baş verdi",
            "details": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def edit_image(request):
    """
    Edit image using Fal.ai Nano Banana Pro model
    
    POST /api/ai/fal-ai/edit-image/
    
    Body:
    {
        "image_url": "https://example.com/image.jpg",
        "prompt": "Make the background blue, add sunset",
        "strength": 0.8  # Optional: edit strength 0.0-1.0 (default: 0.8)
    }
    
    Returns:
    {
        "image_url": "https://...",
        "status": "completed",
        "job_id": "..."
    }
    """
    user = request.user
    
    try:
        image_url = request.data.get('image_url')
        prompt = request.data.get('prompt')
        
        if not image_url:
            return Response({
                "error": "image_url tələb olunur"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not prompt:
            return Response({
                "error": "prompt tələb olunur (şəkildə nə dəyişiklik etmək istəyirsən?)"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        strength = float(request.data.get('strength', 0.8))
        strength = max(0.0, min(1.0, strength))  # Clamp between 0 and 1
        
        logger.info(f" Image edit request from user: {user.email}")
        logger.info(f"   Image URL: {image_url}")
        logger.info(f"   Prompt: {prompt}")
        logger.info(f"   Strength: {strength}")
        
        # Check if Fal.ai service is available
        if not FAL_AI_AVAILABLE:
            return Response({
                "error": "Fal.ai service mövcud deyil. Zəhmət olmasa fal-client paketi install edin: pip install fal-client"
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Initialize Fal.ai service
        try:
            fal_service = FalAIService(user=user)
        except ImportError as import_err:
            safe_log_error(logger.error, f" FalAIService import error: {str(import_err)}")
            return Response({
                "error": f"Fal.ai service başlatıla bilmədi: {str(import_err)}"
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Edit image
        result = fal_service.edit_image(
            image_url=image_url,
            prompt=prompt,
            strength=strength
        )
        
        # Optionally download and save image
        save_to_storage = request.data.get('save_to_storage', False)
        if save_to_storage:
            saved_url = fal_service.download_and_save(
                result['image_url'],
                user.id,
                prefix="fal_ai_edited"
            )
            result['saved_image_url'] = saved_url
        
        return Response({
            "success": True,
            "image_url": result['image_url'],
            "status": result['status'],
            "job_id": result['job_id'],
            "saved_image_url": result.get('saved_image_url')
        }, status=status.HTTP_200_OK)
        
    except ValueError as e:
        logger.error(f" Validation error: {str(e)}")
        return Response({
            "error": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except TimeoutError as e:
        logger.error(f"  Timeout error: {str(e)}")
        return Response({
            "error": "Şəkil redaktəsi zamanı gözləmə müddəti bitdi. Zəhmət olmasa, yenidən cəhd edin."
        }, status=status.HTTP_504_GATEWAY_TIMEOUT)
    except Exception as e:
        logger.error(f" Image edit error: {str(e)}", exc_info=True)
        return Response({
            "error": "Şəkil redaktəsi zamanı xəta baş verdi",
            "details": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def nano_banana_text_to_image(request):
    """
    Generate image from text using Fal.ai Nano Banana model
    
    POST /api/ai/fal-ai/nano-banana/text-to-image/
    
    Body:
    {
        "prompt": "A beautiful sunset over mountains",
        "product_name": "Optional product name for context",
        "product_description": "Optional product description for context",
        "width": 1024,  # Optional
        "height": 1024,  # Optional
        "enhance_prompt": true  # Optional: enhance prompt with AI (default: true)
    }
    
    Returns:
    {
        "image_url": "https://...",
        "status": "completed",
        "job_id": "...",
        "enhanced_prompt": "..."
    }
    """
    user = request.user
    
    try:
        prompt = request.data.get('prompt')
        if not prompt:
            return Response({
                "error": "prompt tələb olunur"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        product_name = request.data.get('product_name')
        product_description = request.data.get('product_description')
        width = int(request.data.get('width', 1024))
        height = int(request.data.get('height', 1024))
        enhance_prompt = request.data.get('enhance_prompt', True)
        
        logger.info(f" Nano Banana text-to-image request from user: {user.email}")
        logger.info(f"   Prompt: {prompt}")
        
        # Check if Fal.ai service is available
        if not FAL_AI_AVAILABLE:
            return Response({
                "error": "Fal.ai service mövcud deyil. Zəhmət olmasa fal-client paketi install edin: pip install fal-client"
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Initialize Fal.ai service
        try:
            fal_service = FalAIService(user=user)
        except ImportError as import_err:
            safe_log_error(logger.error, f" FalAIService import error: {str(import_err)}")
            return Response({
                "error": f"Fal.ai service başlatıla bilmədi: {str(import_err)}"
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Enhance prompt if requested
        enhanced_prompt = prompt
        if enhance_prompt:
            enhanced_prompt = fal_service.enhance_prompt(
                prompt,
                product_name=product_name,
                product_description=product_description,
                context="ad_creative"
            )
        
        # Generate image
        result = fal_service.text_to_image(
            prompt=enhanced_prompt,
            width=width,
            height=height
        )
        
        # Optionally download and save image
        save_to_storage = request.data.get('save_to_storage', False)
        if save_to_storage:
            saved_url = fal_service.download_and_save(
                result['image_url'],
                user.id,
                prefix="nano_banana_generated"
            )
            result['saved_image_url'] = saved_url
        
        return Response({
            "success": True,
            "image_url": result['image_url'],
            "status": result['status'],
            "job_id": result['job_id'],
            "enhanced_prompt": enhanced_prompt if enhance_prompt else None,
            "saved_image_url": result.get('saved_image_url')
        }, status=status.HTTP_200_OK)
        
    except ValueError as e:
        logger.error(f" Validation error: {str(e)}")
        return Response({
            "error": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except TimeoutError as e:
        logger.error(f"  Timeout error: {str(e)}")
        return Response({
            "error": "Şəkil yaratma zamanı gözləmə müddəti bitdi. Zəhmət olmasa, yenidən cəhd edin."
        }, status=status.HTTP_504_GATEWAY_TIMEOUT)
    except Exception as e:
        logger.error(f" Text-to-image error: {str(e)}", exc_info=True)
        return Response({
            "error": "Şəkil yaratma zamanı xəta baş verdi",
            "details": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def nano_banana_image_to_image(request):
    """
    Transform image using Fal.ai Nano Banana model (image-to-image)
    
    POST /api/ai/fal-ai/nano-banana/image-to-image/
    
    Body:
    {
        "image_url": "https://example.com/image.jpg",
        "prompt": "Make it more vibrant, add professional lighting",
        "product_name": "Optional product name for context",
        "product_description": "Optional product description for context",
        "strength": 0.8,  # Optional: transformation strength 0.0-1.0 (default: 0.8)
        "enhance_prompt": true  # Optional: enhance prompt with AI (default: true)
    }
    
    Returns:
    {
        "image_url": "https://...",
        "status": "completed",
        "job_id": "...",
        "enhanced_prompt": "..."
    }
    """
    user = request.user
    
    try:
        image_url = request.data.get('image_url')
        prompt = request.data.get('prompt')
        
        if not image_url:
            return Response({
                "error": "image_url tələb olunur"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not prompt:
            return Response({
                "error": "prompt tələb olunur"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        product_name = request.data.get('product_name')
        product_description = request.data.get('product_description')
        strength = float(request.data.get('strength', 0.8))
        strength = max(0.0, min(1.0, strength))  # Clamp between 0 and 1
        enhance_prompt = request.data.get('enhance_prompt', True)
        
        logger.info(f" Nano Banana image-to-image request from user: {user.email}")
        logger.info(f"   Image URL: {image_url}")
        logger.info(f"   Prompt: {prompt}")
        
        # Check if Fal.ai service is available
        if not FAL_AI_AVAILABLE:
            return Response({
                "error": "Fal.ai service mövcud deyil. Zəhmət olmasa fal-client paketi install edin: pip install fal-client"
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Initialize Fal.ai service
        try:
            fal_service = FalAIService(user=user)
        except ImportError as import_err:
            safe_log_error(logger.error, f" FalAIService import error: {str(import_err)}")
            return Response({
                "error": f"Fal.ai service başlatıla bilmədi: {str(import_err)}"
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Enhance prompt if requested
        enhanced_prompt = prompt
        if enhance_prompt:
            enhanced_prompt = fal_service.enhance_prompt(
                prompt,
                product_name=product_name,
                product_description=product_description,
                context="ad_creative"
            )
        
        # Transform image
        result = fal_service.image_to_image(
            image_url=image_url,
            prompt=enhanced_prompt,
            strength=strength
        )
        
        # Optionally download and save image
        save_to_storage = request.data.get('save_to_storage', False)
        if save_to_storage:
            saved_url = fal_service.download_and_save(
                result['image_url'],
                user.id,
                prefix="nano_banana_transformed"
            )
            result['saved_image_url'] = saved_url
        
        return Response({
            "success": True,
            "image_url": result['image_url'],
            "status": result['status'],
            "job_id": result['job_id'],
            "enhanced_prompt": enhanced_prompt if enhance_prompt else None,
            "saved_image_url": result.get('saved_image_url')
        }, status=status.HTTP_200_OK)
        
    except ValueError as e:
        logger.error(f" Validation error: {str(e)}")
        return Response({
            "error": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except TimeoutError as e:
        logger.error(f"  Timeout error: {str(e)}")
        return Response({
            "error": "Şəkil transformasiyası zamanı gözləmə müddəti bitdi. Zəhmət olmasa, yenidən cəhd edin."
        }, status=status.HTTP_504_GATEWAY_TIMEOUT)
    except Exception as e:
        logger.error(f" Image-to-image error: {str(e)}", exc_info=True)
        return Response({
            "error": "Şəkil transformasiyası zamanı xəta baş verdi",
            "details": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def kling_video_text_to_video(request):
    """
    Generate video from text using Fal.ai Kling Video model
    
    POST /api/ai/fal-ai/kling-video/text-to-video/
    
    Body:
    {
        "prompt": "A beautiful sunset over mountains with birds flying",
        "product_name": "Optional product name for context",
        "product_description": "Optional product description for context",
        "duration": 5,  # Optional: video duration in seconds (default: 5)
        "fps": 24,  # Optional: frames per second (default: 24)
        "width": 1024,  # Optional
        "height": 576,  # Optional
        "enhance_prompt": true  # Optional: enhance prompt with AI (default: true)
    }
    
    Returns:
    {
        "video_url": "https://...",
        "status": "completed",
        "job_id": "...",
        "enhanced_prompt": "..."
    }
    """
    user = request.user
    
    try:
        prompt = request.data.get('prompt')
        if not prompt:
            return Response({
                "error": "prompt tələb olunur"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        product_name = request.data.get('product_name')
        product_description = request.data.get('product_description')
        duration = int(request.data.get('duration', 5))
        fps = int(request.data.get('fps', 24))
        width = int(request.data.get('width', 1024))
        height = int(request.data.get('height', 576))
        enhance_prompt = request.data.get('enhance_prompt', True)
        
        logger.info(f" Kling Video text-to-video request from user: {user.email}")
        logger.info(f"   Prompt: {prompt}")
        
        # Check if Fal.ai service is available
        if not FAL_AI_AVAILABLE:
            return Response({
                "error": "Fal.ai service mövcud deyil. Zəhmət olmasa fal-client paketi install edin: pip install fal-client"
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Initialize Fal.ai service
        try:
            fal_service = FalAIService(user=user)
        except ImportError as import_err:
            safe_log_error(logger.error, f" FalAIService import error: {str(import_err)}")
            return Response({
                "error": f"Fal.ai service başlatıla bilmədi: {str(import_err)}"
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Enhance prompt if requested
        enhanced_prompt = prompt
        if enhance_prompt:
            enhanced_prompt = fal_service.enhance_prompt(
                prompt,
                product_name=product_name,
                product_description=product_description,
                context="video"
            )
        
        # Generate video
        result = fal_service.text_to_video(
            prompt=enhanced_prompt,
            duration=duration,
            fps=fps,
            width=width,
            height=height
        )
        
        # Optionally download and save video
        save_to_storage = request.data.get('save_to_storage', False)
        if save_to_storage:
            saved_url = fal_service.download_and_save(
                result['video_url'],
                user.id,
                prefix="kling_video_generated"
            )
            result['saved_video_url'] = saved_url
        
        return Response({
            "success": True,
            "video_url": result['video_url'],
            "status": result['status'],
            "job_id": result['job_id'],
            "enhanced_prompt": enhanced_prompt if enhance_prompt else None,
            "saved_video_url": result.get('saved_video_url')
        }, status=status.HTTP_200_OK)
        
    except ValueError as e:
        logger.error(f" Validation error: {str(e)}")
        return Response({
            "error": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except TimeoutError as e:
        logger.error(f"  Timeout error: {str(e)}")
        return Response({
            "error": "Video yaratma zamanı gözləmə müddəti bitdi. Zəhmət olmasa, yenidən cəhd edin."
        }, status=status.HTTP_504_GATEWAY_TIMEOUT)
    except Exception as e:
        logger.error(f" Text-to-video error: {str(e)}", exc_info=True)
        return Response({
            "error": "Video yaratma zamanı xəta baş verdi",
            "details": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

