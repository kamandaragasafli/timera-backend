"""
AI Ad Creative Generator
Creates professional advertising images with product placement using Fal.ai
"""

from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings
import io
import os
import uuid
import requests
import logging
import json
from openai import OpenAI
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

# Fal.ai import (optional)
try:
    import fal_client  # type: ignore
    FAL_AI_AVAILABLE = True
except ImportError:
    FAL_AI_AVAILABLE = False
    fal_client = None  # type: ignore


class AdCreativeGenerator:
    """Generate professional ad creatives with AI"""
    
    # Ad format specifications
    FORMATS = {
        'social_square': {'width': 1080, 'height': 1350, 'name': 'Instagram/Facebook Square'},
        'story': {'width': 1080, 'height': 1920, 'name': 'Instagram/Facebook Story'},
        'landscape': {'width': 1200, 'height': 628, 'name': 'Facebook/LinkedIn Landscape'},
        'portrait': {'width': 1080, 'height': 1350, 'name': 'Instagram Portrait'},
    }
    
    def __init__(self, user=None):
        """Initialize generator"""
        self.user = user
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.fal_api_key = getattr(settings, "FAL_AI_API_KEY", None)

        # Fal.ai üçün env dəyişəni burada 1 dəfə set edirik
        if FAL_AI_AVAILABLE and self.fal_api_key:
            # Əgər artıq başqa yerdə set olunmayıbsa, yazırıq
            os.environ.setdefault("FAL_API_KEY", self.fal_api_key)
            logger.info("Fal.ai API key configured (FAL_API_KEY)")
        elif FAL_AI_AVAILABLE and not self.fal_api_key:
            logger.warning("Fal.ai client var, amma FAL_AI_API_KEY settings-də tapılmadı.")
        else:
            logger.info("Fal.ai client import olunmayıb, yalnız DALL-E istifadə ediləcək.")
    
    def generate_ad_creative(
        self,
        product_name,
        product_description,
        ad_format='social_square',
        style='modern',
        target_audience=None,
        product_image_url=None,
        product_url=None,
        logo_url=None
    ):
        """
        Generate complete ad creative
        
        Args:
            product_url: Optional URL to scrape product info from
            logo_url: Optional logo URL to place on the ad
        
        Returns: {
            'ad_image_url': str,
            'ad_copy': str,
            'headline': str,
            'hashtags': list,
            'cta': str
        }
        """
        logger.info(f"Generating ad creative: {product_name}")
        
        # If product URL is provided, scrape the information
        if product_url:
            scraped_data = self._scrape_product_info(product_url)
            if scraped_data:
                # Update with scraped data
                product_name = scraped_data.get('name', product_name) or product_name
                product_description = scraped_data.get('description', product_description) or product_description
                product_image_url = scraped_data.get('image_url', product_image_url)
                logo_url = scraped_data.get('logo_url', logo_url)
                logger.info("Scraped product info from URL")
            else:
                logger.warning("Could not scrape URL - will need manual input")
                if not product_name or not product_description:
                    raise ValueError(
                        "Saytdan məlumat əldə edilə bilmədi. "
                        "Zəhmət olmasa məhsul adı və təsvirini manual daxil edin."
                    )
        
        # Get format specs
        format_specs = self.FORMATS.get(ad_format, self.FORMATS['social_square'])
        width, height = format_specs['width'], format_specs['height']
        
        # Generate ad copy first
        ad_copy_data = self._generate_ad_copy(
            product_name, product_description, target_audience
        )
        
        # DEBUG: Check Fal.ai availability
        logger.info(f"DEBUG: FAL_AI_AVAILABLE = {FAL_AI_AVAILABLE}")
        logger.info(f"DEBUG: self.fal_api_key = {bool(self.fal_api_key)}")
        logger.info(f"DEBUG: product_image_url = {product_image_url}")
        
        # Fal.ai varsa ondan, yoxdursa DALL-E 3-dən istifadə et
        if FAL_AI_AVAILABLE and self.fal_api_key:
            logger.info("Fal.ai is available!")
            
            if product_image_url:
                # Image-to-image edit
                logger.info("Using Nano Banana Pro EDIT for image-to-image transformation")
                background_url = self._transform_with_nano_banana(
                    product_image_url, product_name, product_description, style, width, height
                )
            else:
                # Heç bir product image yoxdursa, birbaşa text-to-image Nano Banana Pro istifadə edə bilərik
                logger.info("No product image – using Nano Banana Pro text-to-image")
                background_url = self._generate_background_fal(
                    product_name, product_description, style, width, height
                )
        else:
            if not FAL_AI_AVAILABLE:
                logger.error("Fal.ai client not available! fal_client paketi install olunmayıb!")
            if not self.fal_api_key:
                logger.error("Fal.ai API key not configured (FAL_AI_API_KEY yoxdur)!")
            logger.warning("Using DALL-E 3 fallback")
            background_url = self._generate_background_dalle(
                product_name, product_description, style, width, height
            )
        
        # Download background
        background_img = self._download_image(background_url)
        
        # Resize to exact format
        background_img = background_img.resize((width, height), Image.Resampling.LANCZOS)
        
        # If product image provided, composite it
        if product_image_url:
            try:
                product_img = self._download_image(product_image_url)
                background_img = self._composite_product(background_img, product_img)
            except Exception as e:
                logger.warning(f"Failed to composite product image: {e}")
        
        # If logo provided, add it
        if logo_url:
            try:
                logo_img = self._download_image(logo_url)
                background_img = self._add_logo(background_img, logo_img)
            except Exception as e:
                logger.warning(f"Failed to add logo: {e}")
        
        # Add text overlay if needed
        if ad_copy_data.get('headline'):
            background_img = self._add_text_overlay(
                background_img, ad_copy_data['headline']
            )
        
        # Save final image
        output = io.BytesIO()
        background_img.save(output, format='PNG', optimize=True)
        output.seek(0)
        
        # Upload to storage
        filename = f"ad_creatives/user_{self.user.id if self.user else 'demo'}_{uuid.uuid4()}.png"
        path = default_storage.save(filename, ContentFile(output.read()))
        ad_image_url = default_storage.url(path)
        
        logger.info(f"Ad creative generated: {ad_image_url}")
        
        return {
            'ad_image_url': ad_image_url,
            'ad_copy': ad_copy_data['copy'],
            'headline': ad_copy_data.get('headline', ''),
            'hashtags': ad_copy_data.get('hashtags', []),
            'cta': ad_copy_data.get('cta', 'Learn More'),
        }
    
    def _generate_ad_copy(self, product_name, product_description, target_audience=None):
        """Generate ad copy with GPT-4o-mini"""
        logger.info("Generating ad copy with GPT-4o-mini...")
        
        audience_text = f"\nTarget Audience: {target_audience}" if target_audience else ""
        
        prompt = f"""Create compelling advertising copy for this product:

Product: {product_name}
Description: {product_description}{audience_text}

Generate:
1. Headline (5-7 words, attention-grabbing)
2. Main copy (2-3 sentences, persuasive)
3. Call-to-action (3-4 words)
4. 5 relevant hashtags

Format as JSON:
{{
  "headline": "...",
  "copy": "...",
  "cta": "...",
  "hashtags": ["#...", "#...", "..."]
}}"""
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.8
        )
        
        result = json.loads(response.choices[0].message.content)
        logger.info("Ad copy generated")
        return result
    
    def _transform_with_nano_banana(self, input_image_url, product_name, product_description, style, width, height):
        """Transform image with Nano Banana Pro (Image Editing Model)"""
        logger.info("Transforming image with Nano Banana Pro EDIT...")
        logger.info(f"   Input image: {input_image_url}")
        logger.info(f"   Product: {product_name}")
        logger.info(f"   Style: {style}")
        
        prompt = (
            f"Transform this into a professional product advertisement for {product_name}. "
            f"Style: {style}, clean composition, commercial quality, professional lighting, "
            f"advertising photography aesthetic."
        )
        
        logger.info(f"   Prompt: {prompt}")
        
        try:
            def on_queue_update(update):
                if isinstance(update, fal_client.InProgress):
                    for log in update.logs:
                        logger.info(f"   {log['message']}")
            
            logger.info("   Calling Nano Banana Pro EDIT API...")
            
            result = fal_client.subscribe(
                "fal-ai/nano-banana-pro/edit",  # IMAGE EDITING model
                arguments={
                    "prompt": prompt,
                    "image_urls": [input_image_url],  # Input image REQUIRED
                    "aspect_ratio": "auto",
                    "resolution": "1K",  # 1K, 2K, or 4K
                    "num_images": 1,
                    "output_format": "png"
                },
                with_logs=True,
                on_queue_update=on_queue_update
            )
            
            url = result['images'][0]['url']
            logger.info("Image transformed with Nano Banana Pro")
            return url
            
        except Exception as e:
            logger.error(f"Nano Banana Pro failed: {e}")
            logger.info("Returning original image URL...")
            return input_image_url
    
    def _generate_background_fal(self, product_name, product_description, style, width, height):
        """Generate ad background with Fal.ai (Nano Banana Pro - Product Photography)"""
        logger.info("Generating professional product ad with Fal.ai Nano Banana Pro (text-to-image)...")
        
        style_keywords = {
            'modern': 'sleek, contemporary, minimalist, clean lines, futuristic',
            'professional': 'corporate, business, sophisticated, formal, premium quality',
            'playful': 'vibrant, fun, energetic, colorful, dynamic, youthful',
            'elegant': 'luxury, refined, sophisticated, classy, premium, high-end',
            'minimalist': 'simple, clean, white space, minimal, subtle, zen'
        }
        
        style_desc = style_keywords.get(style, 'modern professional')
        
        prompt = f"""Professional product photography for {product_name}. 

{product_description}

Clean studio background, {style_desc}, professional lighting, minimal composition, commercial quality, no clutter, simple and elegant."""
        try:
            def on_queue_update(update):
                if isinstance(update, fal_client.InProgress):
                    for log in update.logs:
                        logger.info(f"   {log['message']}")
            
            result = fal_client.subscribe(
                "fal-ai/nano-banana-pro",  # Text-to-image product ads
                arguments={
                    "prompt": prompt,
                    "image_size": {
                        "width": width,
                        "height": height
                    },
                    "num_images": 1,
                    "enable_safety_checker": True,
                    "output_format": "png"
                },
                with_logs=True,
                on_queue_update=on_queue_update
            )
            
            url = result['images'][0]['url']
            logger.info("Professional ad background generated with Nano Banana Pro")
            return url
            
        except Exception as e:
            logger.error(f"Fal.ai Nano Banana Pro failed: {e}")
            logger.info("Trying fallback to DALL-E...")
            return self._generate_background_dalle(product_name, product_description, style, width, height)
    
    def _generate_background_dalle(self, product_name, product_description, style, width, height):
        """Generate ad background with DALL-E 3 - Clean Professional Ads"""
        logger.info("Generating clean professional ad background with DALL-E 3...")
        
        aspect = "square" if width == height else "portrait" if height > width else "landscape"
        
        prompt = f"""A clean, minimal product advertisement background for {product_name}.

Style: {style}, professional, simple, elegant
Background: Solid color or subtle gradient, no clutter
Lighting: Studio quality, soft and professional
Composition: Minimal, spacious, {aspect} format
Aesthetic: Modern commercial advertising
Quality: High-end professional

Simple, clean, and ready for product placement. No text, no logos, no complex elements."""
        response = self.client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",  # DALL-E 3 only supports 1024x1024
            quality="hd",
            n=1
        )
        
        url = response.data[0].url
        logger.info("Clean professional background generated with DALL-E 3")
        return url
    
    def _download_image(self, url):
        """Download image from URL"""
        if url.startswith('http'):
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return Image.open(io.BytesIO(response.content))
        else:
            return Image.open(url)
    
    def _composite_product(self, background, product_img):
        """Composite product image onto background"""
        max_size = min(background.size[0], background.size[1]) * 0.6
        product_img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        x = (background.size[0] - product_img.size[0]) // 2
        y = (background.size[1] - product_img.size[1]) // 2
        
        if product_img.mode == 'RGBA':
            background.paste(product_img, (x, y), product_img)
        else:
            background.paste(product_img, (x, y))
        
        return background
    
    def _add_text_overlay(self, img, text):
        """Add text overlay to image"""
        draw = ImageDraw.Draw(img)
        
        try:
            font_size = img.size[1] // 15
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (img.size[0] - text_width) // 2
        y = img.size[1] // 10
        
        shadow_offset = 3
        for offset_x in range(-shadow_offset, shadow_offset + 1):
            for offset_y in range(-shadow_offset, shadow_offset + 1):
                if offset_x != 0 or offset_y != 0:
                    draw.text(
                        (x + offset_x, y + offset_y),
                        text,
                        font=font,
                        fill=(0, 0, 0, 180)
                    )
        
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
        
        return img
    
    def _scrape_product_info(self, url):
        """
        Scrape product information from URL
        """
        logger.info(f"Scraping product info from: {url}")
        logger.warning("Web scraping: İstifadəçi website Terms of Service-ə cavabdehdir")
        
        try:
            headers = {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                ),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'az-AZ,az;q=0.9,en-US;q=0.8,en;q=0.7,tr;q=0.6',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0',
                'Referer': urlparse(url).scheme + '://' + urlparse(url).netloc
            }
            
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract product name
            name = None
            name_selectors = [
                soup.find('h1'),
                soup.find('meta', property='og:title'),
                soup.find('meta', attrs={'name': 'title'}),
                soup.find(class_='product-title'),
                soup.find(class_='product-name'),
            ]
            for selector in name_selectors:
                if selector:
                    name = selector.get('content') if selector.name == 'meta' else selector.get_text()
                    if name:
                        name = name.strip()
                        break
            
            # Extract description
            description = None
            desc_selectors = [
                soup.find('meta', property='og:description'),
                soup.find('meta', attrs={'name': 'description'}),
                soup.find(class_='product-description'),
                soup.find(class_='description'),
            ]
            for selector in desc_selectors:
                if selector:
                    description = selector.get('content') if selector.name == 'meta' else selector.get_text()
                    if description:
                        description = description.strip()[:500]
                        break
            
            # Extract product image
            image_url = None
            image_selectors = [
                soup.find('meta', property='og:image'),
                soup.find('meta', property='twitter:image'),
                soup.find('img', class_='product-image'),
                soup.find('img', itemprop='image'),
                soup.find('img', class_='main-image'),
            ]
            for selector in image_selectors:
                if selector:
                    image_url = selector.get('content') or selector.get('src')
                    if image_url:
                        image_url = urljoin(url, image_url)
                        break
            
            # Extract logo (site logo)
            logo_url = None
            logo_selectors = [
                soup.find('link', rel='icon'),
                soup.find('link', rel='apple-touch-icon'),
                soup.find('img', class_='logo'),
                soup.find('img', alt=lambda x: x and 'logo' in x.lower()),
            ]
            for selector in logo_selectors:
                if selector:
                    logo_url = selector.get('href') or selector.get('src')
                    if logo_url:
                        logo_url = urljoin(url, logo_url)
                        if 'favicon' not in logo_url.lower():
                            break
            
            logger.info(f"Scraped: name={name}, image={bool(image_url)}, logo={bool(logo_url)}")
            
            return {
                'name': name,
                'description': description,
                'image_url': image_url,
                'logo_url': logo_url,
            }
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.error(f"403 Forbidden: Sayt bot-ları bloklayır - {url}")
                logger.info("Manuel məlumat daxil etmək tövsiyə olunur")
            else:
                logger.error(f"HTTP Error {e.response.status_code}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to scrape product info: {e}")
            return None
    
    def _add_logo(self, img, logo_img, position='bottom-right', size_percent=10):
        """Add logo to image"""
        logger.info("Adding logo to ad creative...")
        
        if logo_img.mode != 'RGBA':
            logo_img = logo_img.convert('RGBA')
        
        logo_width = int(img.size[0] * (size_percent / 100))
        aspect_ratio = logo_img.size[1] / logo_img.size[0]
        logo_height = int(logo_width * aspect_ratio)
        
        logo_img = logo_img.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
        
        padding = int(img.size[0] * 0.03)
        
        if position == 'bottom-right':
            x = img.size[0] - logo_width - padding
            y = img.size[1] - logo_height - padding
        elif position == 'bottom-left':
            x = padding
            y = img.size[1] - logo_height - padding
        elif position == 'top-right':
            x = img.size[0] - logo_width - padding
            y = padding
        elif position == 'top-left':
            x = padding
            y = padding
        else:
            x = img.size[0] - logo_width - padding
            y = img.size[1] - logo_height - padding
        
        background = Image.new('RGBA', (logo_width + 20, logo_height + 20), (255, 255, 255, 200))
        bg_x = x - 10
        bg_y = y - 10
        
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        img.paste(background, (bg_x, bg_y), background)
        img.paste(logo_img, (x, y), logo_img)
        
        if img.mode == 'RGBA':
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[3])
            img = rgb_img
        
        logger.info("Logo added successfully")
        return img
