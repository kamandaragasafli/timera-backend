from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view, permission_classes, parser_classes
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
from django.db import transaction
import openai
import logging
import re
import base64
import io
import uuid
import requests
import json
from datetime import datetime, timedelta
from PIL import Image
import sys
from urllib.parse import urlparse, urljoin
import time

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


def convert_image_to_supported_format(image_data, content_type=None, filename=None):
    """
    Convert image to a format supported by OpenAI API (PNG, JPEG, GIF, WEBP).
    AVIF and other unsupported formats are converted to PNG.
    
    Args:
        image_data: Binary image data
        content_type: MIME type of the image (optional)
        filename: Original filename (optional)
    
    Returns:
        tuple: (converted_image_data, mime_type)
    """
    try:
        # Try to detect format from content type or filename
        format_hint = None
        if content_type:
            if 'avif' in content_type.lower():
                format_hint = 'AVIF'
            elif 'png' in content_type.lower():
                format_hint = 'PNG'
            elif 'jpeg' in content_type.lower() or 'jpg' in content_type.lower():
                format_hint = 'JPEG'
            elif 'gif' in content_type.lower():
                format_hint = 'GIF'
            elif 'webp' in content_type.lower():
                format_hint = 'WEBP'
        
        if not format_hint and filename:
            ext = filename.split('.')[-1].lower()
            if ext == 'avif':
                format_hint = 'AVIF'
            elif ext in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
                format_hint = ext.upper()
        
        # Open image with PIL
        image = Image.open(io.BytesIO(image_data))
        
        # Check if format is supported by OpenAI
        supported_formats = ['PNG', 'JPEG', 'GIF', 'WEBP']
        current_format = format_hint or image.format
        
        if current_format and current_format.upper() not in supported_formats:
            # Convert unsupported format to PNG
            logger.info(f"Converting unsupported format {current_format} to PNG")
            
            # Convert to RGB if necessary (for JPEG compatibility)
            if image.mode in ('RGBA', 'LA', 'P'):
                # Create white background for transparency
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
                image = background
            elif image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')
            
            # Save as PNG
            output = io.BytesIO()
            image.save(output, format='PNG', optimize=True)
            converted_data = output.getvalue()
            output.close()
            
            return converted_data, 'image/png'
        
        # Format is supported, return as-is or convert to ensure compatibility
        output = io.BytesIO()
        if image.format == 'PNG':
            image.save(output, format='PNG', optimize=True)
            mime_type = 'image/png'
        elif image.format in ('JPEG', 'JPG'):
            # Ensure RGB mode for JPEG
            if image.mode != 'RGB':
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'RGBA':
                    rgb_image.paste(image, mask=image.split()[3])
                else:
                    rgb_image.paste(image)
                image = rgb_image
            image.save(output, format='JPEG', quality=95, optimize=True)
            mime_type = 'image/jpeg'
        elif image.format == 'GIF':
            # For GIF, save as PNG (OpenAI supports GIF but PNG is more reliable)
            if image.mode != 'RGB':
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                if image.mode in ('RGBA', 'LA'):
                    rgb_image.paste(image, mask=image.split()[-1])
                else:
                    rgb_image.paste(image)
                image = rgb_image
            image.save(output, format='PNG', optimize=True)
            mime_type = 'image/png'
        elif image.format == 'WEBP':
            # Convert WEBP to PNG for better compatibility
            if image.mode != 'RGB':
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode in ('RGBA', 'LA'):
                    rgb_image.paste(image, mask=image.split()[-1])
                else:
                    rgb_image.paste(image)
                image = rgb_image
            image.save(output, format='PNG', optimize=True)
            mime_type = 'image/png'
        else:
            # Default to PNG
            if image.mode != 'RGB':
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode in ('RGBA', 'LA', 'P'):
                    if image.mode == 'P':
                        image = image.convert('RGBA')
                    rgb_image.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
                else:
                    rgb_image.paste(image)
                image = rgb_image
            image.save(output, format='PNG', optimize=True)
            mime_type = 'image/png'
        
        converted_data = output.getvalue()
        output.close()
        return converted_data, mime_type
        
    except Exception as e:
        logger.error(f"Error converting image format: {e}", exc_info=True)
        # Return original data and let API handle it
        return image_data, content_type or 'image/jpeg'

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
            
            # Read and convert image if needed
            image_data = logo_file.read()
            content_type = logo_file.content_type
            filename = logo_file.name
            
            # Convert to supported format (AVIF -> PNG/JPEG)
            image_data, mime_type = convert_image_to_supported_format(
                image_data, 
                content_type=content_type, 
                filename=filename
            )
            
            # Determine format for data URL
            if 'png' in mime_type.lower():
                data_url_format = 'image/png'
            elif 'jpeg' in mime_type.lower() or 'jpg' in mime_type.lower():
                data_url_format = 'image/jpeg'
            else:
                data_url_format = 'image/png'  # Default to PNG
            
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
                                    "url": f"data:{data_url_format};base64,{base64_image}",
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


class GenerateComplementaryColorsView(APIView):
    """Generate complementary colors based on primary colors and brand analysis"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            primary_color = request.data.get('primary_color')
            color_palette = request.data.get('color_palette', [])
            brand_personality = request.data.get('brand_personality', [])
            design_style = request.data.get('design_style', '')
            
            if not primary_color:
                return Response({
                    'error': 'Primary color is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info(f"Generating complementary colors for user: {request.user.email}")
            logger.info(f"Primary color: {primary_color}")
            
            # Initialize OpenAI client
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Build context
            context_info = f"Primary Color: {primary_color}\n"
            if color_palette:
                context_info += f"Color Palette: {', '.join(color_palette)}\n"
            if brand_personality:
                context_info += f"Brand Personality: {', '.join(brand_personality)}\n"
            if design_style:
                context_info += f"Design Style: {design_style}\n"
            
            # Create prompt for complementary colors
            prompt = f"""You are a color theory expert. Generate 3 complementary colors that work harmoniously with the given brand colors.

{context_info}

Requirements:
- Generate exactly 3 complementary colors in HEX format
- Colors should complement the primary color and existing palette
- Consider the brand personality and design style
- Return ONLY a valid JSON array of hex codes, no explanations

Return format (JSON array only):
["#HEX1", "#HEX2", "#HEX3"]"""
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if '```' in response_text:
                parts = response_text.split('```')
                if len(parts) >= 3:
                    response_text = parts[1]
                    if response_text.lower().startswith('json'):
                        response_text = response_text[4:]
                elif len(parts) == 2:
                    response_text = parts[1]
            
            response_text = response_text.strip()
            
            # Parse JSON
            try:
                complementary_colors = json.loads(response_text)
                if not isinstance(complementary_colors, list) or len(complementary_colors) != 3:
                    raise ValueError("Response must be an array of 3 hex codes")
                
                # Validate hex codes
                hex_pattern = re.compile(r'^#[0-9A-Fa-f]{6}$')
                for color in complementary_colors:
                    if not hex_pattern.match(color):
                        raise ValueError(f"Invalid hex code: {color}")
                
                logger.info(f"Successfully generated complementary colors: {complementary_colors}")
                
                return Response({
                    'complementary_colors': complementary_colors,
                    'status': 'success'
                }, status=status.HTTP_200_OK)
                
            except json.JSONDecodeError as e:
                # Try to extract JSON manually
                json_match = re.search(r'\[.*?\]', response_text, re.DOTALL)
                if json_match:
                    complementary_colors = json.loads(json_match.group(0))
                    return Response({
                        'complementary_colors': complementary_colors,
                        'status': 'success'
                    }, status=status.HTTP_200_OK)
                else:
                    raise ValueError(f"Failed to parse JSON: {str(e)}")
            
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return Response({
                'error': f'OpenAI API error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Error generating complementary colors: {str(e)}", exc_info=True)
            return Response({
                'error': f'Failed to generate complementary colors: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GenerateSmartPromptView(APIView):
    """Generate smart content prompt based on product image and company info"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            product_image = request.FILES.get('product_image')
            company_name = request.data.get('company_name', '')
            industry = request.data.get('industry', '')
            target_audience = request.data.get('target_audience', '')
            brand_personality = request.data.get('brand_personality', '')
            user_notes = request.data.get('user_notes', '')
            
            logger.info(f"Generating smart prompt for user: {request.user.email}")
            
            # Initialize OpenAI client
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Prepare messages
            messages = [
                {
                    "role": "system",
                    "content": "Sən peşəkar sosial media content strategistisən. Şəkil və şirkət məlumatlarına əsasən professional content generation prompt-ları yazırsan."
                }
            ]
            
            # If image provided, analyze it first
            image_analysis = None
            if product_image:
                logger.info(f"📸 Analyzing product image...")
                
                # Convert image to base64
                image_data = product_image.read()
                base64_image = base64.b64encode(image_data).decode('utf-8')
                
                # Analyze image with Vision API
                vision_messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Şəkildəki məhsulu detallı analiz et. Məhsul növü, rəng, dizayn, xüsusiyyətlər, hədəf auditoriya, və sosial media üçün necə təqdim etmək olar haqqında məlumat ver. Azərbaycan dilində cavab ver."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ]
                
                vision_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=vision_messages,
                    max_tokens=500
                )
                
                image_analysis = vision_response.choices[0].message.content.strip()
                logger.info(f"✅ Image analyzed: {len(image_analysis)} chars")
            
            # Build context
            context = ""
            if company_name:
                context += f"Şirkət: {company_name}\n"
            if industry:
                context += f"Sənaye: {industry}\n"
            if target_audience:
                context += f"Hədəf Auditoriya: {target_audience}\n"
            if brand_personality:
                context += f"Brend Şəxsiyyəti: {brand_personality}\n"
            if image_analysis:
                context += f"\nMəhsul Şəkli Analizi:\n{image_analysis}\n"
            if user_notes:
                context += f"\nİstifadəçi Qeydləri:\n{user_notes}\n"
            
            # Generate smart prompt
            prompt_request = f"""Aşağıdakı məlumatlara əsasən, AI content generator üçün professional və effektiv bir prompt yaz.

{context}

Tələblər:
- Prompt Azərbaycan dilində olmalıdır
- Məhsula və şirkətə uyğun olmalıdır
- Kreativ və engaging content yaratmaq üçün
- 3-5 cümlə, konkret və aydın
- Hədəf auditoriyaya uyğun ton
- Əgər məhsul şəkli varsa, onun xüsusiyyətlərini vurğula

Yalnız prompt-u qaytar, başqa heç nə yazma."""
            
            messages.append({
                "role": "user",
                "content": prompt_request
            })
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=300,
                temperature=0.8
            )
            
            smart_prompt = response.choices[0].message.content.strip()
            smart_prompt = smart_prompt.strip('"\'')
            
            logger.info(f"✅ Generated smart prompt: {len(smart_prompt)} chars")
            
            return Response({
                'smart_prompt': smart_prompt,
                'image_analysis': image_analysis,
                'status': 'success'
            }, status=status.HTTP_200_OK)
            
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return Response({
                'error': f'OpenAI API error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Error generating smart prompt: {str(e)}", exc_info=True)
            return Response({
                'error': f'Failed to generate smart prompt: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CompetitorAnalysisView(APIView):
    """Analyze competitor's social media profile and compare with user's profile"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            competitor_url = request.data.get('competitor_url', '')
            competitor_name = request.data.get('competitor_name', '')
            your_profile_data = request.data.get('your_profile', {})
            analysis_depth = request.data.get('analysis_depth', 'standard')  # quick, standard, deep
            
            if not competitor_url and not competitor_name:
                return Response({
                    'error': 'Competitor URL or name is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info(f"🔍 Competitor Analysis for user: {request.user.email}")
            logger.info(f"   Competitor URL: {competitor_url}")
            logger.info(f"   Analysis Depth: {analysis_depth}")
            
            # Detect platform
            platform = None
            if competitor_url:
                if 'instagram.com' in competitor_url:
                    platform = 'Instagram'
                elif 'facebook.com' in competitor_url or 'fb.com' in competitor_url:
                    platform = 'Facebook'
                elif 'linkedin.com' in competitor_url:
                    platform = 'LinkedIn'
            
            # Try to scrape competitor profile
            competitor_data = None
            scraping_attempted = False
            
            if competitor_url and platform:
                logger.info(f"📡 Attempting to scrape {platform} profile...")
                scraping_attempted = True
                
                try:
                    if platform == 'Instagram':
                        competitor_data = scrape_instagram_with_apify(competitor_url)
                    elif platform == 'Facebook':
                        competitor_data = scrape_facebook_with_apify(competitor_url)
                    elif platform == 'LinkedIn':
                        if '/company/' in competitor_url:
                            competitor_data = scrape_linkedin_company_with_apify(competitor_url)
                        else:
                            competitor_data = scrape_linkedin_with_apify(competitor_url)
                    
                    if competitor_data:
                        logger.info(f"✅ Successfully scraped competitor profile")
                except Exception as scraping_error:
                    logger.warning(f"⚠️ Scraping failed: {str(scraping_error)}")
            
            # Get company profile for comparison
            try:
                from accounts.models import CompanyProfile
                user_company = CompanyProfile.objects.filter(user=request.user).first()
            except Exception as e:
                logger.warning(f"Could not fetch user company profile: {str(e)}")
                user_company = None
            
            # Build analysis context
            context_info = ""
            
            # Competitor info
            if competitor_data:
                context_info += "Rəqib Profil (Real Data):\n"
                context_info += f"- Platform: {platform}\n"
                context_info += f"- Username: {competitor_data.get('username', competitor_data.get('name', 'N/A'))}\n"
                context_info += f"- Followers: {competitor_data.get('followersCount', competitor_data.get('followers', 'N/A'))}\n"
                context_info += f"- Following: {competitor_data.get('followsCount', competitor_data.get('following', 'N/A'))}\n"
                context_info += f"- Posts: {competitor_data.get('postsCount', competitor_data.get('posts_count', 'N/A'))}\n"
                context_info += f"- Bio: {competitor_data.get('biography', competitor_data.get('bio', competitor_data.get('about', 'N/A')))}\n"
                
                # Recent posts info if available
                if 'latest_posts' in competitor_data or 'recentPosts' in competitor_data:
                    posts = competitor_data.get('latest_posts', competitor_data.get('recentPosts', []))
                    if posts and len(posts) > 0:
                        context_info += f"- Son paylaşımlar sayı: {len(posts)}\n"
                        # Calculate average engagement if available
                        total_likes = sum(post.get('likesCount', post.get('likes', 0)) for post in posts[:10])
                        total_comments = sum(post.get('commentsCount', post.get('comments', 0)) for post in posts[:10])
                        if total_likes > 0 or total_comments > 0:
                            context_info += f"- Orta likes (son 10 post): {total_likes / min(len(posts), 10):.0f}\n"
                            context_info += f"- Orta comments (son 10 post): {total_comments / min(len(posts), 10):.0f}\n"
            else:
                context_info += f"Rəqib: {competitor_name or competitor_url}\n"
                context_info += "- Real data əlçatan deyil, AI təxmini analiz ediləcək\n"
            
            # Your profile info
            if your_profile_data:
                context_info += "\nSizin Profil:\n"
                for key, value in your_profile_data.items():
                    context_info += f"- {key}: {value}\n"
            elif user_company:
                context_info += "\nSizin Şirkət:\n"
                context_info += f"- Ad: {user_company.company_name}\n"
                context_info += f"- Sənaye: {user_company.industry}\n"
                context_info += f"- Hədəf Auditoriya: {user_company.target_audience}\n"
            
            # Initialize OpenAI client
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Create comprehensive prompt
            prompt = f"""Sən peşəkar sosial media və rəqabət analitikisən. Aşağıdakı məlumatlara əsasən detallı rəqib analizi hazırla.

{context_info}

Aşağıdakı formatta JSON cavab qaytar (yalnız JSON, başqa mətn yox):

{{
  "competitor_overview": {{
    "name": "Rəqib adı",
    "platform": "Platform adı",
    "follower_count": 0,
    "engagement_rate": "X%",
    "posting_frequency": "Həftədə X dəfə",
    "overall_score": 85,
    "strengths": ["Güclü tərəf 1", "Güclü tərəf 2"],
    "weaknesses": ["Zəif tərəf 1", "Zəif tərəf 2"]
  }},
  "content_strategy": {{
    "content_types": [
      {{
        "type": "Video/Image/Carousel/Reel",
        "percentage": 40,
        "performance": "Yüksək/Orta/Aşağı"
      }}
    ],
    "themes": ["Tema 1", "Tema 2", "Tema 3"],
    "tone": "Professional/Casual/Creative",
    "language_style": "Formal/Informal/Mixed"
  }},
  "engagement_analysis": {{
    "average_likes": 0,
    "average_comments": 0,
    "average_shares": 0,
    "engagement_rate": "X%",
    "best_performing_content": "Content növü",
    "peak_engagement_times": ["Saat aralığı"]
  }},
  "hashtag_strategy": {{
    "most_used_hashtags": ["#hashtag1", "#hashtag2"],
    "hashtag_count_per_post": "X-Y arası",
    "hashtag_effectiveness": "Yüksək/Orta/Aşağı",
    "recommendations": ["Tövsiyə 1", "Tövsiyə 2"]
  }},
  "audience_insights": {{
    "target_demographic": "Hədəf auditoriya",
    "engagement_patterns": "Engagement patterns",
    "follower_quality": "Yüksək/Orta/Aşağı",
    "growth_trend": "Artır/Sabit/Azalır"
  }},
  "competitive_advantages": [
    {{
      "advantage": "Rəqibin üstünlüyü",
      "impact": "Yüksək/Orta/Aşağı",
      "how_they_do_it": "Necə edirlər",
      "how_you_can_compete": "Siz necə rəqabət apara bilərsiniz"
    }}
  ],
  "opportunities_for_you": [
    {{
      "opportunity": "İmkan",
      "difficulty": "Asan/Orta/Çətin",
      "potential_impact": "Yüksək/Orta/Aşağı",
      "action_steps": ["Addım 1", "Addım 2"]
    }}
  ],
  "content_gaps": [
    {{
      "gap": "Rəqibin etmədiyi şey",
      "why_important": "Niyə vacib",
      "how_to_leverage": "Necə istifadə etmək"
    }}
  ],
  "recommendations": [
    {{
      "category": "Content/Engagement/Timing/Hashtags",
      "recommendation": "Tövsiyə",
      "priority": "Yüksək/Orta/Aşağı",
      "expected_result": "Gözlənilən nəticə"
    }}
  ],
  "summary": {{
    "overall_assessment": "Ümumi qiymətləndirmə",
    "key_takeaways": ["Əsas çıxarış 1", "Əsas çıxarış 2"],
    "immediate_actions": ["Dərhal etməli 1", "Dərhal etməli 2"],
    "long_term_strategy": "Uzunmüddətli strategiya"
  }}
}}

Tələblər:
- Real dataya əsasən (əgər varsa) dəqiq analiz
- Praktik və tətbiq oluna bilən tövsiyələr
- Azərbaycan dilində
- Müqayisəli təhlil (sizin profil vs rəqib)
- Actionable insights
- Yalnız JSON qaytar, başqa mətn yazma"""
            
            # Determine max_tokens based on analysis depth
            max_tokens_map = {
                'quick': 2000,
                'standard': 3000,
                'deep': 4500
            }
            max_tokens = max_tokens_map.get(analysis_depth, 3000)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Sən peşəkar sosial media və rəqabət analitikisən. Həmişə JSON formatında detallı analiz verirsən."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=max_tokens,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            # Parse JSON response
            analysis_data = json.loads(response.choices[0].message.content.strip())
            
            logger.info(f"✅ Successfully analyzed competitor")
            
            return Response({
                'analysis': analysis_data,
                'competitor_data': competitor_data if competitor_data else None,
                'scraping_attempted': scraping_attempted,
                'scraping_successful': competitor_data is not None,
                'platform': platform,
                'status': 'success'
            }, status=status.HTTP_200_OK)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            return Response({
                'error': 'Failed to parse analysis response'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return Response({
                'error': f'OpenAI API error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Error analyzing competitor: {str(e)}", exc_info=True)
            return Response({
                'error': f'Failed to analyze competitor: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AnalyzeTrendsView(APIView):
    """Analyze current trends for specific industry and target audience"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            company_name = request.data.get('company_name', '')
            industry = request.data.get('industry', '')
            target_audience = request.data.get('target_audience', '')
            keywords = request.data.get('keywords', [])
            region = request.data.get('region', 'Azerbaijan')
            
            logger.info(f"Analyzing trends for user: {request.user.email}")
            logger.info(f"Industry: {industry}, Region: {region}")
            
            if not industry:
                return Response({
                    'error': 'Industry is required for trend analysis'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Initialize OpenAI client
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Get current date info
            from datetime import datetime
            current_date = datetime.now()
            current_month = current_date.strftime('%B')
            current_year = current_date.year
            
            # Build context
            context_info = f"Şirkət: {company_name or 'N/A'}\n"
            context_info += f"Sənaye: {industry}\n"
            if target_audience:
                context_info += f"Hədəf Auditoriya: {target_audience}\n"
            if keywords:
                context_info += f"Açar Sözlər: {', '.join(keywords)}\n"
            context_info += f"Region: {region}\n"
            context_info += f"Hazırkı tarix: {current_month} {current_year}\n"
            
            # Create comprehensive prompt
            prompt = f"""Sən peşəkar sosial media və marketinq trend analitikisən. Aşağıdakı məlumatlara əsasən detallı trend analizi hazırla.

{context_info}

Aşağıdakı formatta JSON cavab qaytar (yalnız JSON, başqa mətn yox):

{{
  "current_trends": [
    {{
      "title": "Trend adı",
      "description": "Trendin təsviri",
      "relevance_score": 95,
      "why_relevant": "Niyə bu trend relevant",
      "action_items": ["Nə etmək lazım 1", "Nə etmək lazım 2"]
    }}
  ],
  "seasonal_opportunities": [
    {{
      "event": "Bayram və ya event",
      "date": "Təxmini tarix",
      "content_ideas": ["İdeya 1", "İdeya 2"],
      "hashtags": ["#hashtag1", "#hashtag2"]
    }}
  ],
  "trending_topics": [
    {{
      "topic": "Mövzu",
      "popularity": 90,
      "audience_fit": "Hədəf auditoriyaya uyğunluq",
      "content_angle": "Bu mövzunu necə istifadə etmək"
    }}
  ],
  "content_recommendations": [
    {{
      "type": "Content növü (video, carousel, reel, etc)",
      "theme": "Tema",
      "description": "Təsvir",
      "estimated_engagement": "Yüksək/Orta/Aşağı",
      "best_platforms": ["Instagram", "Facebook"]
    }}
  ],
  "hashtag_trends": [
    {{
      "hashtag": "#hashtag",
      "trend_status": "Yüksəlir/Populyar/Sabit",
      "estimated_reach": "Təxmini reach",
      "usage_tip": "İstifadə tövsiyəsi"
    }}
  ],
  "competitor_insights": [
    {{
      "strategy": "Strategiya",
      "why_it_works": "Niyə işə yarayır",
      "how_to_apply": "Necə tətbiq etmək"
    }}
  ],
  "upcoming_events": [
    {{
      "event": "Event/Bayram",
      "date": "Tarix",
      "preparation_timeline": "Hazırlıq müddəti",
      "content_ideas": ["İdeya 1", "İdeya 2"]
    }}
  ],
  "summary": {{
    "overall_trend_direction": "Ümumi trend istiqaməti",
    "key_opportunities": ["Əsas imkan 1", "Əsas imkan 2"],
    "quick_wins": ["Tez qazanc 1", "Tez qazanc 2"],
    "long_term_strategy": "Uzunmüddətli strategiya"
  }}
}}

Tələblər:
- Azərbaycan dilinə real və aktual trendlər
- {industry} sənayesi üçün spesifik
- {region} regionuna uyğun
- Hazırkı ay və mövsümə uyğun
- Praktik və tətbiq oluna bilən tövsiyələr
- 5-8 trend, 3-5 seasonal opportunity, 5-7 trending topic
- Yalnız JSON qaytar, başqa mətn yazma"""
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Sən peşəkar sosial media və marketinq trend analitikisən. Həmişə JSON formatında cavab verirsən."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=4000,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            # Parse JSON response
            trends_data = json.loads(response.choices[0].message.content.strip())
            
            logger.info(f"✅ Successfully analyzed trends for {industry}")
            logger.info(f"   Current Trends: {len(trends_data.get('current_trends', []))}")
            logger.info(f"   Seasonal Opportunities: {len(trends_data.get('seasonal_opportunities', []))}")
            logger.info(f"   Trending Topics: {len(trends_data.get('trending_topics', []))}")
            
            return Response({
                'trends': trends_data,
                'analysis_date': current_date.isoformat(),
                'status': 'success'
            }, status=status.HTTP_200_OK)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            return Response({
                'error': 'Failed to parse trend analysis response'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return Response({
                'error': f'OpenAI API error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Error analyzing trends: {str(e)}", exc_info=True)
            return Response({
                'error': f'Failed to analyze trends: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OptimizeCaptionView(APIView):
    """Optimize captions/titles for better engagement"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            caption = request.data.get('caption', '')
            content_type = request.data.get('content_type', 'post')  # post, title, description
            platform = request.data.get('platform', 'general')  # instagram, facebook, linkedin, general
            company_name = request.data.get('company_name', '')
            industry = request.data.get('industry', '')
            target_audience = request.data.get('target_audience', '')
            tone = request.data.get('tone', 'professional')  # professional, casual, creative, friendly
            
            if not caption:
                return Response({
                    'error': 'Caption is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info(f"Optimizing caption for user: {request.user.email}")
            logger.info(f"Content type: {content_type}, Platform: {platform}, Tone: {tone}")
            
            # Initialize OpenAI client
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Build context
            context_info = ""
            if company_name:
                context_info += f"Şirkət: {company_name}\n"
            if industry:
                context_info += f"Sənaye: {industry}\n"
            if target_audience:
                context_info += f"Hədəf Auditoriya: {target_audience}\n"
            
            # Platform-specific guidelines
            platform_guidelines = {
                'instagram': 'Instagram üçün: Qısa, cəlbedici, emoji istifadə et, call-to-action əlavə et',
                'facebook': 'Facebook üçün: Daha uzun, məlumatlı, sual ver, müzakirə yarad',
                'linkedin': 'LinkedIn üçün: Professional, dəyər əlavə edən, biznes fokuslu',
                'general': 'Ümumi: Cəlbedici, aydın, hədəf auditoriyaya uyğun'
            }
            
            # Tone guidelines
            tone_guidelines = {
                'professional': 'Professional və formal ton',
                'casual': 'Dostcasına və səmimi ton',
                'creative': 'Yaradıcı və orijinal ton',
                'friendly': 'Dostlu və açıq ton'
            }
            
            # Create prompt
            prompt = f"""Sən peşəkar sosial media marketinq ekspertisən. Aşağıdakı başlıq/caption-ı optimallaşdır.

{context_info}

Orijinal {content_type}: {caption}

Platform: {platform_guidelines.get(platform, platform_guidelines['general'])}
Ton: {tone_guidelines.get(tone, 'professional')}

Tələblər:
- Daha cəlbedici və engagement yaradan
- Aydın və anlaşılan
- Hədəf auditoriyaya uyğun
- Platform xüsusiyyətlərinə uyğun
- Ton-a uyğun
- Orijinal məzmunu saxla, amma daha effektiv et
- Yalnız optimallaşdırılmış başlıq/caption qaytar, başqa heç nə yazma"""
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Sən peşəkar sosial media marketinq ekspertisən. Başlıq və caption-ları optimallaşdırırsan."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=500,
                temperature=0.8
            )
            
            optimized_caption = response.choices[0].message.content.strip()
            optimized_caption = optimized_caption.strip('"\'')
            
            logger.info(f"Successfully optimized caption: {len(optimized_caption)} chars")
            
            return Response({
                'original_caption': caption,
                'optimized_caption': optimized_caption,
                'improvements': {
                    'length_change': len(optimized_caption) - len(caption),
                    'platform': platform,
                    'tone': tone
                },
                'status': 'success'
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return Response({
                'error': f'OpenAI API error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Error optimizing caption: {str(e)}", exc_info=True)
            return Response({
                'error': f'Failed to optimize caption: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GenerateHashtagsView(APIView):
    """Generate hashtags based on company information and content"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            # Get company information
            company_name = request.data.get('company_name', '')
            industry = request.data.get('industry', '')
            business_description = request.data.get('business_description', '')
            content = request.data.get('content', '')
            target_audience = request.data.get('target_audience', '')
            brand_keywords = request.data.get('brand_keywords', [])
            num_hashtags = request.data.get('num_hashtags', 15)
            
            if not company_name and not content:
                return Response({
                    'error': 'Company name or content is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info(f"Generating hashtags for user: {request.user.email}")
            logger.info(f"Company: {company_name}, Industry: {industry}")
            
            # Initialize OpenAI client
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Build context
            context_info = ""
            if company_name:
                context_info += f"Şirkət Adı: {company_name}\n"
            if industry:
                context_info += f"Sənaye: {industry}\n"
            if business_description:
                context_info += f"Biznes Təsviri: {business_description}\n"
            if target_audience:
                context_info += f"Hədəf Auditoriya: {target_audience}\n"
            if brand_keywords:
                keywords_str = ', '.join(brand_keywords) if isinstance(brand_keywords, list) else brand_keywords
                context_info += f"Brend Açar Sözləri: {keywords_str}\n"
            if content:
                context_info += f"Paylaşım Məzmunu: {content[:500]}\n"
            
            # Create prompt for hashtag generation
            prompt = f"""Sən peşəkar sosial media marketinq ekspertisən. Aşağıdakı məlumatlara əsasən {num_hashtags} ədəd uyğun hashtag yarat.

{context_info}

Tələblər:
- {num_hashtags} ədəd hashtag (az və ya çox deyil)
- Populyar və trend hashtaglar
- Niş (niche) hashtaglar
- Yerli hashtaglar (#baku, #azerbaijan və s.)
- Sənaye xüsusi hashtaglar
- Brend hashtaglar (şirkət adı əsasında)
- Mix: populyar (yüksək trafik) və niş (az rəqabət) hashtaglar
- Yalnız hashtagları qaytar, başqa heç nə yazma
- Hashtaglar # işarəsi ilə başlamalıdır
- JSON array formatında qaytar: ["#hashtag1", "#hashtag2", ...]"""
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=500,
                temperature=0.8
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if '```' in response_text:
                parts = response_text.split('```')
                if len(parts) >= 3:
                    response_text = parts[1]
                    if response_text.lower().startswith('json'):
                        response_text = response_text[4:]
                elif len(parts) == 2:
                    response_text = parts[1]
            
            response_text = response_text.strip()
            
            # Parse JSON
            try:
                hashtags = json.loads(response_text)
                if not isinstance(hashtags, list):
                    raise ValueError("Response must be an array")
                
                # Validate and clean hashtags
                cleaned_hashtags = []
                for tag in hashtags:
                    tag_str = str(tag).strip()
                    if not tag_str.startswith('#'):
                        tag_str = '#' + tag_str.lstrip('#')
                    # Remove duplicates
                    if tag_str not in cleaned_hashtags:
                        cleaned_hashtags.append(tag_str)
                
                # Limit to requested number
                hashtags = cleaned_hashtags[:num_hashtags]
                
                logger.info(f"Successfully generated {len(hashtags)} hashtags")
                
                return Response({
                    'hashtags': hashtags,
                    'count': len(hashtags),
                    'status': 'success'
                }, status=status.HTTP_200_OK)
                
            except json.JSONDecodeError as e:
                # Try to extract hashtags manually
                import re
                hashtag_pattern = r'#\w+'
                found_hashtags = re.findall(hashtag_pattern, response_text)
                if found_hashtags:
                    hashtags = list(set(found_hashtags))[:num_hashtags]
                    return Response({
                        'hashtags': hashtags,
                        'count': len(hashtags),
                        'status': 'success'
                    }, status=status.HTTP_200_OK)
                else:
                    raise ValueError(f"Failed to parse hashtags: {str(e)}")
            
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return Response({
                'error': f'OpenAI API error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Error generating hashtags: {str(e)}", exc_info=True)
            return Response({
                'error': f'Failed to generate hashtags: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GenerateSloganView(APIView):
    """Generate slogan based on company information"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            # Get company information
            company_name = request.data.get('company_name', '')
            industry = request.data.get('industry', '')
            business_description = request.data.get('business_description', '')
            target_audience = request.data.get('target_audience', '')
            unique_selling_points = request.data.get('unique_selling_points', '')
            brand_personality = request.data.get('brand_personality', [])
            brand_keywords = request.data.get('brand_keywords', [])
            
            if not company_name:
                return Response({
                    'error': 'Company name is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info(f"Generating slogan for user: {request.user.email}")
            logger.info(f"Company: {company_name}")
            
            # Initialize OpenAI client
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Build context
            context_info = f"Şirkət Adı: {company_name}\n"
            if industry:
                context_info += f"Sənaye: {industry}\n"
            if business_description:
                context_info += f"Biznes Təsviri: {business_description}\n"
            if target_audience:
                context_info += f"Hədəf Auditoriya: {target_audience}\n"
            if unique_selling_points:
                context_info += f"Unikal Satış Təklifləri: {unique_selling_points}\n"
            if brand_personality:
                context_info += f"Brend Şəxsiyyəti: {', '.join(brand_personality) if isinstance(brand_personality, list) else brand_personality}\n"
            if brand_keywords:
                context_info += f"Brend Açar Sözləri: {', '.join(brand_keywords) if isinstance(brand_keywords, list) else brand_keywords}\n"
            
            # Create prompt for slogan generation
            prompt = f"""Sən peşəkar brending ekspertisən. Aşağıdakı şirkət məlumatlarına əsasən güclü, yadda qalan slogan yarat.

{context_info}

Tələblər:
- Qısa və yadda qalan (3-7 söz, maksimum 200 simvol)
- Professional və ilhamverici
- Azərbaycan dilində
- Brendin mahiyyətini və dəyərlərini əks etdirən
- Şirkətin unikal xüsusiyyətlərini vurğulayan
- Hədəf auditoriyaya cəlbedici

YALNIZ sloganı qaytar, başqa heç nə yazma. Slogan dırnaqsız olmalıdır."""
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=100,
                temperature=0.9
            )
            
            slogan_raw = response.choices[0].message.content.strip()
            # Remove quotes if present
            slogan = slogan_raw.strip('"').strip("'").strip()
            
            # Validate slogan
            if not slogan or len(slogan) < 3:
                logger.warning(f"Slogan çox qısadır: '{slogan}'. Default slogan istifadə olunur.")
                slogan = f"{company_name} - Sizin Uğurunuz, Bizim Məqsədimiz"
            
            # Limit length
            if len(slogan) > 200:
                slogan = slogan[:197] + "..."
            
            logger.info(f"Successfully generated slogan: '{slogan}'")
            
            return Response({
                'slogan': slogan,
                'status': 'success'
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return Response({
                'error': f'OpenAI API error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Error generating slogan: {str(e)}", exc_info=True)
            return Response({
                'error': f'Failed to generate slogan: {str(e)}'
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


def upload_product_image(image_file, user_id, folder_name="product_images"):
    """Məhsul şəklini yükləyir"""
    # Reset file pointer to beginning
    image_file.seek(0)
    ext = image_file.name.split('.')[-1].lower()
    filename = f"{folder_name}/user_{user_id}_{uuid.uuid4()}.{ext}"
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
        
    except openai.APITimeoutError as e:
        logger.error(f"❌ OpenAI API timeout error: {str(e)}")
        raise ValueError(f"OpenAI API cavab vermədi. Zəhmət olmasa yenidən cəhd edin: {str(e)}")
    except openai.APIError as e:
        logger.error(f"❌ OpenAI API error: {str(e)}")
        raise ValueError(f"OpenAI API xətası: {str(e)}. Zəhmət olmasa API key-in düzgün olduğunu yoxlayın.")
    except Exception as e:
        logger.error(f"❌ Logo və slogan yaratma xətası: {str(e)}", exc_info=True)
        raise Exception(f"Logo və slogan yaradıla bilmədi: {str(e)}")


def download_and_save_logo(logo_url, user_id):
    """Logo yükləyib transparent background ilə saxlayır"""
    try:
        logger.info(f"📥 Logo yüklənir: {logo_url}")
        response = requests.get(logo_url, timeout=60)  # Increased timeout for server
        response.raise_for_status()
        
        # Load image with PIL
        from PIL import Image
        import io
        
        logo_image = Image.open(io.BytesIO(response.content))
        logger.info(f"   Original image size: {logo_image.size}, mode: {logo_image.mode}")
        
        # Convert to RGBA if not already
        if logo_image.mode != 'RGBA':
            logo_image = logo_image.convert('RGBA')
        
        # Remove white/light background and make transparent
        logger.info("🔄 Arxa fon transparent edilir...")
        
        # Get image dimensions
        width, height = logo_image.size
        
        # Optimize: Use NumPy for faster processing if available
        # Note: NumPy is optional - code will work without it using fallback method
        try:
            import numpy as np  # noqa: F401, pylint: disable=import-error
            # Convert to NumPy array for faster processing
            img_array = np.array(logo_image)
            
            # Create mask for white/light pixels (threshold: RGB > 240)
            # For RGBA images, check RGB channels only
            white_mask = (img_array[:, :, 0] > 240) & (img_array[:, :, 1] > 240) & (img_array[:, :, 2] > 240)
            
            # Set alpha channel to 0 for white/light pixels
            img_array[:, :, 3] = np.where(white_mask, 0, 255)
            
            # Convert back to PIL Image
            logo_image = Image.fromarray(img_array, 'RGBA')
            logger.info("   Background removal completed using NumPy (fast method)")
        except ImportError:
            # NumPy not available - use simpler method for small images
            logger.info("   NumPy not available, using simplified background removal")
            # Most DALL-E generated logos already have transparent backgrounds
            # Just keep the image as-is for now
            logger.info("   Keeping original image (most AI-generated logos already have transparent backgrounds)")
        except Exception as np_error:
            # NumPy error - fallback to keeping original
            logger.warning(f"   NumPy processing error: {str(np_error)}, keeping original image")
        
        # Save transparent logo to memory
        output = io.BytesIO()
        logo_image.save(output, format='PNG', optimize=True)
        output.seek(0)
        
        # Save to storage
        filename = f"generated_logos/user_{user_id}_{uuid.uuid4()}.png"
        logger.info(f"   Saving logo to: {filename}")
        
        try:
            path = default_storage.save(filename, ContentFile(output.read()))
            saved_url = default_storage.url(path)
            logger.info(f"✅ Transparent logo saxlandı: {saved_url}")
            return saved_url
        except Exception as save_error:
            logger.error(f"❌ File save error: {str(save_error)}")
            logger.error(f"   Storage backend: {type(default_storage).__name__}")
            logger.error(f"   MEDIA_ROOT: {getattr(settings, 'MEDIA_ROOT', 'Not set')}")
            raise Exception(f"Logo fayl sisteminə yazıla bilmədi: {str(save_error)}")
            
    except requests.exceptions.Timeout:
        logger.error(f"❌ Logo yükləmə timeout oldu (60 saniyə)")
        raise Exception("Logo yükləmə çox uzun çəkdi. Zəhmət olmasa yenidən cəhd edin.")
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Network error logo yükləyərkən: {str(e)}")
        raise Exception(f"Logo yüklənə bilmədi (şəbəkə xətası): {str(e)}")
    except Exception as e:
        logger.error(f"❌ Logo yüklənmədi: {str(e)}", exc_info=True)
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
        logger.error(f"❌ Validation error: {str(e)}")
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except openai.APITimeoutError as e:
        logger.error(f"❌ OpenAI API timeout: {str(e)}")
        return Response({
            "error": "OpenAI API cavab vermədi. Zəhmət olmasa bir az sonra yenidən cəhd edin.",
            "details": str(e)
        }, status=status.HTTP_504_GATEWAY_TIMEOUT)
    except openai.APIError as e:
        logger.error(f"❌ OpenAI API error: {str(e)}")
        return Response({
            "error": "OpenAI API xətası baş verdi. Zəhmət olmasa API key-in düzgün olduğunu yoxlayın.",
            "details": str(e)
        }, status=status.HTTP_502_BAD_GATEWAY)
    except requests.exceptions.Timeout as e:
        logger.error(f"❌ Request timeout: {str(e)}")
        return Response({
            "error": "Logo yükləmə çox uzun çəkdi. Zəhmət olmasa yenidən cəhd edin.",
            "details": str(e)
        }, status=status.HTTP_504_GATEWAY_TIMEOUT)
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Network error: {str(e)}")
        return Response({
            "error": "Şəbəkə xətası baş verdi. Zəhmət olmasa internet əlaqənizi yoxlayın.",
            "details": str(e)
        }, status=status.HTTP_502_BAD_GATEWAY)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}", exc_info=True)
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"   Traceback: {error_trace}")
        return Response({
            "error": "Logo və slogan yaratma zamanı gözlənilməz xəta baş verdi",
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
@parser_classes([MultiPartParser, FormParser])
def upload_product_image_for_n8n(request):
    """
    Upload product image and return URL for n8n workflow
    
    POST /api/ai/upload-product-image/
    
    Body (multipart/form-data):
    {
        "image": File (required) - Product image file
    }
    
    Returns:
    {
        "success": true,
        "image_url": "https://...",
        "message": "Image uploaded successfully"
    }
    """
    user = request.user
    
    try:
        # Get image file
        image_file = request.FILES.get('image')
        if not image_file:
            return Response({
                "error": "Şəkil faylı tələb olunur"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info(f"📤 Product image upload request from user: {user.email}")
        logger.info(f"   File name: {image_file.name}")
        logger.info(f"   File size: {image_file.size} bytes")
        logger.info(f"   Content type: {image_file.content_type}")
        
        # Reset file pointer before reading
        image_file.seek(0)
        
        # Upload image using existing function with product_images folder
        image_url = upload_product_image(image_file, user.id, folder_name="product_images")
        
        # Make absolute URL if relative - MƏCBURİ
        if not image_url.startswith('http://') and not image_url.startswith('https://'):
            # Build absolute URL
            base_url = request.build_absolute_uri('/').rstrip('/')
            # Ensure image_url doesn't start with / if base_url already ends with /
            if image_url.startswith('/'):
                image_url = f"{base_url}{image_url}"
            else:
                image_url = f"{base_url}/{image_url}"
        
        # Final validation - URL-in düzgün olduğunu yoxla
        if not image_url.startswith('http://') and not image_url.startswith('https://'):
            logger.error(f"❌ URL hələ də absolute deyil: {image_url}")
            raise ValueError(f"URL absolute formatda deyil: {image_url}")
        
        logger.info(f"✅ Product image uploaded: {image_url}")
        logger.info(f"   URL format: {'Absolute' if image_url.startswith('http') else 'Relative'}")
        logger.info(f"   URL length: {len(image_url)}")
        
        return Response({
            "success": True,
            "image_url": image_url,
            "message": "Şəkil uğurla yükləndi"
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"❌ Error uploading product image: {str(e)}", exc_info=True)
        return Response({
            "error": f"Şəkil yüklənərkən xəta baş verdi: {str(e)}"
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


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_product_post(request):
    """
    FOUR-STEP MARKETING WORKFLOW for Product Post Creation (AZERBAIJANI CONTENT)
    
    Execute a comprehensive marketing workflow: background removal, structured product analysis,
    high-conversion content generation (in Azerbaijani), and technical AI prompt creation for Nano Banana.
    
    POST /api/ai/product-post/
    
    Body (multipart/form-data):
    {
        "product_image": File (required) - Product image to process,
        "product_name": str (optional) - Product name (will be AI-suggested if not provided),
        "product_description": str (optional) - Product description,
        "num_images": int (default: 3) - Number of ad variations to generate (1-5)
    }
    
    WORKFLOW STEPS:
    
    1. IMAGE PROCESSING (Background Removal):
       - Accepts uploaded image
       - Digitally removes background to isolate product
       - Creates transparent subject for analysis
    
    2. PRODUCT ANALYSIS (Structured Breakdown):
       - Product Name/Type: Identifies exact product category
       - Color Palette: Primary and secondary colors
       - Material & Texture: Surface materials and finish
       - Intended Use: Product function and purpose
       - Target Industry: Market sector identification
    
    3. ADVERTISING CONTENT GENERATION:
       - Hook: Catchy headline (50-80 chars)
       - Body: Benefits and features (150-250 chars)
       - Call to Action (CTA): Purchase encouragement (40-60 chars)
       - Hashtags: 10-15 relevant, high-traffic hashtags
       - Tone: Professional, engaging, persuasive (Instagram/Facebook style)
    
    4. GENERATIVE AI PROMPT CREATION:
       - Technical prompt optimized for Nano Banana/Stable Diffusion/Midjourney
       - Format: [Subject] + [Action/Pose] + [Context] + [Background] + [Lighting] + [Specs]
       - Goal: Place product in lifestyle context with professional model
       - Example: "Model wearing [Product] walking down busy NY street, golden hour, cinematic 4K"
    
    Returns:
    {
        "success": true,
        "message": "Four-step marketing workflow completed successfully",
        "workflow_summary": {
            "step_1": "Background removal completed",
            "step_2": "Product analysis with structured breakdown completed",
            "step_3": "High-conversion advertising content generated",
            "step_4": "Technical AI prompts created"
        },
        "posts": [
            {
                "id": "uuid",
                "hook": "Catchy headline",
                "body": "Benefits-focused content",
                "cta": "Clear call to action",
                "full_caption": "Complete caption text",
                "hashtags": ["#tag1", "#tag2", ...],
                "complete_content": "Hook + Body + CTA + Hashtags",
                "image_generation_prompt": "Technical prompt for AI image generation",
                "status": "pending_approval",
                "design_context": "Lifestyle photography context"
            },
            ...
        ],
        "product_analysis": {
            "product_name_type": "Exact product name and type",
            "product_type": "Category",
            "color_palette": {
                "primary_colors": [...],
                "secondary_colors": [...],
                "color_description": "..."
            },
            "material_texture": {
                "materials": [...],
                "texture": "...",
                "finish": "..."
            },
            "intended_use": "Function and purpose",
            "target_industry": "Market sector",
            "visual_analysis": {...},
            "features": [...],
            "benefits": [...],
            "target_audience": "...",
            "selling_points": [...],
            "lifestyle_context": "..."
        },
        "images": {
            "original_image_url": "https://...",
        "background_removed_image_url": "https://..."
        },
        "num_created": 3
    }
    """
    user = request.user
    
    try:
        # Get product image
        product_image = request.FILES.get('product_image')
        if not product_image:
            return Response({
                "error": "Məhsul rəsmi tələb olunur"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        product_name = request.data.get('product_name', '')
        product_description = request.data.get('product_description', '')
        num_images = int(request.data.get('num_images', 3))
        
        logger.info(f"🛍️ Product post creation request from user: {user.email}")
        logger.info(f"   Product name: {product_name}")
        logger.info(f"   Number of images: {num_images}")
        
        # Step 1: Save product image to local storage
        logger.info("📤 Step 1: Saving product image to local storage...")
        
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile
        
        # Save product image to media folder
        product_image.seek(0)  # Reset file pointer
        product_filename = f"product_images/product_{uuid.uuid4()}.{product_image.name.split('.')[-1]}"
        saved_path = default_storage.save(product_filename, product_image)
        
        # Get URL for the saved image
        from django.conf import settings
        base_url = request.build_absolute_uri('/').rstrip('/')
        media_url = getattr(settings, 'MEDIA_URL', '/media/')
        if not media_url.startswith('http'):
            original_image_url = f"{base_url}{media_url}{saved_path}"
        else:
            original_image_url = f"{media_url}{saved_path}"
        
        logger.info(f"✅ Product image saved to: {saved_path}")
        logger.info(f"✅ Product image URL: {original_image_url}")
        
        # Step 2: Remove background using Fal.ai
        # NOTE: Background removal might not work perfectly, so we'll use original image if needed
        background_removed_url = None
        if FAL_AI_AVAILABLE:
            try:
                logger.info("🎨 Step 2: Attempting background removal...")
                fal_service = FalAIService(user=user)
                
                # Try to remove background, but use lower strength to preserve product
                bg_removal_result = fal_service.edit_image(
                    image_url=original_image_url,
                    prompt="remove background completely, make background transparent, keep product exactly as is, do not modify product",
                    strength=0.7  # Lower strength to preserve product better
                )
                
                background_removed_url = bg_removal_result['image_url']
                logger.info(f"✅ Background removal attempted: {background_removed_url}")
            except Exception as e:
                logger.warning(f"⚠️ Background removal failed: {str(e)}, using original image")
                background_removed_url = original_image_url
        else:
            logger.warning("⚠️ Fal.ai not available, using original image")
            background_removed_url = original_image_url
        
        # For image-to-image, we'll use the original image if background removal didn't work well
        # This ensures the product is preserved
        image_for_generation = background_removed_url if background_removed_url != original_image_url else original_image_url
        
        # Step 3: Analyze product using ChatGPT (ENHANCED WITH STRUCTURED BREAKDOWN)
        logger.info("🔍 Step 3: Analyzing product with structured breakdown...")
        product_analysis = None
        product_type = None
        
        # Use product_name from user, or ask ChatGPT to suggest based on description
        final_product_name = product_name.strip() if product_name else None
        
        try:
            openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            
            # If user didn't provide name, ask ChatGPT to suggest one based on description
            if not final_product_name and product_description:
                logger.info("💡 Asking ChatGPT to suggest product name...")
                name_response = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "Sən peşəkar məhsul analitiçisisin. Məhsulun təsvirinə əsasən dəqiq məhsul adını müəyyənləşdirirsən."
                        },
                        {
                            "role": "user",
                            "content": f"""Aşağıdakı məhsul təsvirinə əsasən konkret məhsul adını müəyyənləşdir. Generic adlar yazma (məsələn: "telefon", "qulaqcıq"), konkret ad yaz (məsələn: "iPhone 15 Pro", "AirPods Pro").

Məhsul təsviri: {product_description}

Yalnız məhsulun adını yaz, əlavə mətn yazma."""
                        }
                    ],
                    temperature=0.7,
                    max_tokens=50
                )
                suggested_name = name_response.choices[0].message.content.strip()
                if suggested_name and len(suggested_name) > 2:
                    final_product_name = suggested_name
                    logger.info(f"✅ ChatGPT suggested product name: {final_product_name}")
            
            # If still no name, use default
            if not final_product_name:
                final_product_name = "Məhsul"
            
            # ENHANCED: Structured product analysis matching the required format (AZERBAIJANI)
            analysis_prompt = f"""Aşağıdakı məhsul üçün ətraflı vizual yoxlama aparın və STRUKTURLAŞDIRILMIŞ ANALİZ təqdim edin. JSON formatında cavab verin:

Məhsul Adı: {final_product_name}
Məhsul Təsviri: {product_description or 'Təsvir verilməyib'}

TƏLƏBOLUNANstrukturu:
{{
    "product_name_type": "Dəqiq məhsul adı və növü (məsələn: 'Simsiz Bluetooth Qulaqcıq', 'Dəri Çanta', 'Ağıllı Saat')",
    "product_type": "Kateqoriya növü (məsələn: Elektronika, Moda, Ev Dekorasiyası, Aksesuar)",
    "color_palette": {{
        "primary_colors": ["Əsas rəng 1", "Əsas rəng 2"],
        "secondary_colors": ["Aksent rəng 1", "Aksent rəng 2"],
        "color_description": "Rəng sxeminin qısa təsviri"
    }},
    "material_texture": {{
        "materials": ["Əsas material", "İkinci material"],
        "texture": "Ətraflı tekstura təsviri (məsələn: Hamar İpək, Fırçalanmış Metal, Mat Plastik, Yumşaq Dəri)",
        "finish": "Səth üzlüyü (məsələn: Parlaq, Mat, Fırçalanmış, Cilalanmış)"
    }},
    "intended_use": "Məhsulun funksiyası və məqsədi nədir? (1-2 cümlə)",
    "target_industry": "Əsas sənaye/bazar sektoru (məsələn: Moda və Geyim, İstehlak Elektronikası, Ev və Yaşayış, Gözəllik və Kosmetika)",
    "visual_analysis": {{
        "shape": "Ətraflı forma təsviri",
        "size": "Ölçü təsviri",
        "design_style": "Dizayn stili (məsələn: Minimalist, Müasir, Klassik, Vintage, Çağdaş)",
        "special_details": "Unikal xüsusiyyətlər və detallar"
    }},
    "features": ["Əsas xüsusiyyət 1", "Əsas xüsusiyyət 2", "Əsas xüsusiyyət 3"],
    "benefits": ["Fayda 1", "Fayda 2", "Fayda 3"],
    "target_audience": "Hədəf demoqrafik təsvir",
    "selling_points": ["Satış nöqtəsi 1", "Satış nöqtəsi 2", "Satış nöqtəsi 3"],
    "keywords": ["açar söz 1", "açar söz 2", "açar söz 3"],
    "visual_description": "Tam vizual təsvir (rəng, forma, material, dizayn, detallar - 150-200 simvol)",
    "lifestyle_context": "Fotoqrafiya üçün təklif olunan həyat tərzi konteksti (məsələn: 'Şəhər peşəkar mühiti', 'Açıq hava macəra səhnəsi', 'Lüks ev interyeri')"
}}

Yalnız JSON cavab verin, əlavə mətn yazMAYIN."""
            
            logger.info("🤖 Getting structured product analysis from ChatGPT...")
            analysis_response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Sən ekspert məhsul analitiki və marketinq strateqisən. Sən ətraflı, strukturlaşdırılmış məhsul analizi təqdim edirsən. Həmişə Azərbaycan dilində JSON formatında cavab verirsən."
                    },
                    {
                        "role": "user",
                        "content": analysis_prompt
                    }
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            analysis_text = analysis_response.choices[0].message.content.strip()
            # Remove markdown code blocks if present
            if analysis_text.startswith('```json'):
                analysis_text = analysis_text[7:]
            if analysis_text.startswith('```'):
                analysis_text = analysis_text[3:]
            if analysis_text.endswith('```'):
                analysis_text = analysis_text[:-3]
            analysis_text = analysis_text.strip()
            
            product_analysis = json.loads(analysis_text)
            product_type = product_analysis.get('product_type', 'məhsul')
            
            # Ensure product_name is set correctly
            product_analysis['name'] = final_product_name
            product_analysis['product_name'] = final_product_name
            
            # Override description if user provided one
            if product_description:
                product_analysis['description'] = product_description
            
            logger.info(f"✅ Product analyzed: {final_product_name} (Type: {product_type})")
            
        except Exception as e:
            logger.error(f"❌ Product analysis failed: {str(e)}", exc_info=True)
            # Use fallback analysis
            product_analysis = {
                "name": final_product_name or "Məhsul",
                "product_name": final_product_name or "Məhsul",
                "product_type": "məhsul",
                "product_category": "ümumi",
                "description": product_description or "Məhsul təsviri",
                "visual_description": "Məhsulun vizual təsviri",
                "features": [],
                "benefits": [],
                "target_audience": "Geniş auditoriya",
                "selling_points": [],
                "keywords": []
            }
            product_type = "məhsul"
        
        # Step 4: Generate HIGH-CONVERSION ADVERTISING CONTENT (Instagram/Facebook Style - AZERBAIJANI)
        logger.info("✍️ Step 4: Generating high-conversion social media content in Azerbaijani...")
        generated_content = None
        try:
            content_prompt = f"""Aşağıdaki məhsul üçün {num_images} dənə cəlbedici, yüksək konversiyalı sosial media başlıqları yaradın (Instagram/Facebook stili):

Məhsul Analizi:
{json.dumps(product_analysis, ensure_ascii=False, indent=2)}

ÇOX VACİB: Məhsulun adı "{product_analysis.get('name', 'Məhsul')}"-dır. Postlarda konkret məhsul adını istifadə edin - generic terminlər yazmayın!

TON: Peşəkar, cəlbedici və inandırıcı

HƏR POST ÜÇÜN STRUKTUR (QATI FORMAT):
1. HOOK (QARMAQÇQə - diqqəti cəlb edən başlıq (1 güclü cümlə, 50-80 simvol)
2. BODY (ƏSAS MƏTN): Faydaları və xüsusiyyətləri vurğulayın (2-3 cümlə, 150-250 simvol)
   - Müştərinin əldə etdiklərinə fokuslanın
   - Emosional təsirlər istifadə edin
   - Unikal satış nöqtələrini vurğulayın
3. CALL TO ACTION (CTA - FƏALIYYƏTƏ ÇAĞIRIŞ): Alışı və ya qarşılıqlı əlaqəni təşviq edin (1 aydın cümlə, 40-60 simvol)
   - Nümunələr: "İndi sifariş et!", "Bu günə sənin olsun!", "Məhdud sayda!", "Həyatını dəyişdir!"
4. HASHTAGS (HEŞTEQLƏR): 10-15 relevant, yüksək trafikli heşteq

JSON formatında cavab verin:
{{
    "posts": [
        {{
            "hook": "Diqqəti cəlb edən cəlbedici başlıq",
            "body": "Faydaya fokuslanmış məzmun, xüsusiyyətləri vurğulayır. Dəyər təklifini vurğulayın. Arzu yaradın.",
            "cta": "Qarşılıqlı əlaqəni təşviq edən aydın fəaliyyətə çağırış",
            "hashtags": ["#heşteq1", "#heşteq2", "#heşteq3", ... (10-15 heşteq)],
            "full_caption": "Hook + Body + CTA birləşdirilmiş tam başlıq",
            "design_context": "Həyat tərzi fotoqrafiya konteksti (məsələn: 'Model məhsulu şəhər küçəsində geyinir', 'Məhsul müasir iş yerində', 'Məhsul lüks həyat tərzi mühitində')"
        }},
        ...
    ]
}}

HEŞTEQ TƏLƏBLƏRİ:
- Populyar (#moda, #stil, #baku, #azerbaijan) və niş heştəqlərin qarışığı
- Məhsul kateqoriyası heştəqləri daxil edin
- Həyat tərzi/istək heştəqləri daxil edin
- Fəaliyyət/CTA heştəqləri daxil edin (#indisifariş, #məhdudsay)
- Həm Azərbaycan, həm də beynəlxalq heştəqlər istifadə edin

Yalnız JSON cavab verin, əlavə mətn yazMAYIN."""
            
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Sən peşəkar sosial media marketinq eksperti və yüksək konversiyalı reklam məzmunu yaratmaqda ixtisaslaşan kopyraytersən. Həmişə Azərbaycan dilində JSON formatında cavab verirsən."
                    },
                    {
                        "role": "user",
                        "content": content_prompt
                    }
                ],
                temperature=0.8,
                max_tokens=3000
            )
            
            content_text = response.choices[0].message.content.strip()
            # Remove markdown code blocks
            if content_text.startswith('```json'):
                content_text = content_text[7:]
            if content_text.startswith('```'):
                content_text = content_text[3:]
            if content_text.endswith('```'):
                content_text = content_text[:-3]
            content_text = content_text.strip()
            
            generated_content = json.loads(content_text)
            logger.info(f"✅ Content generated: {len(generated_content.get('posts', []))} posts")
        except Exception as e:
            logger.error(f"❌ Content generation failed: {str(e)}", exc_info=True)
            return Response({
                "error": f"Məzmun yaradıla bilmədi: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Step 5: Generate TECHNICAL PROMPTS for Nano Banana / Stable Diffusion (OPTIMIZED FORMAT)
        logger.info("📝 Step 5: Generating technical AI prompts for image generation...")
        posts_data = generated_content.get('posts', [])
        created_posts = []
        
        # Extract detailed analysis for prompt generation
        color_palette = product_analysis.get('color_palette', {})
        primary_colors = color_palette.get('primary_colors', [])
        secondary_colors = color_palette.get('secondary_colors', [])
        
        material_texture = product_analysis.get('material_texture', {})
        materials = material_texture.get('materials', [])
        texture = material_texture.get('texture', '')
        finish = material_texture.get('finish', '')
        
        visual_analysis = product_analysis.get('visual_analysis', {})
        design_style = visual_analysis.get('design_style', 'modern')
        shape = visual_analysis.get('shape', '')
        
        product_name_type = product_analysis.get('product_name_type', product_analysis.get('name', 'Product'))
        product_type = product_analysis.get('product_type', 'Product')
        visual_description = product_analysis.get('visual_description', '')
        lifestyle_context = product_analysis.get('lifestyle_context', 'professional studio setting')
        
        logger.info(f"📝 Generating {num_images} technical prompts optimized for Nano Banana/Stable Diffusion...")
        
        for idx, post_data in enumerate(posts_data[:num_images], 1):
            try:
                logger.info(f"🎨 Creating technical prompt {idx}/{num_images}...")
                
                # Get design context from generated content
                design_context = post_data.get('design_context', lifestyle_context)
                
                # TECHNICAL PROMPT FORMAT for Nano Banana (AZERBAIJANI): [Subject] + [Action/Pose] + [Outfit/Context] + [Background/Environment] + [Lighting/Style] + [Aspect Ratio]
                
                # HƏR POST ÜÇÜN TAMAMİLƏ FƏRQLİ SƏHNƏLƏR - 10+ müxtəlif variant
                scenes = [
                    {
                        "action": "peşəkar biznes modeli məhsulu tutub nümayiş etdirir",
                        "pose": "özünəinamlı poz, birbaşa göz təması, gülümsəmə",
                        "context": "qızıl saat vaxtı işıqlı Nyu York küçəsində gəzir",
                        "background": "bulanıq şəhər mənzərəsi bokeh effekti ilə, yumşaq axşam işıqları, sarı taksi, insanlar",
                        "lighting": "qızıl saat işıqlandırması, isti gün batımı tonları, subyektdə halə işıqlandırması",
                        "style": "urban professional, street fashion, cinematic",
                        "mood": "energetic, confident, urban lifestyle"
                    },
                    {
                        "action": "həyat tərzi modeli məhsulu təbii şəkildə istifadə edir",
                        "pose": "təbii poz, məhsulla səmimi qarşılıqlı əlaqə, rahat",
                        "context": "lüks atmosferli müasir minimalist studiya",
                        "background": "təmiz ağ/boz qradiyent fon, peşəkar studiya quruluşu, minimal dekor",
                        "lighting": "peşəkar studiya işıqlandırması, yumşaq əsas işıq, incə doldurma işığı, dramatik halə işığı",
                        "style": "minimalist, clean, luxury studio",
                        "mood": "serene, elegant, sophisticated"
                    },
                    {
                        "action": "peşəkar model məhsulu zərif şəkildə nümayiş etdirir",
                        "pose": "dinamik hərəkət pozu, üçdördə bucaq, əl hərəkəti",
                        "context": "müasir memarlıqlı yüksək səviyyəli şəhər mühiti",
                        "background": "müasir memarlıq elementləri, şüşə və polad strukturlar, dərinlik sahəsi, qeyri-müəyyən binalar",
                        "lighting": "təbii gün işığı peşəkar işıqlandırma ilə qarışıq, kinematik rəng qreydini",
                        "style": "architectural, contemporary, modern",
                        "mood": "dynamic, professional, aspirational"
                    },
                    {
                        "action": "gənc peşəkar qadın məhsulu göstərir",
                        "pose": "düz dayanmış, məhsulu yuxarı tutub, güclü baxış",
                        "context": "müasir ofis mühiti, şüşə divarlar, müasir mebel",
                        "background": "blurred office environment, glass walls, modern furniture, city view through windows",
                        "lighting": "bright natural daylight, soft window light, professional office lighting",
                        "style": "corporate, professional, business",
                        "mood": "confident, powerful, successful"
                    },
                    {
                        "action": "model məhsulu kafe mühitində istifadə edir",
                        "pose": "oturmuş poz, məhsulu masada göstərir, rahat",
                        "context": "trendy urban cafe, wooden tables, plants",
                        "background": "cozy cafe interior, blurred background, warm atmosphere, coffee cups, plants",
                        "lighting": "warm ambient lighting, soft natural light from windows, cozy atmosphere",
                        "style": "lifestyle, casual, warm",
                        "mood": "relaxed, comfortable, everyday luxury"
                    },
                    {
                        "action": "peşəkar model məhsulu açıq havada nümayiş etdirir",
                        "pose": "gəzinti pozu, məhsulu təbii şəkildə tutub, gülümsəmə",
                        "context": "park və ya bağ mühiti, ağaclar, çiçəklər",
                        "background": "blurred park scenery, trees, flowers, green nature, soft bokeh",
                        "lighting": "soft natural daylight, dappled sunlight through trees, fresh outdoor lighting",
                        "style": "natural, outdoor, fresh",
                        "mood": "fresh, natural, vibrant"
                    },
                    {
                        "action": "model məhsulu lüks interyerdə göstərir",
                        "pose": "zərif poz, məhsulu dəbdəbəli mühitdə nümayiş etdirir",
                        "context": "lüks ev interyeri, dəbdəbəli mebel, incəsənət əsərləri",
                        "background": "luxury home interior, elegant furniture, art pieces, marble surfaces, gold accents",
                        "lighting": "dramatic interior lighting, warm golden tones, elegant shadows",
                        "style": "luxury, opulent, high-end",
                        "mood": "luxurious, elegant, premium"
                    },
                    {
                        "action": "gənc model məhsulu şəhər panoraması ilə göstərir",
                        "pose": "balkon və ya terrasda, məhsulu şəhərə doğru tutub",
                        "context": "yüksək bina balkonu, şəhər panoraması",
                        "background": "city skyline panorama, tall buildings, urban landscape, distant view",
                        "lighting": "bright daylight, clear sky, urban atmosphere, professional",
                        "style": "panoramic, urban, expansive",
                        "mood": "aspirational, grand, impressive"
                    },
                    {
                        "action": "model məhsulu qaranlıq studiyada nümayiş etdirir",
                        "pose": "dramatik poz, kontrast işıqlandırma, güclü siluet",
                        "context": "qaranlıq studiya, minimal dekor",
                        "background": "dark studio background, dramatic shadows, minimal setup, professional",
                        "lighting": "dramatic studio lighting, high contrast, rim lighting, moody atmosphere",
                        "style": "dramatic, high-contrast, artistic",
                        "mood": "dramatic, bold, artistic"
                    },
                    {
                        "action": "model məhsulu dəniz kənarında göstərir",
                        "pose": "rahat poz, dənizə baxır, məhsulu təbii şəkildə tutub",
                        "context": "dəniz kənarı, qum, dalğalar",
                        "background": "ocean beach, waves, sand, blue sky, coastal scenery, blurred",
                        "lighting": "bright coastal daylight, blue sky reflection, fresh ocean atmosphere",
                        "style": "coastal, fresh, vacation",
                        "mood": "relaxed, vacation, premium lifestyle"
                    }
                ]
                
                # Hər post üçün fərqli scene seç (idx-1 istifadə edirik çünki idx 1-dən başlayır)
                scene = scenes[(idx - 1) % len(scenes)]
                
                logger.info(f"   Scene {idx}: {scene['style']} - {scene['mood']} - {scene['context']}")
                
                # HƏR POST ÜÇÜN FƏRQLİ STİL VƏ MOOD (10 müxtəlif variant)
                styles = [
                    "modern, premium, luxury advertising",
                    "contemporary, sleek, high-end commercial",
                    "sophisticated, elegant, professional",
                    "dynamic, energetic, urban",
                    "minimalist, clean, refined",
                    "artistic, creative, unique",
                    "corporate, professional, business",
                    "lifestyle, casual, approachable",
                    "dramatic, bold, impactful",
                    "natural, fresh, authentic"
                ]
                
                lighting_styles = [
                    "studio lighting, professional photography, high-end commercial, golden hour, soft shadows",
                    "natural daylight, soft window light, professional office lighting, bright and clear",
                    "dramatic studio lighting, high contrast, rim lighting, moody atmosphere",
                    "warm ambient lighting, cozy atmosphere, soft natural light",
                    "bright coastal daylight, blue sky reflection, fresh atmosphere",
                    "qızıl saat işıqlandırması, isti tonlar, halə effekti",
                    "peşəkar studiya işığı, yumşaq əsas işıq, dramatik halə",
                    "təbii gün işığı, kinematik rəng qreydini",
                    "dramatik interyer işığı, isti qızıl tonlar",
                    "parlaq gün işığı, aydın göy, təzə atmosfer"
                ]
                
                # MODERN DİZAYN ELEMENTLƏRİ - Aurora-like effects, glowing lights, gradients
                modern_design_elements = [
                    {
                        "background": "vibrant teal to emerald green gradient background, aurora-like glowing arc effect in upper half, abstract glowing light streaks, dynamic energy",
                        "effects": "glowing aurora borealis effect, bright horizontal light line creating horizon, glossy reflective surface, modern luxury aesthetic",
                        "colors": "deep teal transitioning to bright emerald green, white glowing accents, metallic reflections"
                    },
                    {
                        "background": "purple to pink gradient background, neon light streaks, cyberpunk-inspired glowing effects, futuristic atmosphere",
                        "effects": "neon glow effects, electric light streaks, holographic reflections, modern tech aesthetic",
                        "colors": "deep purple to vibrant pink gradient, cyan neon accents, metallic silver highlights"
                    },
                    {
                        "background": "blue to cyan gradient background, flowing light waves, ethereal glow effects, dynamic movement",
                        "effects": "flowing light waves, soft glow halos, water-like reflections, serene modern aesthetic",
                        "colors": "deep blue to bright cyan gradient, white light accents, glass-like transparency"
                    },
                    {
                        "background": "orange to red gradient background, fire-like glowing effects, warm energy waves, passionate atmosphere",
                        "effects": "fire-like glowing streaks, warm energy waves, dramatic light flares, energetic modern aesthetic",
                        "colors": "deep orange to vibrant red gradient, golden light accents, warm reflections"
                    },
                    {
                        "background": "gold to amber gradient background, luxury light rays, premium glow effects, opulent atmosphere",
                        "effects": "luxury light rays, golden glow halos, premium reflections, high-end aesthetic",
                        "colors": "rich gold to warm amber gradient, white luxury accents, metallic gold highlights"
                    },
                    {
                        "background": "indigo to violet gradient background, cosmic light effects, star-like glows, mystical atmosphere",
                        "effects": "cosmic light streaks, star-like sparkles, nebula-like glow, mystical modern aesthetic",
                        "colors": "deep indigo to vibrant violet gradient, silver star accents, cosmic blue highlights"
                    },
                    {
                        "background": "turquoise to mint green gradient background, fresh light waves, natural glow effects, refreshing atmosphere",
                        "effects": "fresh light waves, natural glow halos, water-like transparency, clean modern aesthetic",
                        "colors": "bright turquoise to mint green gradient, white fresh accents, crystal-like clarity"
                    },
                    {
                        "background": "coral to peach gradient background, warm sunset glow, soft light rays, cozy atmosphere",
                        "effects": "warm sunset glow, soft light rays, gentle reflections, inviting modern aesthetic",
                        "colors": "vibrant coral to soft peach gradient, golden light accents, warm highlights"
                    },
                    {
                        "background": "navy to royal blue gradient background, electric light bolts, dynamic energy, powerful atmosphere",
                        "effects": "electric light bolts, dynamic energy waves, powerful glow effects, strong modern aesthetic",
                        "colors": "deep navy to royal blue gradient, electric blue accents, metallic highlights"
                    },
                    {
                        "background": "magenta to fuchsia gradient background, vibrant neon glow, electric atmosphere, bold modern aesthetic",
                        "effects": "vibrant neon glow, electric light streaks, bold reflections, striking modern aesthetic",
                        "colors": "rich magenta to fuchsia gradient, bright pink accents, neon highlights"
                    }
                ]
                
                selected_style = styles[(idx - 1) % len(styles)]
                selected_lighting = lighting_styles[(idx - 1) % len(lighting_styles)]
                design_element = modern_design_elements[(idx - 1) % len(modern_design_elements)]
                
                logger.info(f"   Style: {selected_style}")
                logger.info(f"   Lighting: {selected_lighting[:80]}...")
                logger.info(f"   Design Element: {design_element['background'][:60]}...")
                
                # Build UNIQUE TECHNICAL PROMPT for each post (AZERBAIJANI)
                # HƏR POST ÜÇÜN TAMAMİLƏ FƏRQLİ PROMPT + MODERN DİZAYN ELEMENTLƏRİ
                image_generation_prompt = f"""Professional product advertising photography, ultra realistic, 8K quality, modern luxury aesthetic

[SUBYEKTİ İSTİNAD]: Peşəkar moda/həyat tərzi modeli (yaş 25-35, cəlbedici, baxımlı) {product_name_type} məhsulunu təqdim edir. Məhsul detalları: {visual_description}. Rənglər: {', '.join(primary_colors) if primary_colors else 'original'} əsas rənglərlə {', '.join(secondary_colors) if secondary_colors else 'original'} aksent rəngləri. Materiallar: {', '.join(materials) if materials else 'original'}. Tekstura: {texture if texture else 'original'}. Üzlük: {finish if finish else 'original'}.

[HƏRƏKƏT/POZ]: {scene['action']}, {scene['pose']}

[GEYİM/KONTEKST]: {scene['context']}. Model məhsulu tamamlayan, lakin onunla rəqabət aparmayan geyim geyinir. Peşəkar stilizasiya, {scene['mood']} atmosfer.

[MODERN FON DİZAYNI]: {design_element['background']}. {design_element['effects']}. {design_element['colors']}. Peşəkar kommersiya fotoqrafiyası çəkiliş, {scene['style']} dizayn, modern luxury aesthetic.

[İŞIQLANDIRMA/STİL]: {scene['lighting']}. {design_element['effects']}. Kinematik 4K keyfiyyət. Yüksək səviyyəli kommersiya fotoqrafiyası. Peşəkar rəng qreydini. Məhsul və modeldə kəskin fokus. {scene['mood']} əhval-ruhiyyə, {scene['style']} estetikası, modern dynamic energy.

[TEXNİKİ SPESIFIKASIYALAR]: Aspekt nisbəti: 16:9, Rezolyusiya: 4K UHD, Stil: {selected_style}, Keyfiyyət: Ultra yüksək keyfiyyət, peşəkar retouching

[KRİTİK TƏLIMATLAR]:
- Məhsul orijinal şəkildə göstərildiyi kimi TAM OLARAQ qalmalıdır
- Məhsulu dəyişdirməyin, modifikasiya etməyin və ya əvəz etməyin
- Bütün məhsul detallarını, rəngləri, materialları və dizaynı eyni saxlayın
- Yalnız fonu, ətraf mühiti dəyişdirin və model əlavə edin
- Fokus: Həm məhsulda, həm də modeldə kəskin
- Əhval-ruhiyyə: {scene['mood']}, yüksək konversiyalı reklam, modern luxury
- Kompozisiya: Üçdə bir qaydası, peşəkar kommersiya tərtibatı, {scene['style']} kompozisiya

Lighting: {selected_lighting}, {design_element['effects']}
Quality: ultra realistic, 8K, professional photography, sharp focus, detailed
Style: {selected_style}, {scene['mood']} atmosphere, {scene['style']} composition, modern luxury aesthetic
Mood: {scene['mood']}, {selected_style}, dynamic energy, premium luxury
Background: {design_element['background']}, {design_element['effects']}, {design_element['colors']}
Effects: glowing aurora effects, abstract light streaks, gradient transitions, modern luxury aesthetic, dynamic energy"""
                
                # Step 5: Generate image using Nano Banana with the created prompt
                generated_image_url = None
                if FAL_AI_AVAILABLE:
                    try:
                        logger.info(f"🎨 Step 5: Nano Banana ilə şəkil yaradılır {idx}/{num_images}...")
                        logger.info(f"   Input image: {background_removed_url}")
                        logger.info(f"   Prompt: {image_generation_prompt[:200]}...")
                        
                        # Use image-to-image with lower strength to preserve product
                        nano_result = fal_service.image_to_image(
                            image_url=background_removed_url,
                            prompt=image_generation_prompt,
                            strength=0.6  # Lower strength to preserve product details
                        )
                        
                        # Download and save the generated image
                        if nano_result and nano_result.get('image_url'):
                            logger.info(f"✅ Nano Banana şəkil yaradıldı: {nano_result['image_url']}")
                            
                            # Download and save to storage with unique name per post
                            scene_name = scene['style'].replace(' ', '_').replace(',', '').lower()[:30]
                            prefix = f"product_ad_{scene_name}_post{idx}"
                            saved_url = fal_service.download_and_save(
                                nano_result['image_url'],
                                user.id,
                                prefix=prefix
                            )
                            
                            # Convert to full URL if needed (saved_url is like /media/...)
                            if saved_url and not saved_url.startswith('http'):
                                from django.conf import settings
                                base_url = request.build_absolute_uri('/').rstrip('/')
                                # saved_url already includes /media/, so just prepend base_url
                                if saved_url.startswith('/'):
                                    generated_image_url = f"{base_url}{saved_url}"
                                else:
                                    generated_image_url = f"{base_url}/{saved_url}"
                            else:
                                generated_image_url = saved_url
                            
                            logger.info(f"✅ Şəkil saxlanıldı: {generated_image_url}")
                        else:
                            logger.warning("⚠️ Nano Banana nəticə qaytarmadı")
                            
                    except Exception as nano_error:
                        logger.error(f"❌ Nano Banana xətası: {str(nano_error)}", exc_info=True)
                        logger.info("   Prompt saxlanacaq, şəkil manual yaradıla bilər")
                else:
                    logger.info("   Fal.ai mövcud deyil, yalnız prompt yaradıldı")
                
                # Create post WITH generated image
                from posts.models import Post
                
                # Extract structured content
                hook = post_data.get('hook', '')
                body = post_data.get('body', '')
                cta = post_data.get('cta', '')
                full_caption = post_data.get('full_caption', f"{hook}\n\n{body}\n\n{cta}")
                hashtags = post_data.get('hashtags', [])
                
                # Format hashtags properly
                hashtags_str = ' '.join(hashtags) if hashtags else ''
                
                # Combine full content
                complete_content = f"{full_caption}\n\n{hashtags_str}".strip()
                
                post = Post.objects.create(
                    user=user,
                    title=hook if hook else f"{product_name_type} - Ad {idx}",
                    content=complete_content,
                    hashtags=hashtags,
                    description=body[:200] if body else '',
                    image_url=generated_image_url or '',  # Nano Banana generated image or empty
                    ai_generated=True,
                    ai_prompt=image_generation_prompt,
                    status='pending_approval',
                    requires_approval=True
                )
                
                created_posts.append({
                    "id": str(post.id),
                    "hook": hook,
                    "body": body,
                    "cta": cta,
                    "full_caption": full_caption,
                    "hashtags": hashtags,
                    "complete_content": complete_content,
                    "image_url": generated_image_url,  # Nano Banana generated image
                    "image_generation_prompt": image_generation_prompt,  # Include prompt in response
                    "status": post.status,
                    "design_context": post_data.get('design_context', '')
                })
                
                if generated_image_url:
                    logger.info(f"✅ Post {idx} yaradıldı (Nano Banana şəkil ilə): {post.id}")
                else:
                    logger.info(f"✅ Post {idx} yaradıldı (prompt ilə, şəkil yoxdur): {post.id}")
                
            except Exception as e:
                logger.error(f"❌ Failed to create post {idx}: {str(e)}", exc_info=True)
                continue
        
        if not created_posts:
            return Response({
                "error": "Heç bir post yaradıla bilmədi"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        logger.info(f"✅ Successfully created {len(created_posts)} product posts with complete workflow")
        
        # Prepare structured response (AZERBAIJANI)
        return Response({
            "success": True,
            "message": "Dörd addımlı marketinq iş axını uğurla tamamlandı",
            "workflow_summary": {
                "step_1": "Arxa fon silmə tamamlandı",
                "step_2": "Strukturlaşdırılmış məhsul analizi tamamlandı",
                "step_3": "Yüksək konversiyalı reklam məzmunu yaradıldı",
                "step_4": "Texniki AI promptları yaradıldı",
                "step_5": "Nano Banana ilə professional şəkillər yaradıldı"
            },
            "posts": created_posts,
            "product_analysis": {
                "product_name_type": product_analysis.get('product_name_type', ''),
                "product_type": product_analysis.get('product_type', ''),
                "color_palette": product_analysis.get('color_palette', {}),
                "material_texture": product_analysis.get('material_texture', {}),
                "intended_use": product_analysis.get('intended_use', ''),
                "target_industry": product_analysis.get('target_industry', ''),
                "visual_analysis": product_analysis.get('visual_analysis', {}),
                "features": product_analysis.get('features', []),
                "benefits": product_analysis.get('benefits', []),
                "target_audience": product_analysis.get('target_audience', ''),
                "selling_points": product_analysis.get('selling_points', []),
                "lifestyle_context": product_analysis.get('lifestyle_context', '')
            },
            "images": {
                "original_image_url": original_image_url,
                "background_removed_image_url": background_removed_url
            },
            "num_created": len(created_posts)
        }, status=status.HTTP_201_CREATED)
        
    except ValueError as e:
        logger.error(f"❌ Validation error: {str(e)}")
        return Response({
            "error": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"❌ Product post creation error: {str(e)}", exc_info=True)
        return Response({
            "error": f"Məhsul postu yaradıla bilmədi: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# TODO: Gələcəkdə aktivləşdiriləcək - URL-dən məhsul postu yaratma funksiyası
# NOTE: Bu funksiya hələlik yarımçıq qalıb və işləmir
# Gələcəkdə tamamlanacaq və aktivləşdiriləcək
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_product_post_from_url(request):
    """
    TODO: GƏLƏCƏKDƏ AKTİVLƏŞDİRİLƏCƏK
    
    YENİ FUNKSİYA: Sayt linkindən məhsul məlumatlarını çəkib avtomatik post yaradır
    
    Workflow:
    1. URL-dən səhifə məzmununu çəkir (web scraping)
    2. AI ilə məhsul məlumatlarını analiz edir (ad, təsvir, şəkil)
    3. Məhsul şəklini yükləyir
    4. create_product_post ilə eyni 5 addımlı prosesi tətbiq edir
    
    Request body:
    {
        "product_url": "https://example.com/product/123",
        "num_images": 1  // optional, default 1
    }
    
    Response: create_product_post ilə eyni format + source info
    
    STATUS: Hələlik işləmir - gələcəkdə tamamlanacaq
    """
    # TODO: Gələcəkdə aktivləşdiriləcək - hələlik funksiya işləmir
    # NOTE: Bu funksiya yarımçıq qalıb və gələcəkdə tamamlanacaq
    return Response({
        "error": "Bu funksiya hələlik işləmir. Gələcəkdə aktivləşdiriləcək. Hələlik məhsul şəklini yükləyərək post yarada bilərsiniz.",
        "status": "not_implemented"
    }, status=status.HTTP_501_NOT_IMPLEMENTED)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def analyze_image_and_create_post(request):
    """
    Analyze generated ad image with OpenAI Vision API and create post
    
    POST /api/ai/analyze-image-and-create-post/
    
    Body (JSON):
    {
        "image_url": "https://...",  // Required - URL of the generated ad image
        "product_name": "Product Name"  // Optional
    }
    
    Returns:
    {
        "success": true,
        "post": {
            "id": "uuid",
            "title": "...",
            "content": "...",
            "hashtags": [...],
            "image_url": "...",
            "status": "pending_approval"
        }
    }
    """
    user = request.user
    
    try:
        image_url = request.data.get('image_url')
        product_name = request.data.get('product_name', '')
        
        if not image_url:
            return Response({
                "error": "Şəkil URL-i tələb olunur"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info(f"🖼️ Şəkil analizi və post yaradılması - User: {user.email}")
        logger.info(f"   Image URL: {image_url}")
        
        # Step 1: Download image and convert to base64
        logger.info("📥 Şəkil yüklənir...")
        try:
            image_response = requests.get(image_url, timeout=30)
            image_response.raise_for_status()
            image_data = image_response.content
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Detect content type
            content_type = image_response.headers.get('Content-Type', 'image/jpeg')
            if 'png' in content_type.lower():
                data_url_format = 'image/png'
            elif 'jpeg' in content_type.lower() or 'jpg' in content_type.lower():
                data_url_format = 'image/jpeg'
            else:
                data_url_format = 'image/jpeg'
            
            logger.info(f"✅ Şəkil yükləndi: {len(image_data)} bytes, format: {data_url_format}")
        except Exception as e:
            logger.error(f"❌ Şəkil yüklənə bilmədi: {str(e)}")
            return Response({
                "error": f"Şəkil yüklənə bilmədi: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Step 2: Analyze image with OpenAI Vision API
        logger.info("🤖 OpenAI Vision API ilə şəkil analiz edilir...")
        try:
            openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            
            analysis_prompt = f"""Bu reklam şəklini detallı analiz et və sosial media postu üçün məzmun yarat.

Şəkil haqqında:
- Şəkildə nə göstərilir?
- Məhsulun xüsusiyyətləri nələrdir?
- Rənglər, dizayn, kompozisiya necədir?
- Hədəf auditoriya kimdir?
- Hansı emosiyalar oyadılır?

Yalnız JSON formatında cavab ver (heç bir əlavə mətn yazma):
{{
    "title": "Post başlığı (50-80 simvol)",
    "description": "Post təsviri (150-250 simvol)",
    "content": "Tam post məzmunu (Hook + Body + CTA)",
    "hook": "Cəlbedici başlıq (50-80 simvol)",
    "body": "Faydalar və xüsusiyyətlər (150-250 simvol)",
    "cta": "Çağırış (40-60 simvol)",
    "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3", ...],
    "product_type": "Məhsul növü",
    "target_audience": "Hədəf auditoriya"
}}

Məzmun Azərbaycan dilində olmalıdır və Instagram/Facebook üçün uyğun olmalıdır."""
            
            vision_response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": analysis_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{data_url_format};base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1500,
                temperature=0.7
            )
            
            analysis_text = vision_response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if analysis_text.startswith('```json'):
                analysis_text = analysis_text[7:]
            if analysis_text.startswith('```'):
                analysis_text = analysis_text[3:]
            if analysis_text.endswith('```'):
                analysis_text = analysis_text[:-3]
            analysis_text = analysis_text.strip()
            
            # Parse JSON
            post_data = json.loads(analysis_text)
            logger.info(f"✅ Şəkil analiz edildi")
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parse xətası: {str(e)}")
            logger.error(f"   Response: {analysis_text[:500]}")
            return Response({
                "error": f"AI cavabı parse edilə bilmədi: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"❌ OpenAI Vision API xətası: {str(e)}", exc_info=True)
            return Response({
                "error": f"Şəkil analiz edilə bilmədi: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Step 3: Create post
        logger.info("📝 Post yaradılır...")
        try:
            from posts.models import Post
            
            # Extract data
            title = post_data.get('title') or post_data.get('hook', 'Yeni Reklam Postu')
            content = post_data.get('content', '')
            if not content:
                hook = post_data.get('hook', '')
                body = post_data.get('body', '')
                cta = post_data.get('cta', '')
                hashtags_str = ' '.join(post_data.get('hashtags', []))
                content = f"{hook}\n\n{body}\n\n{cta}\n\n{hashtags_str}".strip()
            
            hashtags = post_data.get('hashtags', [])
            description = post_data.get('description') or post_data.get('body', '')
            
            post = Post.objects.create(
                user=user,
                title=title,
                content=content,
                hashtags=hashtags,
                description=description[:200] if description else '',
                image_url=image_url,
                ai_generated=True,
                ai_prompt=f"Image analysis for: {product_name or 'Generated ad image'}",
                status='pending_approval',
                requires_approval=True
            )
            
            logger.info(f"✅ Post yaradıldı: {post.id}")
            
            # Step 4: Apply automatic branding if enabled
            try:
                from accounts.models import CompanyProfile
                from posts.branding import ImageBrandingService
                from django.core.files.base import ContentFile
                import os
                
                company_profile = CompanyProfile.objects.filter(user=user).first()
                
                if company_profile and company_profile.branding_enabled and company_profile.logo:
                    logger.info(f"🎨 Avtomatik brendləşmə tətbiq olunur...")
                    
                    # Download image from URL
                    try:
                        img_response = requests.get(image_url, timeout=30)
                        img_response.raise_for_status()
                        image_data = img_response.content
                        
                        # Save to post.custom_image
                        filename = f"post_{post.id}_{uuid.uuid4()}.png"
                        post.custom_image.save(filename, ContentFile(image_data), save=True)
                        
                        # Check if logo file exists
                        if os.path.exists(company_profile.logo.path):
                            branding_service = ImageBrandingService(company_profile)
                            image_path = post.custom_image.path
                            logger.info(f"   Brendləşmə tətbiq olunur: {image_path}")
                            
                            branded_image = branding_service.apply_branding(image_path)
                            output = branding_service.save_branded_image(branded_image, format='PNG')
                            
                            # Replace with branded version
                            branded_filename = f"branded_{post.id}.png"
                            post.custom_image.save(branded_filename, ContentFile(output.read()), save=True)
                            post.save()
                            
                            logger.info(f"✅ Brendləşmə uğurla tətbiq olundu")
                        else:
                            logger.warning(f"⚠️ Logo faylı tapılmadı: {company_profile.logo.path}")
                    except Exception as branding_error:
                        logger.error(f"❌ Brendləşmə xətası: {str(branding_error)}", exc_info=True)
                        # Continue without branding - post is still created
                else:
                    if not company_profile:
                        logger.info("ℹ️ Company profile yoxdur, brendləşmə tətbiq edilmədi")
                    elif not company_profile.branding_enabled:
                        logger.info("ℹ️ Brendləşmə deaktivdir")
                    elif not company_profile.logo:
                        logger.info("ℹ️ Logo yoxdur, brendləşmə tətbiq edilmədi")
            except Exception as e:
                logger.error(f"❌ Brendləşmə yoxlanışı xətası: {str(e)}", exc_info=True)
                # Continue without branding - post is still created
            
            # Return response
            return Response({
                "success": True,
                "message": "Post uğurla yaradıldı",
                "post": {
                    "id": str(post.id),
                    "title": post.title,
                    "content": post.content,
                    "description": post.description,
                    "hashtags": post.hashtags,
                    "image_url": post.image_url,
                    "status": post.status
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"❌ Post yaradıla bilmədi: {str(e)}", exc_info=True)
            return Response({
                "error": f"Post yaradıla bilmədi: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"❌ Xəta: {str(e)}", exc_info=True)
        return Response({
            "error": f"Xəta baş verdi: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    
    # TODO: Aktivləşdirildikdə aşağıdakı kodu uncomment edin
    """
    try:
        from .url_product_scraper import (
            scrape_product_page,
            extract_product_info_with_ai,
            download_image_from_url,
            validate_product_data
        )
        
        logger.info("=" * 80)
        logger.info("🔗 YENİ FUNKSİYA: URL-dən Məhsul Postu Yaradılır")
        logger.info("=" * 80)
        
        # Get parameters
        product_url = request.data.get('product_url')
        num_images = int(request.data.get('num_images', 1))  # Default 1
        
        if not product_url:
            return Response({
                "error": "Məhsul URL-i tələb olunur (product_url)"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate URL format
        if not product_url.startswith('http'):
            return Response({
                "error": "Yanlış URL formatı. URL http:// və ya https:// ilə başlamalıdır"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info(f"📌 Məhsul URL: {product_url}")
        logger.info(f"📌 Yaradılacaq post sayı: {num_images}")
        
        # Step 1: Try Apify scraping first
        logger.info(f"🛒 Step 1: Apify ilə məhsul məlumatları çəkilir...")
        
        extracted_data = None
        apify_data = scrape_product_with_apify(product_url)
        
        if apify_data:
            logger.info(f"✅ Apify-dən məhsul məlumatları alındı")
            logger.info(f"   Ad: {apify_data.get('name', 'N/A')}")
            logger.info(f"   Brend: {apify_data.get('brand', 'N/A')}")
            logger.info(f"   Qiymət: {apify_data.get('price', 'N/A')} {apify_data.get('currency', '')}")
            
            # Convert Apify data format to expected format
            extracted_data = {
                'product_name': apify_data.get('name', ''),
                'product_type': apify_data.get('brand', ''),
                'price': f"{apify_data.get('price', '')} {apify_data.get('currency', '')}".strip(),
                'main_image_url': apify_data.get('image', ''),
                'description': apify_data.get('description', ''),
                'url': apify_data.get('url', product_url),
                'brand': apify_data.get('brand', ''),
                'availability': apify_data.get('availability', ''),
                'raw_apify_data': apify_data  # Keep raw data for reference
            }
            
            logger.info(f"✅ Məhsul məlumatları hazırlandı (Apify-dən)")
        else:
            logger.warning(f"⚠️ Apify scraping uğursuz, köhnə metodu istifadə edirik...")
            
            # Step 2: Fallback to old method - Web Scraping
            logger.info(f"🌐 Step 2: Sayt məzmunu çəkilir...")
        
        try:
            scrape_result = scrape_product_page(product_url)
            html_content = scrape_result['html']
            final_url = scrape_result['final_url']
            
            logger.info(f"✅ Sayt məzmunu çəkildi ({len(html_content)} bytes)")
            if final_url != product_url:
                logger.info(f"   Redirect: {final_url}")
            
        except Exception as scraping_error:
            logger.error(f"❌ Web scraping xətası: {str(scraping_error)}")
            return Response({
                "error": f"Sayt açıla bilmədi: {str(scraping_error)}"
            }, status=status.HTTP_400_BAD_REQUEST)
        
            # Step 3: AI Analysis (fallback)
            logger.info(f"🤖 Step 3: AI ilə məhsul məlumatları çıxarılır...")
        
        # TODO: Post yaratma kodu - sonra aktivləşdiriləcək
        # COMMENTED OUT - Hələlik post yaratmırıq, yalnız məlumatları qaytarırıq
        # Step 3 və sonrası: Post yaratma workflow-u (sonra aktivləşdiriləcək)
        
    except Exception as e:
        logger.error(f"❌ URL-dən post yaratma xətası: {str(e)}", exc_info=True)
        return Response({
            "error": f"URL-dən post yaradıla bilmədi: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    """


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def analyze_instagram_profile(request):
    """
    Instagram profil analizi - Metrics → Rules → GPT architecture
    
    Architecture:
    1. METRICS: Compute all metrics from raw data (deterministic)
    2. RULES: Apply business rules to trigger recommendations (deterministic)
    3. GPT: Generate bio suggestions and explain triggered rules (creative, but constrained)
    
    Input:
    {
        "instagram_username": "@username",
        "current_bio": "Hazırkı bio mətn",
        "followers_count": 1500,
        "following_count": 800,
        "posts_count": 120,
        "posting_frequency": "3-4",
        "niche": "Fashion/Tech/Food/..."
    }
    
    Output:
    {
        "profile_info": {...metrics...},
        "bio_suggestions": [...],
        "hashtag_strategy": {...},  # Removed AI guessing
        "content_strategy": {...},  # From rules
        "posting_schedule": {...},  # From rules (fixed times)
        "engagement_tips": [...],
        "growth_strategy": {...},
        "triggered_rules": [...]  # New: show which rules triggered
    }
    """
    try:
        from .metrics.instagram import InstagramMetrics
        from .rules.instagram import InstagramRuleEngine
        
        logger.info("=" * 80)
        logger.info("📱 Instagram Profil Analizi Başlayır (Metrics → Rules → GPT)")
        logger.info("=" * 80)
        
        # Parse input data
        logger.info(f"📥 Request data: {json.dumps(request.data, indent=2)}")
        
        username = request.data.get('instagram_username', '').strip().lstrip('@')
        current_bio = request.data.get('current_bio', '').strip()
        followers = request.data.get('followers_count', 0)
        following = request.data.get('following_count', 0)
        posts = request.data.get('posts_count', 0)
        posting_frequency = request.data.get('posting_frequency', '').strip()
        niche = request.data.get('niche', '').strip()
        
        # Parse to int safely
        try:
            followers = int(followers) if followers else 0
            following = int(following) if following else 0
            posts = int(posts) if posts else 0
        except (ValueError, TypeError):
            pass
        
        logger.info(f"📊 Parsed values - followers: {followers}, following: {following}, posts: {posts}")
        
        if not username:
            return Response({
                "error": "Instagram username tələb olunur"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # STEP 0: SCRAPE POSTS FOR ANALYSIS (optional)
        post_analysis = None
        try:
            logger.info("📸 Step 0: Scraping posts for timestamp analysis...")
            profile_url = f"https://www.instagram.com/{username}/"
            scraped_data = scrape_instagram_with_apify(profile_url)
            
            if scraped_data and scraped_data.get('posts'):
                posts_data = scraped_data.get('posts', [])
                logger.info(f"✅ {len(posts_data)} post scraped for analysis")
                post_analysis = InstagramMetrics.analyze_post_timestamps(posts_data)
                logger.info(f"📊 Post analysis: {post_analysis.get('optimal_posting_times', [])}")
            else:
                logger.warning("⚠️ Post scraping failed or no posts found")
        except Exception as e:
            logger.warning(f"⚠️ Post scraping error: {str(e)}")
        
        # STEP 1: COMPUTE METRICS (deterministic)
        logger.info("📊 Step 1: Computing metrics...")
        metrics = InstagramMetrics.compute_all_metrics(
            username=username,
            followers=followers,
            following=following,
            posts=posts,
            posting_frequency=posting_frequency,
            niche=niche,
            current_bio=current_bio
        )
        logger.info(f"✅ Metrics computed: engagement_rate={metrics['engagement_rate']}%, stage={metrics['account_stage_az']}")
        
        # STEP 2: APPLY RULES (deterministic)
        logger.info("⚙️ Step 2: Applying business rules...")
        rule_engine = InstagramRuleEngine(metrics)
        triggered_rules = rule_engine.evaluate_all_rules()
        content_strategy = rule_engine.get_content_strategy()
        posting_schedule = rule_engine.get_posting_schedule()
        hashtag_strategy = rule_engine.get_hashtag_recommendations()
        
        logger.info(f"✅ Rules applied: {len(triggered_rules)} rules triggered")
        for rule in triggered_rules:
            logger.info(f"   - [{rule.severity}] {rule.rule_id}: {rule.message}")
        
        # STEP 3: GPT for bio suggestions and rule explanations (creative, but constrained)
        logger.info("🤖 Step 3: GPT for bio suggestions and explanations...")
        
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Prepare triggered rules summary for GPT
        rules_summary = "\n".join([
            f"- [{rule.severity.upper()}] {rule.category}: {rule.message} → {rule.recommendation}"
            for rule in triggered_rules
        ])
        
        # Analyze current bio for context
        bio_analysis = ""
        if current_bio:
            bio_analysis = f"""
HAZIRKI BIO ANALİZİ:
"{current_bio}"

Bio analizi:
- Uzunluq: {len(current_bio)} simvol
- Emoji var: {'Bəli' if any(ord(c) > 127000 for c in current_bio) else 'Xeyr'}
- CTA var: {'Bəli' if any(word in current_bio.lower() for word in ['link', 'linkin', 'dm', 'yaz', 'əlaqə', 'contact']) else 'Xeyr'}
- Niche məlumatı: {'Var' if niche and niche.lower() in current_bio.lower() else 'Yoxdur'}

Bio-nun güclü tərəfləri: {', '.join([f'"{part.strip()}"' for part in current_bio.split('|')[:2] if part.strip()]) if '|' in current_bio else 'Strukturlaşdırılmamış'}
"""
        else:
            bio_analysis = "Hazırkı bio boşdur - yeni bio yaradılmalıdır."

        gpt_prompt = f"""Instagram profil analizi - Bio təklifləri və qaydaların izahı (Azərbaycan dilində).

CRITICAL RULES FOR GPT:
- DO NOT hallucinate data, metrics, or numbers
- DO NOT create fake hashtags or guess hashtag competition levels
- DO NOT invent posting times - use only provided times
- ONLY explain and elaborate on provided rules and recommendations
- Bio-lar MUTLAQ profilə spesifik olmalıdır - generic bio-lar yaratma!

PROFIL METRİKLƏRİ (REAL DATA):
- Username: @{username}
- Followers: {followers:,}
- Following: {following:,}
- Posts: {posts}
- Engagement rate: {metrics['engagement_rate']}%
- Hesab mərhələsi: {metrics['account_stage_az']}
- Niche/Sahə: {niche if niche else 'Ümumi'}
{bio_analysis}

TRİGGERED RULES (REAL BUSINESS LOGIC):
{rules_summary if rules_summary else "Heç bir kritik problem tapılmadı"}

TASKS FOR GPT:
1. BIO TƏKLİFLƏRİ (5 variant) - ÇOX ƏHƏMİYYƏTLİDİR:
   - Hər bio MUTLAQ bu profili əks etdirməlidir:
     * Username (@{username}) və ya onun mənasını nəzərə al
     * Niche ({niche if niche else 'Ümumi'}) konkret şəkildə göstər
     * Hesab mərhələsi ({metrics['account_stage_az']}) - starter üçün daha friendly, established üçün daha professional
     * Hazırkı bio-nun güclü tərəflərini saxla və zəif tərəflərini düzəlt
   
   - Bio struktur:
     * 1-ci sətir: Value proposition (niche + unique selling point)
     * 2-ci sətir: Call-to-action və ya engagement elementi
     * 3-cü sətir: Link və ya contact info (əgər varsa)
   
   - Emoji strategiyası:
     * Niche-ə uyğun emojilər ({niche if niche else 'generic'} üçün)
     * Çox emoji yazma (2-4 emoji kifayətdir)
     * Emoji-lər mətnin mənasını gücləndirsin
   
   - Call-to-action:
     * Hesab mərhələsinə görə: starter üçün "Follow for more", established üçün "DM for collab"
     * Niche-spesifik CTA: {niche if niche else 'generic niche'} üçün uyğun CTA
   
   - Uzunluq: 150 simvoldan az (optimal: 100-130 simvol)
   
   - Hər bio variantı FƏRQLİ olmalıdır:
     * Variant 1: Professional/formal ton
     * Variant 2: Friendly/casual ton
     * Variant 3: Creative/artistic ton
     * Variant 4: Minimalist/clean ton
     * Variant 5: Bold/attention-grabbing ton
   
   - Explanation hər bio üçün:
     * Niyə bu bio bu profil üçün uyğundur
     * Hansı elementlər profilə spesifikdir
     * Niyə bu ton və struktur seçilib

2. ENGAGEMENT TİPLƏRİ (10 konkret tip):
   - Triggered rules-ə əsaslanaraq konkret addımlar
   - Praktik, tətbiq oluna bilən məsləhətlər
   - Niche-spesifik tövsiyələr

3. GROWTH STRATEGİYASI:
   - 30 günlük plan (həftəlik breakdown)
   - Real hədəflər (metrics-ə əsasən)
   - Ölçülə bilən nəticələr

4. ÜMUMİ QİYMƏTLƏNDİRMƏ:
   - Güclü tərəflər (metrics-dən)
   - Zəif tərəflər (triggered rules-dən)
   - İmkanlar
   - Prioritet addımlar

JSON formatda qaytarın:
{{
    "bio_suggestions": [
        {{
            "bio": "Tam bio mətn (100-130 simvol, profilə spesifik)",
            "explanation": "DETALLI izah: Niyə bu bio bu profil (@{username}, {niche if niche else 'niche'}, {metrics['account_stage_az']}) üçün uyğundur. Hansı elementlər profilə spesifikdir. Niyə bu ton seçilib. Hansı CTA və emoji strategiyası istifadə olunub."
        }},
        {{
            "bio": "Fərqli ton və strukturda bio (yuxarıdakından fərqli)",
            "explanation": "DETALLI izah: Bu variantın fərqi nədir, niyə bu ton seçilib, hansı elementlər profilə spesifikdir."
        }},
        {{
            "bio": "Üçüncü variant (fərqli yanaşma)",
            "explanation": "DETALLI izah..."
            }},
            {{
            "bio": "Dördüncü variant (fərqli yanaşma)",
            "explanation": "DETALLI izah..."
            }},
            {{
            "bio": "Beşinci variant (fərqli yanaşma)",
            "explanation": "DETALLI izah..."
        }}
    ],
    "engagement_tips": [
        "Tip 1: konkret addım",
        "Tip 2: konkret addım",
        ...
    ],
    "growth_strategy": {{
        "30_day_plan": {{
            "week_1": "...",
            "week_2": "...",
            "week_3": "...",
            "week_4": "..."
        }},
        "realistic_goals": {{
            "followers_growth": "+X%",
            "engagement_target": "Y%"
        }},
        "metrics_to_track": ["metric1", "metric2", ...]
    }},
    "overall_assessment": {{
        "strengths": ["güclü tərəf 1", ...],
        "weaknesses": ["zəif tərəf 1", ...],
        "opportunities": ["fürsət 1", ...],
        "priority_actions": ["öncelikli addım 1", ...]
    }}
}}

Bütün mətnlər Azərbaycan dilində olmalıdır.
REMEMBER: DO NOT hallucinate data. Use only provided metrics and rules."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"""Siz peşəkar Social Media Marketing (SMM) məsləhətçisisiniz və Instagram bio copywriter-siniz.

SİZİN VƏZİFƏNİZ:
1. Bio yaradarkən MUTLAQ profilə spesifik olmalısınız - generic bio-lar yaratmayın!
2. Username (@{username}), niche ({niche if niche else 'Ümumi'}), və hesab mərhələsi ({metrics['account_stage_az']}) əsasında personal bio-lar yaradın
3. Hazırkı bio-nu analiz edin və onun güclü tərəflərini saxlayın, zəif tərəflərini düzəldin
4. Hər bio variantı fərqli ton və strukturda olmalıdır
5. HEÇ VAXT məlumat uydurmayın - yalnız verilmiş faktlar əsasında işləyin
6. Bütün cavablar Azərbaycan dilində olmalıdır

BIO YARADMA PRİNSİPLƏRİ:
- Profilə spesifik ol (username, niche, stage)
- Unique value proposition göstər
- Call-to-action əlavə et
- Emoji-ləri məqsədyönlü istifadə et
- 100-130 simvol optimal uzunluqdur"""
                },
                {
                    "role": "user",
                    "content": gpt_prompt
                }
            ],
            temperature=0.8,  # Higher creativity for personalized bios
            max_tokens=2500  # More tokens for detailed explanations
        )
        
        gpt_text = response.choices[0].message.content.strip()
        
        # Clean up JSON
        if gpt_text.startswith('```'):
            gpt_text = re.sub(r'^```json?\s*', '', gpt_text)
            gpt_text = re.sub(r'\s*```$', '', gpt_text)
        
        gpt_data = json.loads(gpt_text)
        
        logger.info(f"✅ GPT response parsed successfully")
        logger.info(f"   Bio suggestions: {len(gpt_data.get('bio_suggestions', []))}")
        logger.info(f"   Engagement tips: {len(gpt_data.get('engagement_tips', []))}")
        
        # STEP 4: ASSEMBLE FINAL RESPONSE
        logger.info("📦 Step 4: Assembling final response...")
        
        return Response({
            "success": True,
            "profile_info": {
                "username": username,
                "followers": followers,
                "following": following,
                "posts": posts,
                "engagement_rate": metrics['engagement_rate'],
                "posting_frequency": metrics['posting_frequency_text'],
                "niche": niche,
                "account_stage": metrics['account_stage_az'],
                "following_ratio": metrics['following_ratio']
            },
            "bio_suggestions": gpt_data.get('bio_suggestions', []),
            "hashtag_strategy": hashtag_strategy,
            "content_strategy": content_strategy,
            "posting_schedule": posting_schedule,
            "post_analysis": post_analysis,  # Post timestamp analysis
            "engagement_tips": gpt_data.get('engagement_tips', []),
            "growth_strategy": gpt_data.get('growth_strategy', {}),
            "overall_assessment": gpt_data.get('overall_assessment', {}),
            "triggered_rules": [
                {
                    "rule_id": rule.rule_id,
                    "severity": rule.severity,
                    "category": rule.category,
                    "message": rule.message,
                    "recommendation": rule.recommendation
                }
                for rule in triggered_rules
            ],
            "generated_at": datetime.now().isoformat(),
            "architecture_version": "metrics_rules_gpt_v1"
        }, status=status.HTTP_200_OK)
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON parse xətası: {str(e)}")
        logger.error(f"GPT cavabı: {gpt_text[:500] if 'gpt_text' in locals() else 'N/A'}")
        return Response({
            "error": "GPT cavabı parse edilə bilmədi"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        logger.error(f"❌ Instagram analiz xətası: {str(e)}", exc_info=True)
        return Response({
            "error": f"Analiz xətası: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def translate_text(request):
    """
    Translate text between languages using OpenAI
    
    Input:
    {
        "text": "Text to translate",
        "target_language": "az" | "en" | "ru" | "tr",
        "source_language": "auto" | "az" | "en" | "ru" | "tr"
    }
    
    Output:
    {
        "original_text": "...",
        "translated_text": "...",
        "source_language": "...",
        "target_language": "..."
    }
    """
    try:
        text = request.data.get('text', '').strip()
        target_language = request.data.get('target_language', 'az').strip()
        source_language = request.data.get('source_language', 'auto').strip()
        
        if not text:
            return Response({
                "error": "Text tələb olunur"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Language mapping
        language_names = {
            'az': 'Azərbaycan',
            'en': 'English',
            'ru': 'Русский',
            'tr': 'Türkçe'
        }
        
        target_lang_name = language_names.get(target_language, 'Azərbaycan')
        source_lang_name = language_names.get(source_language, 'Auto-detect') if source_language != 'auto' else 'Auto-detect'
        
        logger.info(f"🌐 Translation request: {source_lang_name} → {target_lang_name}")
        
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        translate_prompt = f"""Translate the following text to {target_lang_name}.

Source language: {source_lang_name}
Target language: {target_lang_name}

Text to translate:
{text}

Instructions:
- Translate accurately preserving the meaning
- Keep the same tone and style
- Preserve any emojis or special characters
- If the text is already in {target_lang_name}, return it as is
- Return ONLY the translated text, no explanations

Translated text:"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"You are a professional translator. Translate text accurately between {source_lang_name} and {target_lang_name}. Preserve meaning, tone, and style."
                },
                {
                    "role": "user",
                    "content": translate_prompt
                }
            ],
            temperature=0.3,  # Lower temperature for accurate translation
            max_tokens=1000
        )
        
        translated_text = response.choices[0].message.content.strip()
        
        # Clean up if there are any extra explanations
        if '\n' in translated_text:
            translated_text = translated_text.split('\n')[0]
        
        logger.info(f"✅ Translation completed: {len(text)} → {len(translated_text)} chars")
        
        return Response({
            "success": True,
            "original_text": text,
            "translated_text": translated_text,
            "source_language": source_language,
            "target_language": target_language,
            "source_language_name": source_lang_name,
            "target_language_name": target_lang_name
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"❌ Translation xətası: {str(e)}", exc_info=True)
        return Response({
            "error": f"Translation xətası: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def analyze_facebook_profile(request):
    """
    Facebook Page analizi və SMM tövsiyələri
    
    Input:
    {
        "page_name": "Page Name",
        "current_about": "Hazırkı about mətn",
        "followers_count": 5000,
        "likes_count": 4800,
        "posts_count": 200,
        "posting_frequency": "3-4",
        "niche": "Business/Education/..."
    }
    """
    try:
        logger.info("=" * 80)
        logger.info("📘 Facebook Page Analizi Başlayır")
        logger.info("=" * 80)
        
        # Get input data
        page_name = request.data.get('page_name', '').strip()
        current_about = request.data.get('current_about', '').strip()
        followers = int(request.data.get('followers_count', 0))
        likes = int(request.data.get('likes_count', 0))
        posts = int(request.data.get('posts_count', 0))
        posting_frequency = request.data.get('posting_frequency', '').strip()
        niche = request.data.get('niche', '').strip()
        
        if not page_name:
            return Response({
                "error": "Facebook Page adı tələb olunur"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Map posting frequency
        frequency_map = {
            '1-2': 'Həftədə 1-2 dəfə',
            '3-4': 'Həftədə 3-4 dəfə',
            '5-7': 'Həftədə 5-7 dəfə',
            'daily': 'Gündə 1 dəfə',
            '2plus': 'Gündə 2+ dəfə'
        }
        posting_frequency_text = frequency_map.get(posting_frequency, posting_frequency or 'Təyin olunmayıb')
        
        logger.info(f"📊 Page: {page_name}")
        logger.info(f"   Followers: {followers:,}")
        logger.info(f"   Posts: {posts}")
        logger.info(f"   Paylaşım sıxılığı: {posting_frequency_text}")
        logger.info(f"   Niche: {niche}")
        
        # Calculate metrics
        engagement_ratio = likes / followers if followers > 0 else 0
        
        # Determine page stage
        if followers < 1000:
            page_stage = "starter"
            page_stage_az = "Başlanğıc"
        elif followers < 10000:
            page_stage = "growing"
            page_stage_az = "İnkişaf mərhələsi"
        elif followers < 100000:
            page_stage = "established"
            page_stage_az = "Möhkəm"
        else:
            page_stage = "popular"
            page_stage_az = "Populyar"
        
        logger.info(f"🎯 Page mərhələsi: {page_stage_az}")
        
        # Call OpenAI
        logger.info(f"🤖 OpenAI analizi başlayır...")
        
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        analysis_prompt = f"""Facebook Page analizi və SMM tövsiyələri (Azərbaycan dilində).

PAGE MƏLUMATLARI:
- Page adı: {page_name}
- Hazırkı About: "{current_about if current_about else 'Boş'}"
- Followers: {followers:,}
- Likes: {likes:,}
- Posts: {posts}
- Paylaşım sıxılığı: {posting_frequency_text}
- Niche/Sahə: {niche if niche else 'Ümumi'}
- Page mərhələsi: {page_stage_az}
- Engagement ratio: {engagement_ratio:.2f}

FACEBOOK XÜSUSİYYƏTLƏRİ:
- Facebook algoritmi engagement və comments prioritizə edir
- Video content daha çox reach alır
- Community engagement çox vacibdir
- Facebook Groups ilə inteqrasiya tövsiyə olunur
- Live videos yüksək engagement verir

TƏHLİL VƏ TÖVSİYƏLƏR HAZIRLYIN:

1. ABOUT/PAGE DESCRIPTION TƏKLİFLƏRİ (5 variant):
   - Aydın, informasiya verici
   - SEO-friendly keywords
   - Call-to-action daxil etsin
   - Contact information və linklər

2. CONTENT STRATEGİYASI:
   - Content növləri (faiz payı ilə): Video, Link posts, Photo, Text, Live
   - Post tezliyi tövsiyəsi
   - Video content strategiyası
   - Facebook Groups strategiyası
   - Content pillars (3-5 əsas mövzu)

3. POSTİNG SCHEDULE (REAL VAXT FORMATINDA):
   - Ən yaxşı post saatları (həftə günləri + həftə sonu) - REAL VAXT (məsələn: "18:00", "13:00")
   - Hər zaman slot üçün effektivlik səbəbi
   - Top 3 ən effektiv posting saatları (real vaxt, effektivlik skoru, detallı səbəb)

4. ENGAGEMENT ARTIRILMASI:
   - Facebook-specific engagement tips (10 tip)
   - Comments strategiyası
   - Shares strategiyası
   - Facebook Groups və Communities
   - Live video strategiyası

5. GROWTH STRATEGİYASI:
   - 30 günlük plan
   - Realistic growth hədəfləri
   - Facebook Ads inteqrasiyası
   - Metrics track etmək üçün

JSON formatda qaytarın (Instagram strukturuna oxşar, amma Facebook üçün uyğunlaşdırılmış):
{{
    "about_suggestions": [
        {{
            "about": "...",
            "explanation": "Niyə bu about işləyəcək"
        }}
    ],
    "content_strategy": {{
        "content_mix": {{
            "video": 30,
            "link_posts": 20,
            "photo": 25,
            "text": 15,
            "live": 10
        }},
        "post_frequency": "həftədə X post",
        "video_frequency": "həftədə X video",
        "live_frequency": "ayda X live",
        "content_pillars": ["Mövzu 1", "Mövzu 2", ...]
    }},
    "posting_schedule": {{
        "weekdays": {{
            "morning": {{
                "time_range": "08:00-10:00",
                "best_time": "09:00",
                "effectiveness": "Detallı izah"
            }},
            "afternoon": {{
                "time_range": "12:00-14:00",
                "best_time": "13:00",
                "effectiveness": "Detallı izah"
            }},
            "evening": {{
                "time_range": "18:00-21:00",
                "best_time": "19:00",
                "effectiveness": "Detallı izah"
            }},
            "best_time": "19:00",
            "best_time_reason": "Detallı səbəb"
        }},
        "weekend": {{
            "best_time": "11:00",
            "alternative_times": ["11:00", "20:00"],
            "best_time_reason": "Detallı səbəb"
        }},
        "top_3_best_times": [
            {{
                "time": "19:00",
                "day_type": "Həftə içi",
                "effectiveness_score": "95%",
                "reason": "Detallı səbəb"
            }},
            ...
        ]
    }},
    "engagement_tips": ["Tip 1", "Tip 2", ...],
    "growth_strategy": {{
        "30_day_plan": {{
            "week_1": "...",
            "week_2": "...",
            "week_3": "...",
            "week_4": "..."
        }},
        "realistic_goals": {{
            "followers_growth": "+X%",
            "engagement_target": "Y%"
        }},
        "metrics_to_track": ["metric1", "metric2", ...]
    }},
    "overall_assessment": {{
        "strengths": ["güclü tərəf 1", ...],
        "weaknesses": ["zəif tərəf 1", ...],
        "opportunities": ["fürsət 1", ...],
        "priority_actions": ["öncelikli addım 1", ...]
    }}
}}

Bütün mətnlər Azərbaycan dilində olmalıdır."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Siz peşəkar Social Media Marketing (SMM) məsləhətçisisiniz. Facebook Page-ləri analiz edib konkret, tətbiq oluna bilən tövsiyələr verirsiniz. Bütün cavablar Azərbaycan dilində olmalıdır."
                },
                {
                    "role": "user",
                    "content": analysis_prompt
                }
            ],
            temperature=0.7,
            max_tokens=3000
        )
        
        analysis_text = response.choices[0].message.content.strip()
        
        # Clean up JSON
        if analysis_text.startswith('```'):
            analysis_text = re.sub(r'^```json?\s*', '', analysis_text)
            analysis_text = re.sub(r'\s*```$', '', analysis_text)
        
        analysis_data = json.loads(analysis_text)
        
        logger.info(f"✅ Analiz tamamlandı")
        
        # Calculate estimated engagement
        estimated_engagement = 0
        if posts > 0 and followers > 0:
            base_engagement = {
                "starter": 4.0,
                "growing": 3.5,
                "established": 2.5,
                "popular": 2.0
            }.get(page_stage, 3.0)
            
            frequency_multiplier = {
                '1-2': 1.2,
                '3-4': 1.0,
                '5-7': 0.9,
                'daily': 0.8,
                '2plus': 0.7
            }.get(posting_frequency, 1.0)
            
            estimated_engagement = round(base_engagement * frequency_multiplier, 1)
        
        return Response({
            "success": True,
            "profile_info": {
                "page_name": page_name,
                "followers": followers,
                "likes": likes,
                "posts": posts,
                "engagement_rate": estimated_engagement,
                "posting_frequency": posting_frequency_text,
                "niche": niche,
                "page_stage": page_stage_az,
                "engagement_ratio": round(engagement_ratio, 2)
            },
            "analysis": analysis_data,
            "generated_at": datetime.now().isoformat()
        }, status=status.HTTP_200_OK)
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON parse xətası: {str(e)}")
        return Response({
            "error": "AI cavabı parse edilə bilmədi"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        logger.error(f"❌ Facebook analiz xətası: {str(e)}", exc_info=True)
        return Response({
            "error": f"Analiz zamanı xəta baş verdi: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def analyze_linkedin_profile(request):
    """
    LinkedIn Company Page və ya Personal Profile analizi
    
    Input:
    {
        "profile_name": "Company/Personal Name",
        "current_headline": "Hazırkı headline",
        "followers_count": 3000,
        "connections_count": 1500,
        "posts_count": 80,
        "posting_frequency": "3-4",
        "niche": "B2B/Technology/..."
    }
    """
    try:
        logger.info("=" * 80)
        logger.info("💼 LinkedIn Profil Analizi Başlayır")
        logger.info("=" * 80)
        
        # Get input data
        profile_name = request.data.get('profile_name', '').strip()
        current_headline = request.data.get('current_headline', '').strip()
        followers = int(request.data.get('followers_count', 0))
        connections = int(request.data.get('connections_count', 0))
        posts = int(request.data.get('posts_count', 0))
        posting_frequency = request.data.get('posting_frequency', '').strip()
        niche = request.data.get('niche', '').strip()
        
        if not profile_name:
            return Response({
                "error": "LinkedIn profil adı tələb olunur"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Map posting frequency
        frequency_map = {
            '1-2': 'Həftədə 1-2 dəfə',
            '3-4': 'Həftədə 3-4 dəfə',
            '5-7': 'Həftədə 5-7 dəfə',
            'daily': 'Gündə 1 dəfə',
            '2plus': 'Gündə 2+ dəfə'
        }
        posting_frequency_text = frequency_map.get(posting_frequency, posting_frequency or 'Təyin olunmayıb')
        
        logger.info(f"📊 Profil: {profile_name}")
        logger.info(f"   Followers: {followers:,}")
        logger.info(f"   Posts: {posts}")
        logger.info(f"   Paylaşım sıxılığı: {posting_frequency_text}")
        logger.info(f"   Niche: {niche}")
        
        # Calculate metrics
        connection_ratio = connections / followers if followers > 0 else 0
        
        # Determine profile stage
        if followers < 500:
            profile_stage = "starter"
            profile_stage_az = "Başlanğıc"
        elif followers < 5000:
            profile_stage = "growing"
            profile_stage_az = "İnkişaf mərhələsi"
        elif followers < 50000:
            profile_stage = "established"
            profile_stage_az = "Möhkəm"
        else:
            profile_stage = "influencer"
            profile_stage_az = "İnfluenser"
        
        logger.info(f"🎯 Profil mərhələsi: {profile_stage_az}")
        
        # Call OpenAI
        logger.info(f"🤖 OpenAI analizi başlayır...")
        
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        analysis_prompt = f"""LinkedIn profil analizi və SMM tövsiyələri (Azərbaycan dilində).

PROFIL MƏLUMATLARI:
- Profil adı: {profile_name}
- Hazırkı Headline: "{current_headline if current_headline else 'Boş'}"
- Followers: {followers:,}
- Connections: {connections:,}
- Posts: {posts}
- Paylaşım sıxılığı: {posting_frequency_text}
- Niche/Sahə: {niche if niche else 'Ümumi'}
- Profil mərhələsi: {profile_stage_az}
- Connection ratio: {connection_ratio:.2f}

LINKEDIN XÜSUSİYYƏTLƏRİ:
- LinkedIn B2B və professional network platformasıdır
- Long-form content daha yaxşı işləyir
- Industry insights və thought leadership prioritizə olunur
- Comments və discussions çox vacibdir
- LinkedIn Articles və native video content
- Professional tone və value-driven content

TƏHLİL VƏ TÖVSİYƏLƏR HAZIRLYIN:

1. HEADLINE TƏKLİFLƏRİ (5 variant):
   - Professional, keyword-rich
   - Value proposition göstərsin
   - Industry və expertise vurğulayın
   - SEO-friendly

2. CONTENT STRATEGİYASI:
   - Content növləri (faiz payı ilə): Articles, Native Posts, Video, Carousel, Document
   - Post tezliyi tövsiyəsi
   - Long-form content strategiyası
   - Industry insights strategiyası
   - Content pillars (3-5 əsas mövzu)

3. POSTİNG SCHEDULE (REAL VAXT FORMATINDA):
   - Ən yaxşı post saatları (həftə günləri) - REAL VAXT (məsələn: "08:00", "12:00")
   - LinkedIn-də həftə sonu az aktivlik var
   - Top 3 ən effektiv posting saatları (real vaxt, effektivlik skoru, detallı səbəb)

4. ENGAGEMENT ARTIRILMASI:
   - LinkedIn-specific engagement tips (10 tip)
   - Comments və discussions strategiyası
   - LinkedIn Groups strategiyası
   - Thought leadership content
   - Networking strategiyası

5. GROWTH STRATEGİYASI:
   - 30 günlük plan
   - Realistic growth hədəfləri
   - LinkedIn Ads inteqrasiyası
   - Metrics track etmək üçün

JSON formatda qaytarın:
{{
    "headline_suggestions": [
        {{
            "headline": "...",
            "explanation": "Niyə bu headline işləyəcək"
        }}
    ],
    "content_strategy": {{
        "content_mix": {{
            "articles": 25,
            "native_posts": 35,
            "video": 20,
            "carousel": 15,
            "document": 5
        }},
        "post_frequency": "həftədə X post",
        "article_frequency": "ayda X article",
        "content_pillars": ["Mövzu 1", "Mövzu 2", ...]
    }},
    "posting_schedule": {{
        "weekdays": {{
            "morning": {{
                "time_range": "07:00-09:00",
                "best_time": "08:00",
                "effectiveness": "Detallı izah"
            }},
            "midday": {{
                "time_range": "12:00-13:00",
                "best_time": "12:30",
                "effectiveness": "Detallı izah"
            }},
            "afternoon": {{
                "time_range": "17:00-18:00",
                "best_time": "17:30",
                "effectiveness": "Detallı izah"
            }},
            "best_time": "08:00",
            "best_time_reason": "Detallı səbəb"
        }},
        "top_3_best_times": [
            {{
                "time": "08:00",
                "day_type": "Həftə içi",
                "effectiveness_score": "95%",
                "reason": "Detallı səbəb"
            }},
            ...
        ]
    }},
    "engagement_tips": ["Tip 1", "Tip 2", ...],
    "growth_strategy": {{
        "30_day_plan": {{
            "week_1": "...",
            "week_2": "...",
            "week_3": "...",
            "week_4": "..."
        }},
        "realistic_goals": {{
            "followers_growth": "+X%",
            "engagement_target": "Y%"
        }},
        "metrics_to_track": ["metric1", "metric2", ...]
    }},
    "overall_assessment": {{
        "strengths": ["güclü tərəf 1", ...],
        "weaknesses": ["zəif tərəf 1", ...],
        "opportunities": ["fürsət 1", ...],
        "priority_actions": ["öncelikli addım 1", ...]
    }}
}}

Bütün mətnlər Azərbaycan dilində olmalıdır."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Siz peşəkar Social Media Marketing (SMM) məsləhətçisisiniz. LinkedIn profillərini analiz edib konkret, tətbiq oluna bilən tövsiyələr verirsiniz. Bütün cavablar Azərbaycan dilində olmalıdır."
                },
                {
                    "role": "user",
                    "content": analysis_prompt
                }
            ],
            temperature=0.7,
            max_tokens=3000
        )
        
        analysis_text = response.choices[0].message.content.strip()
        
        # Clean up JSON
        if analysis_text.startswith('```'):
            analysis_text = re.sub(r'^```json?\s*', '', analysis_text)
            analysis_text = re.sub(r'\s*```$', '', analysis_text)
        
        analysis_data = json.loads(analysis_text)
        
        logger.info(f"✅ Analiz tamamlandı")
        
        # Calculate estimated engagement
        estimated_engagement = 0
        if posts > 0 and followers > 0:
            base_engagement = {
                "starter": 3.5,
                "growing": 3.0,
                "established": 2.5,
                "influencer": 2.0
            }.get(profile_stage, 2.8)
            
            frequency_multiplier = {
                '1-2': 1.3,
                '3-4': 1.1,
                '5-7': 1.0,
                'daily': 0.9,
                '2plus': 0.8
            }.get(posting_frequency, 1.0)
            
            estimated_engagement = round(base_engagement * frequency_multiplier, 1)
        
        return Response({
            "success": True,
            "profile_info": {
                "profile_name": profile_name,
                "followers": followers,
                "connections": connections,
                "posts": posts,
                "engagement_rate": estimated_engagement,
                "posting_frequency": posting_frequency_text,
                "niche": niche,
                "profile_stage": profile_stage_az,
                "connection_ratio": round(connection_ratio, 2)
            },
            "analysis": analysis_data,
            "generated_at": datetime.now().isoformat()
        }, status=status.HTTP_200_OK)
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON parse xətası: {str(e)}")
        return Response({
            "error": "AI cavabı parse edilə bilmədi"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        logger.error(f"❌ LinkedIn analiz xətası: {str(e)}", exc_info=True)
        return Response({
            "error": f"Analiz zamanı xəta baş verdi: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def scrape_instagram_with_apify(profile_url):
    """
    Scrape Instagram profile using Apify API
    Actor: apify/instagram-scraper (ID: shu8hvrXbJbY3Eb9W)
    """
    try:
        apify_api_key = getattr(settings, 'APIFY_API_KEY', None)
        
        logger.info(f"🔑 APIFY_API_KEY: {apify_api_key[:20] if apify_api_key else 'YOX'}...")
        
        if not apify_api_key or apify_api_key == '':
            logger.warning("⚠️ APIFY_API_KEY yoxdur və ya boşdur, manual input istifadə edin")
            return None
        
        logger.info(f"🔍 Apify ilə scraping başlayır: {profile_url}")
        
        # Apify Instagram Scraper actor ID
        # https://console.apify.com/actors/shu8hvrXbJbY3Eb9W
        apify_actor_id = "shu8hvrXbJbY3Eb9W"
        
        # Əvvəlcə actor-un input schema-sını alaq
        schema_url = f"https://api.apify.com/v2/acts/{apify_actor_id}/input-schema?token={apify_api_key}"
        schema_response = requests.get(schema_url, timeout=10)
        
        if schema_response.status_code == 200:
            schema = schema_response.json()
            logger.info(f"📋 Actor input schema alındı")
            logger.info(f"📋 Schema keys: {list(schema.get('properties', {}).keys())}")
        
        # Apify Instagram Scraper input formatı
        # Apify console-da işləyən format: directUrls istifadə edir
        # resultsType: "details" - profil detalları üçün
        run_input = {
            "directUrls": [profile_url],
            "resultsType": "details"
        }
        
        run_url = f"https://api.apify.com/v2/acts/{apify_actor_id}/runs?token={apify_api_key}"
        
        logger.info(f"📡 Apify API request: {run_url[:80]}...")
        logger.info(f"📦 Input data: {json.dumps(run_input, indent=2)}")
        
        response = requests.post(run_url, json=run_input, timeout=15)
        
        if response.status_code not in [200, 201]:
            error_text = response.text
            logger.error(f"❌ Apify API error ({response.status_code}): {error_text[:500]}")
            return None
        
        run_data = response.json()
        run_id = run_data['data']['id']
        initial_status = run_data['data'].get('status', 'UNKNOWN')
        
        logger.info(f"✅ Apify actor başladı: {run_id}, initial status: {initial_status}")
        
        max_wait = 120
        wait_interval = 5
        elapsed = 0
        run_status = initial_status
        
        while elapsed < max_wait:
            time.sleep(wait_interval)
            elapsed += wait_interval
            
            status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={apify_api_key}"
            status_response = requests.get(status_url, timeout=10)
            status_data = status_response.json()
            
            run_status = status_data['data']['status']
            
            logger.info(f"⏳ Scraping status: {run_status} ({elapsed}s)")
            
            if run_status == 'SUCCEEDED':
                logger.info(f"✅ Scraping tamamlandı ({elapsed}s)")
                break
            elif run_status in ['FAILED', 'ABORTED', 'TIMED-OUT']:
                error_message = status_data['data'].get('statusMessage', '')
                logger.error(f"❌ Scraping uğursuz: {run_status} - {error_message}")
                return None
            elif run_status in ['READY', 'RUNNING']:
                # Run davam edir
                continue
        
        if run_status != 'SUCCEEDED':
            logger.warning(f"⚠️ Scraping timeout və ya uğursuz ({max_wait}s), final status: {run_status}")
            return None
        
        # Dataset ID-ni run-dan alaq
        final_status = requests.get(f"https://api.apify.com/v2/actor-runs/{run_id}?token={apify_api_key}", timeout=10).json()
        dataset_id = final_status['data'].get('defaultDatasetId')
        
        if not dataset_id:
            dataset_id = f"runs/{run_id}/dataset"
        
        dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={apify_api_key}"
        dataset_response = requests.get(dataset_url, timeout=10)
        dataset_response.raise_for_status()
        
        items = dataset_response.json()
        
        logger.info(f"📦 Dataset-dən {len(items)} item alındı")
        
        if not items or len(items) == 0:
            logger.warning("⚠️ Heç bir məlumat tapılmadı")
            return None
        
        # İlk item-i log edək ki, struktur görək
        logger.info(f"📋 Dataset item struktur (ilk 500 simvol): {json.dumps(items[0], indent=2)[:500]}")
        
        profile_data = items[0]
        
        # Error yoxlayaq
        if "error" in profile_data:
            error_msg = profile_data.get("errorDescription", profile_data.get("error", "Unknown error"))
            logger.warning(f"⚠️ Apify error: {error_msg}")
            logger.warning(f"⚠️ Profil private ola bilər və ya scraping mümkün deyil. OG preview və ya manual input istifadə edin.")
            return None
        
        # Apify Instagram Scraper - real JSON strukturuna görə parse edirik
        # Field adları: username, fullName, biography, followersCount, followsCount, postsCount, etc.
        scraped_data = {
            "username": profile_data.get("username", ""),
            "full_name": profile_data.get("fullName", ""),
            "biography": profile_data.get("biography", ""),
            "followers": profile_data.get("followersCount", 0),
            "following": profile_data.get("followsCount", 0),
            "posts": profile_data.get("postsCount", 0),
            "profile_pic_url": profile_data.get("profilePicUrlHD") or profile_data.get("profilePicUrl", ""),
            "is_verified": profile_data.get("verified", False),
            "is_business": profile_data.get("isBusinessAccount", False),
            "category": profile_data.get("businessCategoryName", ""),
            "is_private": profile_data.get("private", False),
            "highlight_reel_count": profile_data.get("highlightReelCount", 0),
            "igtv_video_count": profile_data.get("igtvVideoCount", 0),
            "latest_posts": profile_data.get("latestPosts", [])
        }
        
        logger.info(f"📊 Scrape edildi: @{scraped_data['username']}, {scraped_data['followers']} followers, {scraped_data['posts']} posts")
        
        return scraped_data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Apify API xətası: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"❌ Scraping xətası: {str(e)}", exc_info=True)
        return None
        
        run_input = {
            "directUrls": [profile_url],
            "resultsType": "profiles",
            "resultsLimit": 1,
            "searchLimit": 1,
            "addParentData": False
        }
        
        run_url = f"https://api.apify.com/v2/acts/{apify_actor_id}/runs?token={apify_api_key}"
        
        response = requests.post(run_url, json=run_input, timeout=10)
        response.raise_for_status()
        
        run_data = response.json()
        run_id = run_data['data']['id']
        default_dataset_id = run_data['data']['defaultDatasetId']
        
        logger.info(f"✅ Apify actor başladı: {run_id}")
        
        max_wait = 60
        wait_interval = 3
        elapsed = 0
        
        while elapsed < max_wait:
            time.sleep(wait_interval)
            elapsed += wait_interval
            
            status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={apify_api_key}"
            status_response = requests.get(status_url, timeout=10)
            status_data = status_response.json()
            
            run_status = status_data['data']['status']
            
            if run_status == 'SUCCEEDED':
                logger.info(f"✅ Scraping tamamlandı ({elapsed}s)")
                break
            elif run_status in ['FAILED', 'ABORTED', 'TIMED-OUT']:
                logger.error(f"❌ Scraping uğursuz: {run_status}")
                return None
        else:
            logger.warning(f"⚠️ Scraping timeout ({max_wait}s)")
            return None
        
        dataset_url = f"https://api.apify.com/v2/datasets/{default_dataset_id}/items?token={apify_api_key}"
        dataset_response = requests.get(dataset_url, timeout=10)
        dataset_response.raise_for_status()
        
        items = dataset_response.json()
        
        if not items or len(items) == 0:
            logger.warning("⚠️ Heç bir məlumat tapılmadı")
            return None
        
        profile_data = items[0]
        
        scraped_data = {
            "username": profile_data.get("username", ""),
            "full_name": profile_data.get("fullName", ""),
            "biography": profile_data.get("biography", ""),
            "followers": profile_data.get("followersCount", 0),
            "following": profile_data.get("followsCount", 0),
            "posts": profile_data.get("postsCount", 0),
            "profile_pic_url": profile_data.get("profilePicUrlHD") or profile_data.get("profilePicUrl", ""),
            "is_verified": profile_data.get("verified", False),
            "is_business": profile_data.get("isBusinessAccount", False),
            "category": profile_data.get("businessCategoryName", ""),
            "is_private": profile_data.get("private", False),
            "highlight_reel_count": profile_data.get("highlightReelCount", 0),
            "igtv_video_count": profile_data.get("igtvVideoCount", 0),
            "latest_posts": profile_data.get("latestPosts", [])
        }
        
        logger.info(f"🖼️ Profil şəkli URL: {scraped_data['profile_pic_url'][:100] if scraped_data['profile_pic_url'] else 'YOX'}...")
        
        logger.info(f"📊 Scrape edildi: @{scraped_data['username']}, {scraped_data['followers']} followers")
        
        return scraped_data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Apify API xətası: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"❌ Scraping xətası: {str(e)}", exc_info=True)
        return None


def scrape_linkedin_with_apify(profile_url):
    """
    Scrape LinkedIn profile using Apify API
    NOTE: Personal profil scraping artıq istifadə edilmir, yalnız şirkət səhifələri dəstəklənir
    """
    logger.info(f"👤 LinkedIn personal profil scraping artıq istifadə edilmir, OG preview istifadə ediləcək: {profile_url}")
    return None


def scrape_linkedin_company_with_apify(company_url):
    """
    Scrape LinkedIn company page using Apify API
    Actor: icypeas_official/linkedin-company-scraper (ID: UKWDVj4p6sQlVquWc)
    """
    try:
        apify_api_key = getattr(settings, 'APIFY_API_KEY', None)
        
        if not apify_api_key or apify_api_key == '':
            logger.warning("⚠️ APIFY_API_KEY yoxdur və ya boşdur, LinkedIn şirkət scraping mümkün deyil")
            return None
        
        logger.info(f"🏢 LinkedIn şirkət səhifəsi Apify scraping başlayır: {company_url}")
        
        # Apify LinkedIn Company Scraper (specifically for company pages)
        # https://console.apify.com/actors/UKWDVj4p6sQlVquWc
        # Actor: icypeas_official/linkedin-company-scraper
        apify_actor_id = "UKWDVj4p6sQlVquWc"
        
        # Extract company name from URL
        # URL format: https://www.linkedin.com/company/company-name/
        company_name = company_url.rstrip('/').split('/')[-1]
        logger.info(f"📝 Extracted LinkedIn company name: {company_name}")
        logger.info(f"📝 Original URL: {company_url}")
        
        # Get actor input schema to understand the correct format
        schema_url = f"https://api.apify.com/v2/acts/{apify_actor_id}/input-schema?token={apify_api_key}"
        try:
            schema_response = requests.get(schema_url, timeout=10)
            if schema_response.status_code == 200:
                schema = schema_response.json()
                logger.info(f"📋 LinkedIn company actor input schema alındı")
                logger.info(f"📋 Schema properties: {list(schema.get('properties', {}).keys())}")
        except Exception as e:
            logger.warning(f"⚠️ Schema alına bilmədi: {str(e)}")
        
        # Apify input format - LinkedIn Company Scraper expects "companies" field with array of URLs
        # Based on the actor UI: "Companies to search (required)" field
        run_input = {
            "companies": [company_url]  # Array of company URLs
        }
        
        run_url = f"https://api.apify.com/v2/acts/{apify_actor_id}/runs?token={apify_api_key}"
        
        logger.info(f"📡 Apify LinkedIn Company API request: {run_url[:80]}...")
        logger.info(f"📦 Input data: {json.dumps(run_input, indent=2)}")
        
        response = requests.post(run_url, json=run_input, timeout=15)
        
        if response.status_code not in [200, 201]:
            error_text = response.text
            logger.error(f"❌ Apify LinkedIn Company API error ({response.status_code}): {error_text[:500]}")
            return None
        
        run_data = response.json()
        run_id = run_data['data']['id']
        initial_status = run_data['data'].get('status', 'UNKNOWN')
        
        logger.info(f"✅ Apify LinkedIn Company actor başladı: {run_id}, initial status: {initial_status}")
        
        max_wait = 120
        wait_interval = 5
        elapsed = 0
        run_status = initial_status
        
        while elapsed < max_wait:
            time.sleep(wait_interval)
            elapsed += wait_interval
            
            status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={apify_api_key}"
            status_response = requests.get(status_url, timeout=10)
            status_data = status_response.json()
            
            run_status = status_data['data']['status']
            
            logger.info(f"⏳ LinkedIn Company scraping status: {run_status} ({elapsed}s)")
            
            if run_status == 'SUCCEEDED':
                logger.info(f"✅ LinkedIn Company scraping tamamlandı ({elapsed}s)")
                break
            elif run_status in ['FAILED', 'ABORTED', 'TIMED-OUT']:
                error_message = status_data['data'].get('statusMessage', '')
                logger.error(f"❌ LinkedIn Company scraping uğursuz: {run_status} - {error_message}")
                return None
            elif run_status in ['READY', 'RUNNING']:
                continue
        
        if run_status != 'SUCCEEDED':
            logger.warning(f"⚠️ LinkedIn Company scraping timeout və ya uğursuz ({max_wait}s), final status: {run_status}")
            return None
        
        # Get dataset ID
        final_status = requests.get(f"https://api.apify.com/v2/actor-runs/{run_id}?token={apify_api_key}", timeout=10).json()
        default_dataset_id = final_status['data'].get('defaultDatasetId')
        
        if not default_dataset_id:
            default_dataset_id = f"runs/{run_id}/dataset"
        
        # Get company data from dataset
        dataset_url = f"https://api.apify.com/v2/datasets/{default_dataset_id}/items?token={apify_api_key}"
        dataset_response = requests.get(dataset_url, timeout=10)
        dataset_response.raise_for_status()
            
        items = dataset_response.json()
        
        if not items or len(items) == 0:
            logger.warning("⚠️ LinkedIn şirkət səhifəsindən heç bir məlumat tapılmadı")
            return None
        
        logger.info(f"✅ LinkedIn Company dataset-dən {len(items)} item alındı")
        
        # İlk item-i log edək - full structure
        logger.info(f"📋 LinkedIn Company dataset item struktur (FULL): {json.dumps(items[0], indent=2)}")
        logger.info(f"📋 LinkedIn Company dataset item keys: {list(items[0].keys())}")
        
        company_data = items[0]
        
        # Parse company data based on the actual structure returned by the actor
        # Check for nested structures (basic_info, company_info, etc.)
        basic_info = company_data.get("basic_info", {}) or company_data.get("company_info", {}) or {}
        
        # Company name - try multiple locations
        company_name = (company_data.get("name", "") or 
                       company_data.get("company_name", "") or 
                       company_data.get("fullname", "") or
                       basic_info.get("name", "") or
                       basic_info.get("company_name", "") or
                       basic_info.get("fullname", ""))
        
        # Headline/tagline
        headline = (company_data.get("headline", "") or 
                   company_data.get("tagline", "") or 
                   company_data.get("description", "") or
                   basic_info.get("headline", "") or
                   basic_info.get("tagline", "") or
                   basic_info.get("description", ""))
        
        # About/summary
        about = (company_data.get("about", "") or 
                company_data.get("summary", "") or 
                company_data.get("description", "") or
                basic_info.get("about", "") or
                basic_info.get("summary", "") or
                basic_info.get("description", ""))
        
        # Location - try multiple locations and formats
        location_data = (company_data.get("location", "") or 
                        company_data.get("headquarters", "") or
                        basic_info.get("location", "") or
                        basic_info.get("headquarters", ""))
        
        if isinstance(location_data, dict):
            location = location_data.get("full", "") or location_data.get("city", "") + ", " + location_data.get("country", "")
            location = location.strip(", ")
        elif isinstance(location_data, str):
            location = location_data
        else:
            location = ""
        
        # Company stats - try multiple locations and field names
        followers_count = (company_data.get("followers_count", 0) or 
                          company_data.get("followerCount", 0) or 
                          company_data.get("followers", 0) or 
                          company_data.get("follower_count", 0) or
                          basic_info.get("followers_count", 0) or
                          basic_info.get("followerCount", 0) or
                          basic_info.get("followers", 0))
        
        employees_count = (company_data.get("employees_count", 0) or 
                          company_data.get("employeeCount", 0) or 
                          company_data.get("employees", 0) or 
                          company_data.get("employee_count", 0) or
                          basic_info.get("employees_count", 0) or
                          basic_info.get("employeeCount", 0) or
                          basic_info.get("employees", 0))
        
        # Posts count - LinkedIn companies might have posts
        posts_count = (company_data.get("posts_count", 0) or 
                      company_data.get("postCount", 0) or 
                      company_data.get("posts", 0) or
                      basic_info.get("posts_count", 0) or
                      basic_info.get("postCount", 0) or
                      basic_info.get("posts", 0))
        
        # Connections (for company pages, this might be different)
        connections_count = (company_data.get("connections_count", 0) or 
                            company_data.get("connectionCount", 0) or 
                            company_data.get("connections", 0) or
                            basic_info.get("connections_count", 0) or
                            basic_info.get("connectionCount", 0) or
                            basic_info.get("connections", 0))
        
        # Profile picture/logo
        profile_pic_url = (company_data.get("profile_pic_url", "") or 
                          company_data.get("profilePicture", "") or 
                          company_data.get("logo", "") or 
                          company_data.get("logo_url", "") or
                          basic_info.get("profile_pic_url", "") or
                          basic_info.get("profilePicture", "") or
                          basic_info.get("logo", "") or
                          basic_info.get("logo_url", ""))
        
        # Company URL
        company_url_linkedin = (company_data.get("profile_url", "") or 
                               company_data.get("url", "") or 
                               basic_info.get("profile_url", "") or
                               basic_info.get("url", "") or
                               company_url)
        
        # Company identifier
        public_identifier = (company_data.get("public_identifier", "") or 
                            company_data.get("identifier", "") or
                            basic_info.get("public_identifier", "") or
                            basic_info.get("identifier", "") or
                            company_name.lower().replace(" ", "-"))
        
        # Company type and industry
        company_type = (company_data.get("company_type", "") or 
                       company_data.get("type", "") or
                       basic_info.get("company_type", "") or
                       basic_info.get("type", ""))
        
        industry = (company_data.get("industry", "") or 
                   company_data.get("sector", "") or
                   basic_info.get("industry", "") or
                   basic_info.get("sector", ""))
        
        # Website
        website = (company_data.get("website", "") or 
                  company_data.get("website_url", "") or
                  basic_info.get("website", "") or
                  basic_info.get("website_url", ""))
        
        # Phone, email, address
        phone = (company_data.get("phone", "") or 
                company_data.get("phone_number", "") or
                basic_info.get("phone", "") or
                basic_info.get("phone_number", ""))
        
        email = (company_data.get("email", "") or 
                basic_info.get("email", ""))
        
        address = (company_data.get("address", "") or 
                  company_data.get("headquarters_address", "") or
                  basic_info.get("address", "") or
                  basic_info.get("headquarters_address", ""))
        
        scraped_data = {
            "name": company_name,
            "full_name": company_name,
            "headline": headline,
            "about": about,
            "location": location,
            "followers": followers_count,
            "employees": employees_count,
            "posts": posts_count,  # Posts count
            "connections": connections_count,  # Connections count
            "profile_pic_url": profile_pic_url,
            "profile_url": company_url_linkedin or company_url,
            "public_identifier": public_identifier,
            "company_type": company_type,
            "industry": industry,
            "website": website,
            "phone": phone,
            "email": email,
            "address": address,
            "verified": company_data.get("verified", False) or basic_info.get("verified", False)
        }
        
        logger.info(f"📊 LinkedIn şirkət səhifəsi scrape edildi: {scraped_data['name']}, {scraped_data['followers']} followers, {scraped_data['employees']} employees, {scraped_data['posts']} posts, {scraped_data['connections']} connections")
        
        return scraped_data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ LinkedIn Company Apify API xətası: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"❌ LinkedIn Company scraping xətası: {str(e)}", exc_info=True)
        return None


def scrape_product_with_apify(product_url):
    """
    Scrape e-commerce product information using Apify E-commerce Scraping Tool
    Actor: E-commerce Scraping Tool (ID: 2APbAvDfNDOWXbkWf)
    
    Based on the UI screenshot, the actor has 3 scrape types:
    1. Product detail URLs (productLevelUrl)
    2. Category listing URLs (categoryListingUrl)
    3. Keyword for search (keywordForSearch)
    
    We'll use product detail URLs format.
    """
    try:
        apify_api_key = getattr(settings, 'APIFY_API_KEY', None)
        
        if not apify_api_key or apify_api_key == '':
            logger.warning("⚠️ APIFY_API_KEY yoxdur və ya boşdur, məhsul scraping mümkün deyil")
            return None
        
        logger.info(f"🛒 Məhsul Apify scraping başlayır: {product_url}")
        
        # Apify E-commerce Scraping Tool
        # https://console.apify.com/actors/2APbAvDfNDOWXbkWf
        apify_actor_id = "2APbAvDfNDOWXbkWf"
        
        # Based on UI screenshot, "Product detail URLs" field expects array of URL strings
        # The UI shows it accepts multiple URLs with "+ Add" button
        run_input = {
            "productLevelUrl": [product_url]  # Array of URL strings (not objects)
        }
        
        run_url = f"https://api.apify.com/v2/acts/{apify_actor_id}/runs?token={apify_api_key}"
        
        logger.info(f"📡 Apify E-commerce API request")
        logger.info(f"📦 Input data: {json.dumps(run_input, indent=2)}")
        
        response = requests.post(run_url, json=run_input, timeout=15)
        
        if response.status_code not in [200, 201]:
            error_text = response.text
            logger.error(f"❌ Apify E-commerce API error ({response.status_code}): {error_text[:500]}")
            return None
        
        run_data = response.json()
        run_id = run_data['data']['id']
        initial_status = run_data['data'].get('status', 'UNKNOWN')
        
        logger.info(f"✅ Apify E-commerce actor başladı: {run_id}, initial status: {initial_status}")
        
        max_wait = 120
        wait_interval = 5
        elapsed = 0
        run_status = initial_status
        
        while elapsed < max_wait:
            time.sleep(wait_interval)
            elapsed += wait_interval
            
            status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={apify_api_key}"
            status_response = requests.get(status_url, timeout=10)
            status_data = status_response.json()
            
            run_status = status_data['data']['status']
            
            logger.info(f"⏳ E-commerce scraping status: {run_status} ({elapsed}s)")
            
            if run_status == 'SUCCEEDED':
                logger.info(f"✅ E-commerce scraping tamamlandı ({elapsed}s)")
                break
            elif run_status in ['FAILED', 'ABORTED', 'TIMED-OUT']:
                error_message = status_data['data'].get('statusMessage', '')
                logger.error(f"❌ E-commerce scraping uğursuz: {run_status} - {error_message}")
                return None
            elif run_status in ['READY', 'RUNNING']:
                continue
        
        if run_status != 'SUCCEEDED':
            logger.warning(f"⚠️ E-commerce scraping timeout və ya uğursuz ({max_wait}s), final status: {run_status}")
            return None
        
        # Get dataset ID
        final_status = requests.get(f"https://api.apify.com/v2/actor-runs/{run_id}?token={apify_api_key}", timeout=10).json()
        default_dataset_id = final_status['data'].get('defaultDatasetId')
        
        if not default_dataset_id:
            default_dataset_id = f"runs/{run_id}/dataset"
        
        # Get product data from dataset
        dataset_url = f"https://api.apify.com/v2/datasets/{default_dataset_id}/items?token={apify_api_key}"
        dataset_response = requests.get(dataset_url, timeout=10)
        dataset_response.raise_for_status()
        
        items = dataset_response.json()
        
        if not items or len(items) == 0:
            logger.warning("⚠️ Məhsul səhifəsindən heç bir məlumat tapılmadı")
            return None
        
        logger.info(f"✅ E-commerce dataset-dən {len(items)} item alındı")
        logger.info(f"📋 E-commerce dataset item struktur (FULL): {json.dumps(items[0], indent=2)}")
        
        product_data = items[0]
        
        # Parse product data - based on the JSON structure you provided
        # Structure: { url, name, offers: { price, priceCurrency }, brand: { slogan }, image, description, additionalProperties }
        product_name = product_data.get("name", "")
        description = product_data.get("description", "")
        image_url = product_data.get("image", "")
        
        # Brand - can be object with slogan or string
        brand_data = product_data.get("brand", "")
        if isinstance(brand_data, dict):
            brand = brand_data.get("slogan", "") or brand_data.get("name", "")
        else:
            brand = str(brand_data) if brand_data else ""
        
        # Offers/Price
        offers_data = product_data.get("offers", {})
        price = ""
        currency = ""
        
        if isinstance(offers_data, dict):
            price = str(offers_data.get("price", ""))
            currency = offers_data.get("priceCurrency", "")
        
        # Additional properties
        additional_properties = product_data.get("additionalProperties", {})
        
        scraped_data = {
            "name": product_name,
            "description": description,
            "image": image_url,
            "brand": brand,
            "price": price,
            "currency": currency,
            "url": product_data.get("url", product_url),
            "additional_properties": additional_properties,
            "raw_data": product_data  # Keep raw data for debugging
        }
        
        logger.info(f"📊 Məhsul scrape edildi: {scraped_data['name']}, Price: {scraped_data['price']} {scraped_data['currency']}")
        
        return scraped_data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ E-commerce Apify API xətası: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"❌ E-commerce scraping xətası: {str(e)}", exc_info=True)
        return None


def scrape_facebook_posts_with_apify(profile_url, apify_api_key):
    """
    Scrape Facebook posts using Apify Facebook Posts Scraper
    Actor: apify/facebook-posts-scraper (ID: KoJrdxJCTtpon81KY)
    """
    try:
        logger.info(f"🔍 Facebook Posts Scraper başlayır: {profile_url}")
        
        # Apify Facebook Posts Scraper actor ID
        # https://console.apify.com/actors/KoJrdxJCTtpon81KY
        apify_actor_id = "KoJrdxJCTtpon81KY"
        
        # Apify input format - startUrls array (required field)
        # Based on the actor UI: "Facebook URLs (required)" and "Results amount"
        # Try multiple parameter names to ensure we get more posts
        # Also add scroll parameters to ensure all posts are loaded
        run_input = {
            "startUrls": [{"url": profile_url}],  # startUrls with url objects
            "resultsLimit": 100,  # Try higher limit
            "resultsAmount": 100,  # Alternative parameter name
            "maxResults": 100,  # Another alternative
            "limit": 100,  # Another alternative
            "scrollDown": 50,  # Scroll down 50 times to load more posts (increased for "people" profiles)
            "maxScrolls": 50,  # Maximum scrolls (increased for "people" profiles)
            "scrollLimit": 50,  # Scroll limit (increased for "people" profiles)
            "maxPosts": 100,  # Max posts to scrape
            "maxItems": 100,  # Max items to scrape
            "scroll": True,  # Enable scrolling
            "enableScroll": True,  # Enable scrolling (alternative)
            "loadMore": True  # Load more posts
        }
        
        # Start Apify actor run
        run_url = f"https://api.apify.com/v2/acts/{apify_actor_id}/runs?token={apify_api_key}"
        
        logger.info(f"📡 Apify Facebook Posts API request: {run_url[:80]}...")
        logger.info(f"📦 Input data: {json.dumps(run_input, indent=2)}")
        logger.info(f"📦 Sending resultsLimit: {run_input.get('resultsLimit')} to get more posts")
        
        response = requests.post(
            run_url,
            json=run_input,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code not in [200, 201]:
            error_text = response.text
            logger.error(f"❌ Facebook Posts Scraper API error ({response.status_code}): {error_text[:500]}")
            return None
        
        run_data = response.json()
        run_id = run_data['data']['id']
        initial_status = run_data['data'].get('status', 'UNKNOWN')
        
        logger.info(f"✅ Apify Facebook Posts actor başladı: {run_id}, initial status: {initial_status}")
        
        max_wait = 120
        wait_interval = 5
        elapsed = 0
        run_status = initial_status
        
        while elapsed < max_wait:
            time.sleep(wait_interval)
            elapsed += wait_interval
            
            status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={apify_api_key}"
            status_response = requests.get(status_url, timeout=10)
            status_data = status_response.json()
            
            run_status = status_data['data']['status']
            
            logger.info(f"⏳ Facebook Posts scraping status: {run_status} ({elapsed}s)")
            
            if run_status == 'SUCCEEDED':
                logger.info(f"✅ Facebook Posts scraping tamamlandı ({elapsed}s)")
                break
            elif run_status in ['FAILED', 'ABORTED', 'TIMED-OUT']:
                error_message = status_data['data'].get('statusMessage', '')
                logger.error(f"❌ Facebook Posts scraping uğursuz: {run_status} - {error_message}")
                return None
            elif run_status in ['READY', 'RUNNING']:
                continue
        
        if run_status != 'SUCCEEDED':
            logger.warning(f"⚠️ Facebook Posts scraping timeout və ya uğursuz ({max_wait}s), final status: {run_status}")
            return None
        
        # Get dataset ID
        final_status = requests.get(f"https://api.apify.com/v2/actor-runs/{run_id}?token={apify_api_key}", timeout=10).json()
        default_dataset_id = final_status['data'].get('defaultDatasetId')
        
        if not default_dataset_id:
            default_dataset_id = f"runs/{run_id}/dataset"
        
        # Get posts from dataset
        dataset_url = f"https://api.apify.com/v2/datasets/{default_dataset_id}/items?token={apify_api_key}"
        dataset_response = requests.get(dataset_url, timeout=10)
        dataset_response.raise_for_status()
        
        posts = dataset_response.json()
        
        logger.info(f"✅ Facebook Posts Scraper-dən {len(posts)} post alındı")
        
        # Log all posts to see what we got
        if posts and len(posts) > 0:
            logger.info(f"📋 First post keys: {list(posts[0].keys())}")
            logger.info(f"📋 First post structure (ilk 1500 simvol): {json.dumps(posts[0], indent=2, default=str)[:1500]}")
            
            # Log all post IDs and URLs
            logger.info(f"📋 Bütün post-ların siyahısı:")
            for idx, post in enumerate(posts):
                post_id = post.get("postId", "") or post.get("id", "")
                post_url = post.get("url", "")
                post_text_preview = (post.get("text", "") or post.get("content", ""))[:50]
                logger.info(f"   Post {idx+1}: postId={post_id}, url={post_url[:60] if post_url else 'N/A'}..., text={post_text_preview}...")
        
        return posts
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Facebook Posts Scraper API xətası: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"❌ Facebook Posts scraping xətası: {str(e)}", exc_info=True)
        return None


def scrape_facebook_with_apify(profile_url):
    """
    Scrape Facebook page/profile data using Apify
    Note: Facebook scraping works best with numeric page IDs
    """
    try:
        apify_api_key = getattr(settings, 'APIFY_API_KEY', None)
        
        logger.info(f"🔑 APIFY_API_KEY: {apify_api_key[:20] if apify_api_key else 'YOX'}...")
        
        if not apify_api_key or apify_api_key == '':
            logger.warning("⚠️ APIFY_API_KEY yoxdur və ya boşdur, manual input istifadə edin")
            return None
        
        logger.info(f"🔍 Facebook Apify scraping başlayır: {profile_url}")
        
        # Apify Facebook Pages Scraper actor ID
        # https://console.apify.com/actors/4Hv5RhChiaDk6iwad
        apify_actor_id = "4Hv5RhChiaDk6iwad"
        
        # Əvvəlcə actor-un input schema-sını alaq
        schema_url = f"https://api.apify.com/v2/acts/{apify_actor_id}/input-schema?token={apify_api_key}"
        schema_response = requests.get(schema_url, timeout=10)
        
        if schema_response.status_code == 200:
            schema = schema_response.json()
            logger.info(f"📋 Actor input schema alındı")
            logger.info(f"📋 Schema keys: {list(schema.get('properties', {}).keys())}")
            
            # Log startUrls schema if available
            if 'properties' in schema and 'startUrls' in schema['properties']:
                startUrls_schema = schema['properties']['startUrls']
                logger.info(f"📋 startUrls schema: {json.dumps(startUrls_schema, indent=2)[:500]}")
        else:
            logger.warning(f"⚠️ Schema alına bilmədi ({schema_response.status_code}): {schema_response.text[:200]}")
        
        # Apify input format - startUrls array with object format
        # Based on Apify documentation, startUrls should be array of objects with "url" key
        # Note: This actor may not scrape posts even with maxPosts parameter
        # Posts will be scraped separately if needed
        run_input = {
            "startUrls": [{"url": profile_url}],
            "maxPosts": 0  # This actor doesn't scrape posts, only page info
        }
        
        # Start Apify actor run
        run_url = f"https://api.apify.com/v2/acts/{apify_actor_id}/runs?token={apify_api_key}"
        
        logger.info(f"📡 Apify Facebook API request: {run_url[:80]}...")
        logger.info(f"📦 Input data: {json.dumps(run_input, indent=2)}")
        
        response = requests.post(
            run_url,
            json=run_input,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code not in [200, 201]:
            error_text = response.text
            logger.error(f"❌ Facebook Apify API error ({response.status_code}): {error_text[:500]}")
            logger.error(f"❌ Full error response: {error_text}")
        return None
        
        run_data = response.json()
        run_id = run_data['data']['id']
        initial_status = run_data['data'].get('status', 'UNKNOWN')
        
        logger.info(f"✅ Apify Facebook actor başladı: {run_id}, initial status: {initial_status}")
        
        max_wait = 120
        wait_interval = 5
        elapsed = 0
        run_status = initial_status
        
        while elapsed < max_wait:
            time.sleep(wait_interval)
            elapsed += wait_interval
            
            status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={apify_api_key}"
            status_response = requests.get(status_url, timeout=10)
            status_data = status_response.json()
            
            run_status = status_data['data']['status']
            
            logger.info(f"⏳ Facebook scraping status: {run_status} ({elapsed}s)")
            
            if run_status == 'SUCCEEDED':
                logger.info(f"✅ Facebook scraping tamamlandı ({elapsed}s)")
                break
            elif run_status in ['FAILED', 'ABORTED', 'TIMED-OUT']:
                error_message = status_data['data'].get('statusMessage', '')
                logger.error(f"❌ Facebook scraping uğursuz: {run_status} - {error_message}")
                return None
            elif run_status in ['READY', 'RUNNING']:
                # Run davam edir
                continue
        
        if run_status != 'SUCCEEDED':
            logger.warning(f"⚠️ Facebook scraping timeout və ya uğursuz ({max_wait}s), final status: {run_status}")
            return None
        
        # Dataset ID-ni run-dan alaq
        final_status = requests.get(f"https://api.apify.com/v2/actor-runs/{run_id}?token={apify_api_key}", timeout=10).json()
        default_dataset_id = final_status['data'].get('defaultDatasetId')
        key_value_store_id = final_status['data'].get('defaultKeyValueStoreId')
        
        if not default_dataset_id:
            default_dataset_id = f"runs/{run_id}/dataset"
        
        logger.info(f"📦 Dataset ID: {default_dataset_id}, KV Store ID: {key_value_store_id}")
        
        # Try multiple methods to get data
        items = []
        
        # Method 1: Dataset items
        if default_dataset_id:
            dataset_url = f"https://api.apify.com/v2/datasets/{default_dataset_id}/items?token={apify_api_key}"
            logger.info(f"🔄 Method 1 - Dataset URL: {dataset_url[:100]}...")
            dataset_response = requests.get(dataset_url, timeout=10)
            dataset_response.raise_for_status()
            
            items = dataset_response.json()
            logger.info(f"✅ Method 1 uğurlu: {len(items)} item alındı")
        
        # Method 2: Key-Value Store OUTPUT key
        if (not items or len(items) == 0) and key_value_store_id:
            output_url = f"https://api.apify.com/v2/key-value-stores/{key_value_store_id}/records/OUTPUT?token={apify_api_key}"
            logger.info(f"🔄 Method 2 - Key-Value Store OUTPUT key: {output_url[:100]}...")
            
            try:
                output_response = requests.get(output_url, timeout=10)
                
                if output_response.status_code == 200:
                    output_data = output_response.json()
                    logger.info(f"📋 OUTPUT key data type: {type(output_data)}")
                    
                    if isinstance(output_data, list):
                        items = output_data
                        logger.info(f"✅ Method 2 - OUTPUT key-dən {len(items)} item alındı")
                    elif isinstance(output_data, dict):
                        items = [output_data]
                        logger.info(f"✅ Method 2 - OUTPUT key-dən 1 page dict alındı")
                else:
                    logger.warning(f"⚠️ Method 2 uğursuz ({output_response.status_code}): {output_response.text[:200]}")
            except Exception as e:
                logger.error(f"❌ Method 2 error: {str(e)}")
        
        if not items or len(items) == 0:
            logger.warning("⚠️ Facebook üçün heç bir məlumat tapılmadı")
            return None
        
        logger.info(f"✅ Facebook dataset-dən {len(items)} item alındı")
        
        # Log all items to see structure
        for idx, item in enumerate(items):
            logger.info(f"📋 Item {idx} keys: {list(item.keys())}")
            # Check for any post-related fields
            post_related_keys = [k for k in item.keys() if 'post' in k.lower() or 'text' in k.lower() or 'time' in k.lower()]
            if post_related_keys:
                logger.info(f"📋 Item {idx} post-related keys: {post_related_keys}")
        
        # Separate page info from posts
        # First item is usually the page info, rest might be posts
        profile_data = None
        posts_array = []
        
        for item in items:
            # Check if this is a page info item (has title, categories, etc.)
            if 'title' in item or 'pageUrl' in item:
                if profile_data is None:
                    profile_data = item
                    logger.info(f"📋 Facebook page info keys: {list(item.keys())}")
                    logger.info(f"📋 Facebook page info struktur (ilk 2000 simvol): {json.dumps(item, indent=2, default=str)[:2000]}")
                    
                    # Check for posts in various possible fields
                    possible_post_fields = ['posts', 'pagePosts', 'recentPosts', 'feed', 'timeline', 'pageFeed']
                    for field in possible_post_fields:
                        if field in item:
                            field_value = item[field]
                            logger.info(f"📋 Found field '{field}': type={type(field_value)}, length={len(field_value) if isinstance(field_value, (list, dict)) else 'N/A'}")
                            if isinstance(field_value, list) and len(field_value) > 0:
                                posts_array.extend(field_value)
                                logger.info(f"✅ Added {len(field_value)} posts from field '{field}'")
            # Check if this is a post (has postId, postUrl, text, etc.)
            elif 'postId' in item or 'postUrl' in item or ('text' in item and 'time' in item):
                posts_array.append(item)
                logger.info(f"✅ Found post item: {item.get('postId', item.get('postUrl', 'unknown'))}")
        
        # If no page info found, use first item
        if profile_data is None and len(items) > 0:
            profile_data = items[0]
            logger.info(f"📋 Using first item as page info: {list(profile_data.keys())}")
        
        # Also check if posts are in a nested array in profile_data (final check)
        if profile_data:
            # Check all possible nested structures
            if 'posts' in profile_data:
                nested_posts = profile_data.get('posts', [])
                if isinstance(nested_posts, list) and len(nested_posts) > 0:
                    posts_array.extend(nested_posts)
                    logger.info(f"✅ Added {len(nested_posts)} posts from nested 'posts' field")
            
            # Check if posts are in a dict structure
            if isinstance(profile_data.get('posts'), dict):
                posts_dict = profile_data.get('posts', {})
                logger.info(f"📋 Posts is a dict with keys: {list(posts_dict.keys())}")
                # Try to extract posts from dict
                for key, value in posts_dict.items():
                    if isinstance(value, list):
                        posts_array.extend(value)
                        logger.info(f"✅ Added {len(value)} posts from dict key '{key}'")
        
        logger.info(f"📊 Found {len(posts_array)} posts total in dataset")
        
        # Facebook profile data parse et - Apify facebook-pages-scraper format
        title = profile_data.get("title", "") or profile_data.get("name", "")
        categories = profile_data.get("categories", [])
        likes_count = profile_data.get("likes", 0)
        followers_count = profile_data.get("followers", 0) or likes_count  # Use followers if available, fallback to likes
        info = profile_data.get("info", [])  # info is an array, not dict
        intro = profile_data.get("intro", "")  # About/intro text
        email = profile_data.get("email", "")
        phone = profile_data.get("phone", "")
        address = profile_data.get("address", "")
        website = profile_data.get("website", "")
        websites = profile_data.get("websites", [])  # websites is an array
        page_url = profile_data.get("pageUrl", "") or profile_url
        profile_pic_url = profile_data.get("profilePictureUrl", "") or profile_data.get("profilePhoto", "")
        cover_photo_url = profile_data.get("coverPhotoUrl", "")
        
        # Extract website from websites array if website is empty
        if not website and websites and len(websites) > 0:
            # Filter out Google Maps URLs and get actual website
            for ws in websites:
                if ws and "maps.google.com" not in ws and "facebook.com" not in ws:
                    website = ws
                    break
        
        # Extract about text from intro or info array
        about_text = intro
        if not about_text and info and isinstance(info, list) and len(info) > 0:
            # Join info array items, skip first item if it's just basic info
            about_text = " ".join([item for item in info if item and len(item) > 20])
        
        # Extract rating if available
        rating_info = profile_data.get("rating", "")
        if isinstance(rating_info, str) and "Reviews" in rating_info:
            # Parse "Not yet rated (0 Reviews)" or "4.5 (120 Reviews)"
            rating_text = rating_info
        else:
            rating_text = ""
        
        # Post count - use extracted posts_array from dataset items
        posts_count = len(posts_array) if posts_array else 0
        
        # If posts_count is 0, try to get from profile_data
        if posts_count == 0 and profile_data:
            nested_posts = profile_data.get("posts", [])
            if isinstance(nested_posts, list):
                posts_count = len(nested_posts)
                posts_array = nested_posts
        
        # If still 0, try to extract from info array (e.g., "11 talking about this" might indicate activity)
        # Note: This is just a fallback, actual post count may not be available
        if posts_count == 0 and info and isinstance(info, list):
            for info_item in info:
                if isinstance(info_item, str):
                    # Look for patterns like "X talking about this" or "X posts"
                    import re
                    # Try to find number in "X talking about this" or similar patterns
                    match = re.search(r'(\d+)\s+(?:talking|posts|post)', info_item.lower())
                    if match:
                        potential_count = int(match.group(1))
                        # "talking about this" is not exact post count, but indicates activity
                        # We'll use it as a rough estimate if no other data available
                        logger.info(f"📊 Found potential activity indicator: {info_item}, but not using as post count")
        
        # Always try to scrape posts using Facebook Posts Scraper (even if posts_count > 0)
        # Because the main scraper might not return all posts
        logger.info(f"📝 Facebook Posts Scraper ilə post-ları scrape edirik (current posts_count: {posts_count})...")
        posts_from_scraper = scrape_facebook_posts_with_apify(profile_url, apify_api_key)
        if posts_from_scraper:
            # Log all posts to see what we got
            logger.info(f"📋 Facebook Posts Scraper-dən {len(posts_from_scraper)} post alındı")
            for idx, post in enumerate(posts_from_scraper):
                post_id = post.get("postId", "") or post.get("id", "")
                post_url = post.get("url", "")
                logger.info(f"📋 Post {idx+1}: postId={post_id}, url={post_url[:80] if post_url else 'N/A'}...")
            
            # Remove duplicates based on postId (more strict) - only remove if postId is exactly the same
            seen_post_ids = set()
            unique_posts = []
            for post in posts_from_scraper:
                post_id = post.get("postId", "") or post.get("id", "")
                # Only use postId for duplicate detection, not URL (URLs can be different for same post)
                if post_id:
                    post_id_str = str(post_id)
                    if post_id_str not in seen_post_ids:
                        seen_post_ids.add(post_id_str)
                        unique_posts.append(post)
                    else:
                        logger.warning(f"⚠️ Duplicate post skipped: postId={post_id}")
                else:
                    # If no postId, add anyway (might be different posts)
                    unique_posts.append(post)
            
            posts_array = unique_posts
            posts_count = len(posts_array)
            logger.info(f"✅ Facebook Posts Scraper-dən {len(posts_from_scraper)} post alındı, {posts_count} unikal post (duplicate detection: postId-based)")
        else:
            logger.warning(f"⚠️ Facebook Posts Scraper heç bir post qaytarmadı")
        
        scraped_data = {
            "name": title,
            "full_name": title,
            "username": page_url.split("/")[-1] if page_url else "",
            "about": about_text or " | ".join(categories) if categories else "",
            "likes": likes_count,
            "followers": followers_count,
            "posts": posts_count,  # Post count
            "category": categories,
            "address": address,
            "phone": phone,
            "email": email,
            "website": website,
            "profile_pic_url": profile_pic_url,
            "cover_photo": cover_photo_url,
            "verified": False,  # Not provided by this scraper
            "profile_url": page_url,
            "rating": rating_text,
            "info": info,
            "posts_data": posts_array  # Full posts array if needed
        }
        
        logger.info(f"📊 Facebook scrape edildi: {scraped_data['name']}")
        logger.info(f"   Likes: {scraped_data['likes']}, Followers: {scraped_data['followers']}, Posts: {scraped_data['posts']}")
        logger.info(f"   Posts array length: {len(posts_array)}")
        logger.info(f"   Categories: {', '.join(categories) if categories else 'N/A'}")
        logger.info(f"   About: {about_text[:100] if about_text else 'N/A'}...")
        logger.info(f"   Email: {email or 'N/A'}")
        logger.info(f"   Phone: {phone or 'N/A'}")
        logger.info(f"   Website: {website or 'N/A'}")
        logger.info(f"   Address: {address or 'N/A'}")
        logger.info(f"✅ Facebook Apify scraping uğurlu: {scraped_data['name']}")
        
        return scraped_data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Facebook Apify API xətası: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"❌ Facebook scraping xətası: {str(e)}", exc_info=True)
        return None


def extract_og_preview(url):
    """
    Extract OG preview metadata from URL
    """
    try:
        if not url.startswith(('http://', 'https://')):
            return {
                "error": "URL http:// və ya https:// ilə başlamalıdır",
                "status_code": 400
            }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        
        final_url = response.url
        status_code = response.status_code
        
        logger.info(f"✅ URL fetch edildi: {final_url} (status: {status_code})")
        
        if BeautifulSoup is None:
            return {
                "error": "BeautifulSoup quraşdırılmamışdır",
                "status_code": status_code,
                "final_url": final_url
            }
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        og_data = {
            "title": "",
            "description": "",
            "image": "",
            "site_name": "",
            "final_url": final_url,
            "status_code": status_code
        }
        
        title_tag = soup.find('meta', property='og:title') or soup.find('meta', attrs={'name': 'twitter:title'}) or soup.find('title')
        if title_tag:
            title_value = title_tag.get('content') if title_tag.get('content') else title_tag.get_text().strip()
            og_data["title"] = title_value
            logger.info(f"📝 Title: {title_value}")
        
        desc_tag = soup.find('meta', property='og:description') or soup.find('meta', attrs={'name': 'twitter:description'}) or soup.find('meta', attrs={'name': 'description'})
        if desc_tag:
            desc_value = desc_tag.get('content', '').strip()
            og_data["description"] = desc_value
            logger.info(f"📝 Description: {desc_value[:100]}...")
        
        image_tag = soup.find('meta', property='og:image') or soup.find('meta', attrs={'name': 'twitter:image'})
        if image_tag:
            image_url = image_tag.get('content', '').strip()
            if image_url:
                if image_url.startswith('//'):
                    image_url = 'https:' + image_url
                elif image_url.startswith('/'):
                    parsed = urlparse(final_url)
                    image_url = f"{parsed.scheme}://{parsed.netloc}{image_url}"
                elif not image_url.startswith('http'):
                    image_url = urljoin(final_url, image_url)
                og_data["image"] = image_url
                logger.info(f"🖼️ Image: {image_url}")
        
        site_tag = soup.find('meta', property='og:site_name')
        if site_tag:
            site_value = site_tag.get('content', '').strip()
            og_data["site_name"] = site_value
            logger.info(f"🌐 Site: {site_value}")
        
        if not og_data["site_name"]:
            parsed = urlparse(final_url)
            if 'instagram.com' in parsed.netloc:
                og_data["site_name"] = "Instagram"
            elif 'facebook.com' in parsed.netloc or 'fb.com' in parsed.netloc:
                og_data["site_name"] = "Facebook"
            elif 'linkedin.com' in parsed.netloc:
                og_data["site_name"] = "LinkedIn"
            elif 'twitter.com' in parsed.netloc or 'x.com' in parsed.netloc:
                og_data["site_name"] = "Twitter/X"
        
        if not og_data["title"] and 'instagram.com' in final_url:
            username = final_url.rstrip('/').split('/')[-1]
            og_data["title"] = f"@{username}"
            og_data["description"] = "Instagram profili"
        
        return og_data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ URL request xətası: {str(e)}")
        return {
            "error": f"URL-yə daxil olmaq mümkün olmadı: {str(e)}",
            "status_code": 500
        }
    except Exception as e:
        logger.error(f"❌ OG preview extract xətası: {str(e)}", exc_info=True)
        return {
            "error": f"Xəta baş verdi: {str(e)}",
            "status_code": 500
        }


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def analyze_profile_from_url(request):
    """
    Extract OG preview and analyze profile with AI
    Cache mechanism: Check cache first, if exists and fresh, return cached data
    """
    from .models import ProfileAnalysis
    
    try:
        url = request.data.get('url', '').strip()
        manual_data = request.data.get('manual_data', {})
        force_refresh = request.data.get('force_refresh', False)  # Force new analysis
        
        if not url:
            return Response({
                "error": "URL tələb olunur"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info(f"🔍 Profil analizi başlayır: {url}")
        
        # Check cache first (unless force_refresh is True)
        if not force_refresh:
            try:
                cached_analysis = ProfileAnalysis.objects.filter(profile_url=url).first()
                if cached_analysis:
                    # Cache is valid for 7 days
                    cache_age = timezone.now() - cached_analysis.updated_at
                    if cache_age < timedelta(days=7):
                        logger.info(f"✅ Cache tapıldı: {cached_analysis.profile_username or url} (age: {cache_age.days}d)")
                        cached_analysis.increment_access()
                        
                        return Response({
                            "preview": cached_analysis.preview_data,
                            "smm_analysis": cached_analysis.smm_analysis,
                            "cached": True,
                            "cache_age_days": cache_age.days
                        }, status=status.HTTP_200_OK)
                    else:
                        logger.info(f"⚠️ Cache köhnədir ({cache_age.days} gün), yenilənir...")
                        # Delete old cache
                        cached_analysis.delete()
            except Exception as e:
                logger.warning(f"⚠️ Cache yoxlaması xətası: {str(e)}")
                # Continue with fresh analysis
        
        parsed_url = urlparse(url)
        platform_domain = parsed_url.netloc.lower()
        username = parsed_url.path.rstrip('/').split('/')[-1] if parsed_url.path else ""
        
        logger.info(f"🌐 Platform domain: {platform_domain}")
        
        scraped_data = None
        if 'instagram.com' in platform_domain:
            logger.info(f"📸 Instagram detect edildi, Apify scraping başlayır...")
            scraped_data = scrape_instagram_with_apify(url)
            if scraped_data:
                logger.info(f"✅ Instagram Apify scraping uğurlu: @{scraped_data.get('username')}")
            else:
                logger.warning(f"⚠️ Instagram Apify scraping uğursuz və ya deaktiv")
        elif 'linkedin.com' in platform_domain:
            logger.info(f"💼 LinkedIn detect edildi, Apify scraping başlayır...")
            # Check if it's a company page or personal profile
            if '/company/' in url.lower():
                logger.info(f"🏢 LinkedIn şirkət səhifəsi detect edildi")
                scraped_data = scrape_linkedin_company_with_apify(url)
                # Şirkət səhifələri üçün personal profil scraping-i çağırmırıq
                if scraped_data:
                    logger.info(f"✅ LinkedIn şirkət səhifəsi Apify scraping uğurlu: {scraped_data.get('name')}")
                else:
                    logger.warning(f"⚠️ LinkedIn şirkət səhifəsi Apify scraping uğursuz, OG preview istifadə ediləcək")
            else:
                logger.info(f"👤 LinkedIn personal profil detect edildi")
            scraped_data = scrape_linkedin_with_apify(url)
            if scraped_data:
                    logger.info(f"✅ LinkedIn Apify scraping uğurlu: {scraped_data.get('full_name') or scraped_data.get('name')}")
            else:
                logger.warning(f"⚠️ LinkedIn Apify scraping uğursuz və ya deaktiv")
        elif 'facebook.com' in platform_domain or 'fb.com' in platform_domain:
            logger.info(f"📘 Facebook detect edildi, Apify scraping başlayır...")
            scraped_data = scrape_facebook_with_apify(url)
            if scraped_data:
                logger.info(f"✅ Facebook Apify scraping uğurlu: {scraped_data.get('name')}")
            else:
                logger.warning(f"⚠️ Facebook Apify scraping uğursuz və ya deaktiv")
        
        if scraped_data:
            # Determine platform from scraped data structure
            if 'username' in scraped_data and 'biography' in scraped_data:
                # Instagram
                logger.info(f"✅ Instagram Apify scraping uğurlu")
                platform = "Instagram"
                username = scraped_data.get('username', username)
                name = scraped_data.get('full_name', '')
                bio = scraped_data.get('biography', '')
                followers = str(scraped_data.get('followers', ''))
                following = str(scraped_data.get('following', ''))
                posts = str(scraped_data.get('posts', ''))
                category = scraped_data.get('category', '')
                profile_image = scraped_data.get('profile_pic_url', '')
                
                title = f"@{username}"
                description = bio
            elif 'headline' in scraped_data or 'public_identifier' in scraped_data or 'company_type' in scraped_data:
                # LinkedIn (personal profile or company page)
                logger.info(f"✅ LinkedIn Apify scraping uğurlu")
                platform = "LinkedIn"
                
                # Check if it's a company page
                is_company = 'company_type' in scraped_data or 'industry' in scraped_data or '/company/' in url.lower()
                
                if is_company:
                    logger.info(f"🏢 LinkedIn şirkət səhifəsi parse edilir")
                    username = scraped_data.get('public_identifier', '') or username or scraped_data.get('profile_url', '').split('/')[-1] if scraped_data.get('profile_url') else ''
                    name = scraped_data.get('name', '') or scraped_data.get('full_name', '')
                    bio = scraped_data.get('about', '') or scraped_data.get('headline', '')
                    followers = str(scraped_data.get('followers', 0))
                    following = str(scraped_data.get('employees', 0))  # Company pages use employees instead of connections
                    posts = str(scraped_data.get('posts', 0))  # Posts count from scraped data
                    connections = str(scraped_data.get('connections', 0))  # Connections count
                    category = scraped_data.get('industry', '') or scraped_data.get('location', '')
                    profile_image = scraped_data.get('profile_pic_url', '')
                    
                    logger.info(f"📊 LinkedIn şirkət səhifəsi parse edildi: name={name}, followers={followers}, employees={following}, posts={posts}, connections={connections}, bio length={len(bio)}")
                else:
                    logger.info(f"👤 LinkedIn personal profil parse edilir")
                username = scraped_data.get('public_identifier', '') or username or scraped_data.get('profile_url', '').split('/')[-1] if scraped_data.get('profile_url') else ''
                name = scraped_data.get('full_name', '')
                bio = scraped_data.get('about', '') or scraped_data.get('headline', '')
                followers = str(scraped_data.get('followers', 0))
                following = str(scraped_data.get('connections', 0))  # LinkedIn uses connections
                posts = '0'  # LinkedIn doesn't provide posts count in profile
                category = scraped_data.get('location', '')
                profile_image = scraped_data.get('profile_pic_url', '')
                
                logger.info(f"📊 LinkedIn parse edildi: name={name}, followers={followers}, connections={following}, bio length={len(bio)}")
                
                title = name or username
                description = bio
            elif 'likes' in scraped_data or 'pageUrl' in scraped_data:
                # Facebook
                logger.info(f"✅ Facebook Apify scraping uğurlu")
                platform = "Facebook"
                username = scraped_data.get('username', username)
                name = scraped_data.get('full_name', '') or scraped_data.get('name', '')
                bio = scraped_data.get('about', '')
                followers = str(scraped_data.get('followers', 0))
                following = str(scraped_data.get('likes', 0))  # Facebook uses "likes" instead of following
                posts = str(scraped_data.get('posts', 0))  # Posts count (number, not array)
                category = ', '.join(scraped_data.get('category', [])) if isinstance(scraped_data.get('category'), list) else scraped_data.get('category', '')
                profile_image = scraped_data.get('profile_pic_url', '')
                
                logger.info(f"📊 Facebook parse edildi: name={name}, followers={followers}, likes={following}, bio length={len(bio)}")
                
                title = name or f"@{username}"
                description = bio
        elif manual_data and manual_data.get('username'):
            # Manual input - platform detect from URL
            logger.info(f"📝 Manual məlumatlar istifadə edilir")
            
            # Detect platform from URL
            if 'facebook.com' in platform_domain or 'fb.com' in platform_domain:
                platform = "Facebook"
            elif 'linkedin.com' in platform_domain:
                platform = "LinkedIn"
            else:
                platform = "Instagram"
            
            username = manual_data.get('username', username)
            name = manual_data.get('name', '')
            bio = manual_data.get('bio', '')
            followers = manual_data.get('followers', '')
            following = manual_data.get('following', '')
            posts = manual_data.get('posts', '')
            category = manual_data.get('category', '')
            
            title = f"@{username}" if username else name
            description = bio if bio else ""
            profile_image = ""
            
            logger.info(f"📊 Manual məlumatlar ({platform}): posts={posts}, followers={followers}, category={category}")
            logger.info(f"📝 Platform detected: {platform}, username: {username}, name: {name}")
        else:
            og_preview = extract_og_preview(url)
            
            if "error" in og_preview:
                return Response({
                    "error": og_preview["error"],
                    "preview": og_preview
                }, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info(f"✅ OG preview alındı: {og_preview.get('title', 'N/A')}")
            
            platform = og_preview.get('site_name', 'Unknown')
            title = og_preview.get('title', '')
            description = og_preview.get('description', '')
            profile_image = og_preview.get('image', '')
            name = ''
            bio = ''
            followers = ''
            following = ''
            posts = ''
            category = ''
            
            if not title and username:
                title = f"@{username}"
            if not description and username:
                description = f"{platform} profili"
        
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        profile_info = f"""PROFIL MƏLUMATLARI:
- Platforma: {platform}
- Username: @{username}"""

        if name:
            profile_info += f"\n- Ad/Name: {name}"
        if posts:
            profile_info += f"\n- Posts: {posts}"
        if followers:
            profile_info += f"\n- Followers: {followers}"
        if following:
            profile_info += f"\n- Following: {following}"
        if category:
            profile_info += f"\n- Kateqoriya: {category}"
        if bio:
            profile_info += f"\n- Bio: {bio}"
        elif description:
            profile_info += f"\n- Description: {description}"
        
        profile_info += f"\n- URL: {url}"
        
        analysis_prompt = f"""Sosial media profil analizi (Azərbaycan dilində).

{profile_info}

Bu məlumatlara əsasən profil analizi edin və JSON formatda qaytarın:
{{
    "account_type": "Personal/Business/Influencer/Brand",
    "niche": "Fashion/Tech/Food/...",
    "content_style": "Professional/Casual/Creative/..."
}}

Bütün mətnlər Azərbaycan dilində olmalıdır."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Siz peşəkar Social Media Marketing (SMM) məsləhətçisisiniz. Profil preview məlumatlarına əsasən analiz edib konkret tövsiyələr verirsiniz. Bütün cavablar Azərbaycan dilində olmalıdır. YALNIZ JSON formatda cavab verin, heç bir əlavə mətn yazmayın."
                },
                {
                    "role": "user",
                    "content": analysis_prompt
                }
            ],
            temperature=0.7,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        analysis_text = response.choices[0].message.content
        
        if not analysis_text:
            logger.error("❌ OpenAI cavabı boşdur")
            return Response({
                "error": "AI cavab vermədi",
                "preview": {
                    "title": og_preview.get("title", ""),
                    "description": og_preview.get("description", ""),
                    "image": og_preview.get("image", ""),
                    "site_name": og_preview.get("site_name", ""),
                    "final_url": og_preview.get("final_url", url)
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        analysis_text = analysis_text.strip()
        logger.info(f"📝 AI cavabı (ilk 200 simvol): {analysis_text[:200]}")
        
        if analysis_text.startswith('```'):
            analysis_text = re.sub(r'^```json?\s*', '', analysis_text)
            analysis_text = re.sub(r'\s*```$', '', analysis_text)
        
        smm_analysis = json.loads(analysis_text)
        
        logger.info(f"✅ Analiz tamamlandı")
        
        preview_data = {
            "title": title,
            "description": description,
            "image": profile_image,
            "site_name": platform,
            "final_url": url,
            "stats": {
                "followers": str(followers) if followers else "0",
                "following": str(following) if following else "0",
                "posts": str(posts) if posts else "0"
            }
        }
        
        # Apify-dən gələn əlavə məlumatlar
        if scraped_data:
            # Profil şəklini prioritet et (HD versiyası varsa)
            profile_pic = scraped_data.get("profile_pic_url", "")
            if profile_pic:
                preview_data["image"] = profile_pic
                logger.info(f"🖼️ Profil şəkli əlavə edildi: {profile_pic[:80]}...")
            
            # Latest posts parse et
            latest_posts = scraped_data.get("latest_posts", [])
            parsed_posts = []
            for post in latest_posts:
                parsed_posts.append({
                    "id": post.get("id", ""),
                    "type": post.get("type", ""),
                    "url": post.get("url", ""),
                    "caption": post.get("caption", ""),
                    "likes_count": post.get("likesCount", 0),
                    "comments_count": post.get("commentsCount", 0),
                    "timestamp": post.get("timestamp", ""),
                    "hashtags": post.get("hashtags", []),
                    "mentions": post.get("mentions", []),
                    "display_url": post.get("displayUrl", ""),
                    "video_url": post.get("videoUrl", ""),
                    "short_code": post.get("shortCode", "")
                })
            
            # Platforma görə fərqli məlumatlar
            if 'username' in scraped_data and 'biography' in scraped_data:
                # Instagram
                preview_data.update({
                    "username": scraped_data.get("username", ""),
                    "full_name": scraped_data.get("full_name", ""),
                    "biography": scraped_data.get("biography", ""),
                    "is_verified": scraped_data.get("is_verified", False),
                    "is_business": scraped_data.get("is_business", False),
                    "category": scraped_data.get("category", ""),
                    "is_private": scraped_data.get("is_private", False),
                    "highlight_reel_count": scraped_data.get("highlight_reel_count", 0),
                    "igtv_video_count": scraped_data.get("igtv_video_count", 0),
                    "latest_posts": parsed_posts
                })
                preview_data["stats"] = {
                    "followers": str(scraped_data.get("followers", 0)),
                    "following": str(scraped_data.get("following", 0)),
                    "posts": str(scraped_data.get("posts", 0))
                }
                
                logger.info(f"📸 {len(parsed_posts)} paylaşım parse edildi")
            elif 'headline' in scraped_data or 'public_identifier' in scraped_data or 'company_type' in scraped_data:
                # LinkedIn (personal profile or company page)
                is_company = 'company_type' in scraped_data or 'industry' in scraped_data or '/company/' in url.lower()
                
                if is_company:
                    # LinkedIn Company Page
                    preview_data.update({
                        "full_name": scraped_data.get("name", "") or scraped_data.get("full_name", ""),
                        "biography": scraped_data.get("about", "") or scraped_data.get("headline", ""),
                        "headline": scraped_data.get("headline", ""),
                        "location": scraped_data.get("location", ""),
                        "company_type": scraped_data.get("company_type", ""),
                        "industry": scraped_data.get("industry", ""),
                        "website": scraped_data.get("website", ""),
                        "public_identifier": scraped_data.get("public_identifier", ""),
                        "verified": scraped_data.get("verified", False)
                    })
                    preview_data["stats"] = {
                        "followers": str(scraped_data.get("followers", 0)),
                        "employees": str(scraped_data.get("employees", 0)),
                        "posts": str(scraped_data.get("posts", 0)),  # Posts count from scraped data
                        "connections": str(scraped_data.get("connections", 0))  # Connections count
                    }
                    
                    logger.info(f"🏢 LinkedIn şirkət səhifəsi məlumatları əlavə edildi: name={preview_data.get('full_name')[:50] if preview_data.get('full_name') else 'N/A'}, industry={preview_data.get('industry')}, location={preview_data.get('location')}")
                    logger.info(f"🏢 LinkedIn şirkət stats: {scraped_data.get('followers')} followers, {scraped_data.get('employees')} employees, {scraped_data.get('posts', 0)} posts, {scraped_data.get('connections', 0)} connections")
                else:
                    # LinkedIn Personal Profile
                    preview_data.update({
                        "full_name": scraped_data.get("full_name", ""),
                        "first_name": scraped_data.get("first_name", ""),
                        "last_name": scraped_data.get("last_name", ""),
                        "biography": scraped_data.get("about", "") or scraped_data.get("headline", ""),
                        "headline": scraped_data.get("headline", ""),
                        "location": scraped_data.get("location", ""),
                        "experience": scraped_data.get("experience", []),
                        "education": scraped_data.get("education", []),
                        "skills": scraped_data.get("skills", []),
                        "public_identifier": scraped_data.get("public_identifier", ""),
                        "verified": scraped_data.get("verified", False),
                        "open_to_work": scraped_data.get("open_to_work", False),
                        "premium": scraped_data.get("premium", False)
                    })
                preview_data["stats"] = {
                    "followers": str(scraped_data.get("followers", 0)),
                    "connections": str(scraped_data.get("connections", 0)),
                    "posts": "0"  # LinkedIn doesn't provide posts count
                }
                
                logger.info(f"💼 LinkedIn məlumatları əlavə edildi: headline={preview_data.get('headline')[:50] if preview_data.get('headline') else 'N/A'}, location={preview_data.get('location')}, experience={len(preview_data.get('experience', []))}, education={len(preview_data.get('education', []))}, skills={len(preview_data.get('skills', []))}")
                logger.info(f"💼 LinkedIn stats: {scraped_data.get('followers')} followers, {scraped_data.get('connections')} connections")
            elif 'likes' in scraped_data or 'pageUrl' in scraped_data:
                # Facebook
                # Parse Facebook posts if available (posts_data is the array, posts is the count)
                facebook_posts = scraped_data.get("posts_data", [])
                parsed_fb_posts = []
                seen_ids = set()  # Track seen IDs to ensure uniqueness
                
                for idx, post in enumerate(facebook_posts):
                    # Extract text/content - try multiple possible field names
                    post_text = (post.get("text", "") or 
                                post.get("content", "") or 
                                post.get("message", "") or
                                post.get("postText", "") or
                                post.get("description", ""))
                    
                    # Extract image - try multiple possible field names
                    post_image = (post.get("image", "") or 
                                 post.get("imageUrl", "") or
                                 post.get("photo", "") or
                                 post.get("photoUrl", "") or
                                 post.get("images", [""])[0] if isinstance(post.get("images"), list) and len(post.get("images", [])) > 0 else "")
                    
                    # Extract video - try multiple possible field names
                    post_video = (post.get("video", "") or 
                                 post.get("videoUrl", "") or
                                 post.get("videoUrlHd", "") or
                                 post.get("videos", [""])[0] if isinstance(post.get("videos"), list) and len(post.get("videos", [])) > 0 else "")
                    
                    # Extract from media field (Facebook Posts Scraper uses this)
                    media = post.get("media")
                    if media:
                        if isinstance(media, list) and len(media) > 0:
                            # media is an array of media objects
                            for media_item in media:
                                if isinstance(media_item, dict):
                                    # Check media type
                                    media_type = media_item.get("__typename", "") or media_item.get("__isMedia", "")
                                    
                                    # Extract image from photo_image.uri or thumbnail
                                    if not post_image:
                                        photo_image = media_item.get("photo_image", {})
                                        if isinstance(photo_image, dict):
                                            post_image = photo_image.get("uri", "")
                                        
                                        # Fallback to thumbnail
                                        if not post_image:
                                            post_image = media_item.get("thumbnail", "")
                                        
                                        # Fallback to other fields
                                        if not post_image:
                                            post_image = (media_item.get("url", "") or 
                                                         media_item.get("image", "") or
                                                         media_item.get("photo", "") or
                                                         media_item.get("src", ""))
                                    
                                    # Check for video (if media type is Video)
                                    if not post_video and ("Video" in media_type or "video" in str(media_type).lower()):
                                        post_video = (media_item.get("videoUrl", "") or 
                                                     media_item.get("video", "") or
                                                     media_item.get("videoUrlHd", "") or
                                                     media_item.get("source", ""))
                        elif isinstance(media, dict):
                            # media is a single object
                            media_type = media.get("__typename", "") or media.get("__isMedia", "")
                            
                            # Extract image from photo_image.uri or thumbnail
                            if not post_image:
                                photo_image = media.get("photo_image", {})
                                if isinstance(photo_image, dict):
                                    post_image = photo_image.get("uri", "")
                                
                                # Fallback to thumbnail
                                if not post_image:
                                    post_image = media.get("thumbnail", "")
                                
                                # Fallback to other fields
                                if not post_image:
                                    post_image = (media.get("url", "") or 
                                                 media.get("image", "") or
                                                 media.get("photo", "") or
                                                 media.get("src", ""))
                            
                            # Check for video
                            if not post_video and ("Video" in media_type or "video" in str(media_type).lower()):
                                post_video = (media.get("videoUrl", "") or 
                                             media.get("video", "") or
                                             media.get("videoUrlHd", "") or
                                             media.get("source", ""))
                    
                    # Extract URL - try multiple possible field names
                    post_url = (post.get("postUrl", "") or 
                               post.get("url", "") or
                               post.get("link", "") or
                               post.get("permalink", ""))
                    
                    # Extract timestamp - try multiple possible field names
                    post_timestamp = (post.get("time", "") or 
                                     post.get("timestamp", "") or
                                     post.get("createdTime", "") or
                                     post.get("date", "") or
                                     post.get("publishedAt", ""))
                    
                    # Format timestamp for display (if it's ISO format)
                    formatted_date = ""
                    if post_timestamp:
                        try:
                            from datetime import datetime
                            # Try to parse ISO format timestamp
                            if isinstance(post_timestamp, str) and "T" in post_timestamp:
                                dt = datetime.fromisoformat(post_timestamp.replace("Z", "+00:00"))
                                formatted_date = dt.strftime("%Y M%m %d")  # Format: "2025 M12 24"
                            elif isinstance(post_timestamp, (int, float)):
                                # Unix timestamp
                                dt = datetime.fromtimestamp(post_timestamp)
                                formatted_date = dt.strftime("%Y M%m %d")
                        except:
                            formatted_date = str(post_timestamp)
                    
                    # Generate unique ID - use postId/id if available, otherwise create unique ID
                    post_id = (post.get("postId", "") or 
                              post.get("id", "") or 
                              post.get("_id", ""))
                    
                    # Convert to string if it's a number
                    if post_id:
                        post_id = str(post_id)
                    
                    # If ID is empty or already seen, create unique ID
                    if not post_id or post_id in seen_ids:
                        # Create unique ID from URL, timestamp, or index
                        if post_url:
                            # Extract ID from URL if possible
                            import re
                            url_id_match = re.search(r'/(\d+)/', post_url)
                            if url_id_match:
                                post_id = f"{url_id_match.group(1)}_{idx}"
                            else:
                                # Use hash of URL + index
                                post_id = f"post_{hash(post_url) % 1000000}_{idx}"
                        elif post_timestamp:
                            # Use timestamp + index
                            post_id = f"post_{post_timestamp}_{idx}"
                        else:
                            # Use index as last resort
                            post_id = f"post_{idx}"
                    
                    # Ensure ID is unique by appending index if still duplicate
                    original_id = post_id
                    counter = 0
                    while post_id in seen_ids:
                        counter += 1
                        post_id = f"{original_id}_{counter}"
                    
                    seen_ids.add(post_id)
                    
                    # Extract all available data for frontend
                    parsed_post = {
                        "id": post_id,  # Always unique
                        "type": post.get("type", "") or post.get("postType", ""),
                        "url": post_url,
                        "text": post_text,
                        "caption": post_text,  # Frontend uses caption field
                        "likes_count": post.get("likes", 0) or post.get("likeCount", 0) or post.get("reactions", 0),
                        "comments_count": post.get("comments", 0) or post.get("commentCount", 0),
                        "shares_count": post.get("shares", 0) or post.get("shareCount", 0),
                        "timestamp": post_timestamp,
                        "date": formatted_date,  # Formatted date for display
                        "image": post_image,
                        "video": post_video,
                        "display_url": post_image,  # Frontend uses display_url for image display
                        # Additional fields from original post
                        "postId": post.get("postId", "") or post.get("id", ""),
                        "time": post.get("time", ""),
                        "facebookUrl": post.get("facebookUrl", ""),
                        "pageName": post.get("pageName", ""),
                        # Media information
                        "media": []
                    }
                    
                    # Extract all media items with full details
                    if media:
                        if isinstance(media, list):
                            for media_item in media:
                                if isinstance(media_item, dict):
                                    media_info = {
                                        "type": media_item.get("__typename", "") or media_item.get("__isMedia", ""),
                                        "id": media_item.get("id", ""),
                                        "url": media_item.get("url", ""),
                                        "thumbnail": media_item.get("thumbnail", ""),
                                    }
                                    # Extract photo_image details
                                    photo_image = media_item.get("photo_image", {})
                                    if isinstance(photo_image, dict):
                                        media_info["photo_image"] = {
                                            "uri": photo_image.get("uri", ""),
                                            "height": photo_image.get("height", 0),
                                            "width": photo_image.get("width", 0)
                                        }
                                    parsed_post["media"].append(media_info)
                        elif isinstance(media, dict):
                            media_info = {
                                "type": media.get("__typename", "") or media.get("__isMedia", ""),
                                "id": media.get("id", ""),
                                "url": media.get("url", ""),
                                "thumbnail": media.get("thumbnail", ""),
                            }
                            photo_image = media.get("photo_image", {})
                            if isinstance(photo_image, dict):
                                media_info["photo_image"] = {
                                    "uri": photo_image.get("uri", ""),
                                    "height": photo_image.get("height", 0),
                                    "width": photo_image.get("width", 0)
                                }
                            parsed_post["media"].append(media_info)
                    
                    parsed_fb_posts.append(parsed_post)
                
                # Get posts count (use posts field if available, otherwise count from array)
                posts_count = scraped_data.get("posts", 0) or len(parsed_fb_posts)
                
                preview_data.update({
                    "username": scraped_data.get("username", ""),
                    "full_name": scraped_data.get("name", "") or scraped_data.get("full_name", ""),
                    "biography": scraped_data.get("about", ""),
                    "category": ', '.join(scraped_data.get("category", [])) if isinstance(scraped_data.get("category"), list) else scraped_data.get("category", ""),
                    "address": scraped_data.get("address", ""),
                    "phone": scraped_data.get("phone", ""),
                    "email": scraped_data.get("email", ""),
                    "website": scraped_data.get("website", ""),
                    "verified": scraped_data.get("verified", False),
                    "profile_pic_url": scraped_data.get("profile_pic_url", ""),
                    "cover_photo": scraped_data.get("cover_photo", ""),
                    "latest_posts": parsed_fb_posts
                })
                preview_data["stats"] = {
                    "followers": str(scraped_data.get("followers", 0)),
                    "likes": str(scraped_data.get("likes", 0)),
                    "posts": str(posts_count)
                }
                
                logger.info(f"📘 Facebook məlumatları əlavə edildi: {len(parsed_fb_posts)} paylaşım parse edildi")
                logger.info(f"📘 Orijinal post sayı: {len(facebook_posts)}, Parse edilmiş post sayı: {len(parsed_fb_posts)}")
                
                # Log all post IDs to check for duplicates
                post_ids_list = [p.get('id', 'NO_ID') for p in parsed_fb_posts]
                unique_ids = set(post_ids_list)
                if len(post_ids_list) != len(unique_ids):
                    logger.warning(f"⚠️ Duplicate post IDs tapıldı! Total: {len(post_ids_list)}, Unique: {len(unique_ids)}")
                    from collections import Counter
                    id_counts = Counter(post_ids_list)
                    duplicates = {k: v for k, v in id_counts.items() if v > 1}
                    logger.warning(f"⚠️ Duplicate IDs: {duplicates}")
                
                if parsed_fb_posts and len(parsed_fb_posts) > 0:
                    logger.info(f"📘 İlk 3 post ID-ləri: {[p.get('id', 'NO_ID') for p in parsed_fb_posts[:3]]}")
                    first_post = parsed_fb_posts[0]
                    logger.info(f"📘 İlk post nümunəsi:")
                    logger.info(f"   ID: {first_post.get('id')}")
                    logger.info(f"   PostId: {first_post.get('postId')}")
                    logger.info(f"   URL: {first_post.get('url', '')[:80]}...")
                    logger.info(f"   Text length: {len(first_post.get('text', ''))}")
                    logger.info(f"   Text preview: {first_post.get('text', '')[:100]}...")
                    logger.info(f"   Image URL: {first_post.get('image', '')[:100] if first_post.get('image') else 'YOX'}...")
                    logger.info(f"   Display URL: {first_post.get('display_url', '')[:100] if first_post.get('display_url') else 'YOX'}...")
                    logger.info(f"   Date: {first_post.get('date', 'N/A')}")
                    logger.info(f"   Timestamp: {first_post.get('timestamp', 'N/A')}")
                    logger.info(f"   Likes: {first_post.get('likes_count', 0)}")
                    logger.info(f"   Comments: {first_post.get('comments_count', 0)}")
                    logger.info(f"   Shares: {first_post.get('shares_count', 0)}")
                    logger.info(f"   Media count: {len(first_post.get('media', []))}")
                logger.info(f"📘 Facebook stats: {scraped_data.get('followers')} followers, {scraped_data.get('likes')} likes, {posts_count} posts")
        
        # Save to cache
        try:
            with transaction.atomic():
                # Get or create cache entry
                cached_analysis, created = ProfileAnalysis.objects.update_or_create(
                    profile_url=url,
                    defaults={
                        'user': request.user if request.user.is_authenticated else None,
                        'profile_username': preview_data.get('username', ''),
                        'platform': preview_data.get('site_name', 'Unknown'),
                        'preview_data': preview_data,
                        'smm_analysis': smm_analysis,
                        'updated_at': timezone.now()
                    }
                )
                if created:
                    logger.info(f"💾 Cache yaradıldı: {url}")
                else:
                    logger.info(f"💾 Cache yeniləndi: {url}")
        except Exception as e:
            logger.warning(f"⚠️ Cache yazma xətası: {str(e)}")
            # Continue even if cache fails
        
        return Response({
            "preview": preview_data,
            "smm_analysis": smm_analysis,
            "cached": False
        }, status=status.HTTP_200_OK)
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON parse xətası: {str(e)}")
        return Response({
            "error": "AI cavabı parse edilə bilmədi",
            "preview": og_preview if 'og_preview' in locals() else {}
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        logger.error(f"❌ Profil analiz xətası: {str(e)}", exc_info=True)
        return Response({
            "error": f"Analiz zamanı xəta baş verdi: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_saved_profiles(request):
    """
    Get all saved profile analyses for a specific platform
    Query param: ?platform=instagram|facebook|linkedin
    Returns cached profiles ordered by last_accessed
    """
    from .models import ProfileAnalysis
    
    try:
        platform_filter = request.GET.get('platform', 'instagram').lower()
        
        # Map platform names
        platform_map = {
            'instagram': 'instagram',
            'facebook': 'facebook',
            'linkedin': 'linkedin'
        }
        
        platform = platform_map.get(platform_filter, 'instagram')
        
        logger.info(f"📋 Saved profiles sorğusu: platform={platform}")
        
        # Get saved profiles for the platform
        profiles = ProfileAnalysis.objects.filter(
            platform__icontains=platform
        ).order_by('-last_accessed')[:50]  # Limit to 50 most recent
        
        profiles_data = []
        for profile in profiles:
            preview = profile.preview_data or {}
            stats = preview.get('stats', {})
            
            logger.info(f"📋 Profile: {profile.profile_username}, stats: {stats}")
            
            profiles_data.append({
                'id': str(profile.id),
                'profile_url': profile.profile_url,
                'username': profile.profile_username or preview.get('username', ''),
                'full_name': preview.get('full_name', ''),
                'image': preview.get('image', ''),
                'platform': profile.platform,
                'stats': stats,
                'preview_data': preview,  # Include full preview_data for debugging
                'smm_analysis': profile.smm_analysis or {},
                'last_accessed': profile.last_accessed.isoformat() if profile.last_accessed else None,
                'access_count': profile.access_count,
                'created_at': profile.created_at.isoformat() if profile.created_at else None
            })
        
        logger.info(f"📋 {len(profiles_data)} saved profile qaytarıldı")
        
        return Response({
            'profiles': profiles_data,
            'count': len(profiles_data)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"❌ Saved profiles xətası: {str(e)}", exc_info=True)
        return Response({
            "error": f"Saved profiles alınarkən xəta: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

