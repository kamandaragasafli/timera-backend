"""
URL-dən məhsul məlumatlarını çəkən yardımçı funksiyalar
Web scraping və AI analiz
"""

import requests
import json
import re
import logging
from bs4 import BeautifulSoup
from django.conf import settings
import openai

logger = logging.getLogger(__name__)


def scrape_product_page(url):
    """
    Sayt səhifəsindən HTML məzmununu çəkir
    
    Args:
        url: Məhsul səhifəsinin URL-i
        
    Returns:
        dict: {
            'html': HTML məzmunu,
            'status_code': HTTP status code,
            'final_url': Final URL (redirects sonrası)
        }
    """
    try:
        # More realistic browser headers to avoid blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'az-AZ,az;q=0.9,en-US;q=0.8,en;q=0.7,tr;q=0.6,ru;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
        
        # Use session for better cookie/redirect handling
        session = requests.Session()
        session.headers.update(headers)
        
        # First request with timeout and allow redirects
        response = session.get(url, timeout=20, allow_redirects=True)
        response.raise_for_status()
        
        logger.info(f"✅ Successfully scraped: {response.url} (status: {response.status_code})")
        
        return {
            'html': response.text,
            'status_code': response.status_code,
            'final_url': response.url
        }
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            logger.error(f"403 Forbidden - Sayt scraping-i bloklamışdır: {url}")
            raise Exception(f"Sayt məlumat çəkilməsini bloklamışdır (403 Forbidden). Bu sayt üçün bu funksiya işləməyə bilər. Şəkil yükləmə metodunu istifadə edin.")
        elif e.response.status_code == 404:
            logger.error(f"404 Not Found - Səhifə tapılmadı: {url}")
            raise Exception(f"Səhifə tapılmadı (404). URL-i yoxlayın.")
        else:
            logger.error(f"HTTP error {e.response.status_code} for {url}: {str(e)}")
            raise Exception(f"Sayt açılarkən xəta: HTTP {e.response.status_code}")
    except requests.exceptions.Timeout:
        logger.error(f"Timeout error for {url}")
        raise Exception("Sayt çox uzun cavab vermir. Başqa URL sınayın.")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error for {url}: {str(e)}")
        raise Exception("İnternet bağlantısı xətası və ya sayt əlçatan deyil.")
    except Exception as e:
        logger.error(f"Scraping error for {url}: {str(e)}")
        raise


def extract_product_info_with_ai(html_content, original_url):
    """
    AI ilə HTML-dən məhsul məlumatlarını çıxarır
    
    Args:
        html_content: HTML məzmunu
        original_url: Orijinal URL (relative URL-ləri absolute-a çevirmək üçün)
        
    Returns:
        dict: Çıxarılmış məhsul məlumatları
    """
    try:
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Parse with BeautifulSoup for better structure
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Try to extract image URL directly from HTML first (Amazon-specific)
        main_image_url = None
        
        # Method 1: Look for landingImage (Amazon main product image)
        landing_img = soup.find('img', {'id': 'landingImage'})
        if landing_img:
            # Try multiple attributes for highest quality image
            main_image_url = (
                landing_img.get('data-old-hires') or 
                landing_img.get('data-a-dynamic-image') or
                landing_img.get('data-src') or
                landing_img.get('src')
            )
            if main_image_url:
                logger.info(f"Found image via landingImage: {main_image_url[:100]}...")
        
        # Method 2: Look for imgBlkFront
        if not main_image_url:
            img_blk = soup.find('img', {'id': 'imgBlkFront'})
            if img_blk:
                main_image_url = (
                    img_blk.get('data-old-hires') or 
                    img_blk.get('data-a-dynamic-image') or
                    img_blk.get('src')
                )
                if main_image_url:
                    logger.info(f"Found image via imgBlkFront: {main_image_url[:100]}...")
        
        # Method 3: Look for any image with a-dynamic-image class
        if not main_image_url:
            dynamic_img = soup.find('img', {'class': lambda x: x and 'a-dynamic-image' in str(x)})
            if dynamic_img:
                main_image_url = (
                    dynamic_img.get('data-old-hires') or 
                    dynamic_img.get('data-a-dynamic-image') or
                    dynamic_img.get('data-src') or
                    dynamic_img.get('src')
                )
                if main_image_url:
                    logger.info(f"Found image via a-dynamic-image: {main_image_url[:100]}...")
        
        # Method 4: Look for data-a-dynamic-image JSON (Amazon stores image URLs in JSON)
        if not main_image_url:
            dynamic_imgs = soup.find_all('img', {'data-a-dynamic-image': True})
            for img in dynamic_imgs:
                dynamic_data = img.get('data-a-dynamic-image')
                if dynamic_data:
                    try:
                        img_dict = json.loads(dynamic_data)
                        # Get the largest/highest quality image
                        if img_dict:
                            # Sort by size (width x height) and get largest
                            largest_url = max(img_dict.items(), key=lambda x: x[1][0] * x[1][1])[0]
                            main_image_url = largest_url
                            logger.info(f"Found image via data-a-dynamic-image JSON: {main_image_url[:100]}...")
                            break
                    except (json.JSONDecodeError, ValueError):
                        pass
        
        # Method 5: Look for Amazon media images pattern (m.media-amazon.com/images/I/)
        if not main_image_url:
            all_imgs = soup.find_all('img', src=True)
            for img in all_imgs:
                src = img.get('src', '')
                # Look for Amazon media images: m.media-amazon.com/images/I/ with _AC_ or _SL or _UL
                if 'm.media-amazon.com/images/I/' in src or '/images/I/' in src:
                    if '_AC_' in src or '_SL' in src or '_UL' in src or '_SX' in src:
                        main_image_url = src
                        logger.info(f"Found image via Amazon pattern: {main_image_url[:100]}...")
                        break
        
        # Method 6: Look for any image with /images/I/ pattern
        if not main_image_url:
            all_imgs = soup.find_all('img', src=True)
            for img in all_imgs:
                src = img.get('src', '')
                if '/images/I/' in src:
                    main_image_url = src
                    logger.info(f"Found image via /images/I/ pattern: {main_image_url[:100]}...")
                    break
        
        # Remove script, style, nav, footer tags for AI
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()
        
        # Truncate HTML to avoid token limits
        cleaned_html = str(soup)[:8000]
        
        analysis_prompt = f"""Analyze this product page HTML and extract structured information.

URL: {original_url}
{"Pre-extracted Image URL: " + main_image_url if main_image_url else ""}

HTML Content:
{cleaned_html}

Extract the following information in JSON format:
{{
    "product_name": "məhsul adı (Azərbaycan dilində tərcümə et)",
    "product_type": "məhsul növü/kateqoriyası",
    "product_description": "qısa təsvir (Azərbaycan dilində)",
    "price": "qiymət (varsa, məsələn: 299 AZN)",
    "currency": "valyuta (AZN, USD, EUR və s.)",
    "brand": "brend adı",
    "main_image_url": "{main_image_url if main_image_url else 'əsas məhsul şəklinin tam URL-i'}",
    "additional_image_urls": ["əlavə şəkil URL-ləri"],
    "features": ["xüsusiyyət 1", "xüsusiyyət 2", "xüsusiyyət 3"],
    "specifications": {{
        "color": "rəng",
        "material": "material",
        "size": "ölçü",
        "weight": "çəki"
    }},
    "availability": "mövcudluq (stokda, yoxdur və s.)",
    "rating": "reytinq (varsa)",
    "category": "kateqoriya"
}}

CRITICAL Instructions:
- {"Use the pre-extracted image URL above for main_image_url" if main_image_url else "Find the main product image URL from <img> tags"}
- Convert ALL relative URLs to absolute URLs using base: {original_url}
- Extract ACTUAL product information, ignore navigation, ads, footer content
- Translate all text fields to Azerbaijani language
- If price not found, set to null
- Return ONLY valid JSON, no additional text or markdown
- Ensure main_image_url is a complete URL starting with http:// or https://"""

        ai_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional e-commerce data extraction assistant. Extract product information from HTML and return structured JSON in Azerbaijani language."
                },
                {
                    "role": "user",
                    "content": analysis_prompt
                }
            ],
            temperature=0.2,
            max_tokens=2000
        )
        
        extracted_text = ai_response.choices[0].message.content.strip()
        
        # Clean up JSON (remove markdown code blocks if present)
        if extracted_text.startswith('```'):
            extracted_text = re.sub(r'^```json?\s*', '', extracted_text)
            extracted_text = re.sub(r'\s*```$', '', extracted_text)
        
        extracted_data = json.loads(extracted_text)
        
        # If we found image via BeautifulSoup, use it instead of AI's result
        if main_image_url:
            # Fix URL if it's relative
            from urllib.parse import urljoin
            if not main_image_url.startswith('http'):
                main_image_url = urljoin(original_url, main_image_url)
            extracted_data['main_image_url'] = main_image_url
            logger.info(f"✅ BeautifulSoup ilə şəkil tapıldı və istifadə edildi")
        
        # Validate and fix image URLs
        extracted_data = fix_image_urls(extracted_data, original_url)
        
        logger.info(f"✅ AI məhsul məlumatlarını çıxardı: {extracted_data.get('product_name', 'N/A')}")
        logger.info(f"✅ Final şəkil URL: {extracted_data.get('main_image_url', 'N/A')[:100]}...")
        
        return extracted_data
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {str(e)}")
        logger.error(f"AI response: {extracted_text[:500]}")
        raise Exception(f"AI JSON formatda cavab vermədi: {str(e)}")
    except Exception as e:
        logger.error(f"AI extraction error: {str(e)}")
        raise


def fix_image_urls(data, base_url):
    """
    Relative URL-ləri absolute URL-ə çevirir
    
    Args:
        data: Məhsul məlumatları dict
        base_url: Base URL
        
    Returns:
        dict: Düzəldilmiş məlumatlar
    """
    from urllib.parse import urljoin, urlparse
    
    # Fix main image URL
    if data.get('main_image_url'):
        img_url = data['main_image_url']
        # Only fix if it's not already absolute
        if not img_url.startswith('http://') and not img_url.startswith('https://'):
            data['main_image_url'] = urljoin(base_url, img_url)
        # Ensure it's a valid URL
        elif not img_url.startswith('http'):
            data['main_image_url'] = urljoin(base_url, img_url)
    
    # Fix additional image URLs
    if data.get('additional_image_urls'):
        fixed_urls = []
        for url in data['additional_image_urls']:
            if not url.startswith('http://') and not url.startswith('https://'):
                fixed_urls.append(urljoin(base_url, url))
            else:
                fixed_urls.append(url)
        data['additional_image_urls'] = fixed_urls
    
    return data


def download_image_from_url(image_url, headers=None):
    """
    URL-dən şəkli yükləyir
    
    Args:
        image_url: Şəkil URL-i
        headers: HTTP headers (optional)
        
    Returns:
        tuple: (image_bytes, content_type)
    """
    try:
        if headers is None:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': image_url
            }
        
        response = requests.get(image_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        content_type = response.headers.get('content-type', 'image/jpeg')
        
        return response.content, content_type
        
    except Exception as e:
        logger.error(f"Image download error for {image_url}: {str(e)}")
        raise


def validate_product_data(data):
    """
    Məhsul məlumatlarının validasiyası
    
    Args:
        data: Məhsul məlumatları dict
        
    Returns:
        tuple: (is_valid, error_message)
    """
    required_fields = ['product_name', 'main_image_url']
    
    for field in required_fields:
        if not data.get(field):
            return False, f"Tələb olunan sahə tapılmadı: {field}"
    
    # Check if image URL is valid
    image_url = data.get('main_image_url', '')
    if not image_url.startswith('http'):
        return False, f"Yanlış şəkil URL-i: {image_url}"
    
    return True, None

