"""
Image Branding Service
Applies company logo and slogan overlays to images
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from django.core.files.base import ContentFile
from django.conf import settings
import io
import os
import requests
from pathlib import Path


class ImageBrandingService:
    """Service for applying company branding to images"""
    
    def __init__(self, company_profile):
        """
        Initialize branding service with company profile
        
        Args:
            company_profile: CompanyProfile model instance
        """
        self.company_profile = company_profile
        self.logo = company_profile.logo
        self.slogan = company_profile.slogan
        self.slogan_enabled = getattr(company_profile, 'slogan_enabled', True)
        self.branding_enabled = company_profile.branding_enabled
        
        # Get branding settings
        self.branding_mode = getattr(company_profile, 'branding_mode', None) or 'standard'
        self.logo_position = getattr(company_profile, 'logo_position', 'top-center')
        self.slogan_position = getattr(company_profile, 'slogan_position', 'bottom-center')
        
        # Logo size (default 13%)
        self.logo_size_percent = getattr(company_profile, 'logo_size_percent', 13)
        # Clamp logo size to valid range (2-25%)
        self.logo_size_percent = max(2, min(25, self.logo_size_percent))
        
        # Slogan size (default 4%)
        self.slogan_size_percent = getattr(company_profile, 'slogan_size_percent', 4)
        # Clamp slogan size to valid range (2-8%)
        self.slogan_size_percent = max(2, min(8, self.slogan_size_percent))
        
        # Gradient settings
        self.gradient_enabled = getattr(company_profile, 'gradient_enabled', True)
        self.gradient_color = getattr(company_profile, 'gradient_color', '#3B82F6')
        self.gradient_height_percent = getattr(company_profile, 'gradient_height_percent', 25)
        self.gradient_position = getattr(company_profile, 'gradient_position', 'both')
        
        self.padding = 40  # Standard padding
    
    def apply_branding(self, base_image_path_or_url):
        """
        Apply company logo and slogan to an image with gradient overlays
        
        Args:
            base_image_path_or_url: Path to image file or URL
            
        Returns:
            PIL Image object with branding applied
        """
        if not self.branding_enabled:
            # Just return the original image
            return self._load_image(base_image_path_or_url)
        
        if not self.logo:
            # No logo available, return original
            return self._load_image(base_image_path_or_url)
        
        # Load base image
        base_img = self._load_image(base_image_path_or_url)
        
        # Convert to RGBA for transparency support
        if base_img.mode != 'RGBA':
            base_img = base_img.convert('RGBA')
        
        base_width, base_height = base_img.size
        
        # Load logo
        logo_img = self._load_image(self.logo.path)
        if logo_img.mode != 'RGBA':
            logo_img = logo_img.convert('RGBA')
        
        # Get gradient color
        gradient_color = self._get_gradient_color()
        
        # Add gradients based on gradient_position setting
        if self.gradient_enabled:
            if self.gradient_position in ['top', 'both']:
                base_img = self._add_top_gradient(base_img, gradient_color)
            if self.gradient_position in ['bottom', 'both']:
                base_img = self._add_bottom_gradient(base_img, gradient_color)
        
        # Add logo
        base_img = self._add_logo(base_img, logo_img)
        
        # Add slogan if provided and enabled
        if self.slogan and self.slogan_enabled:
            base_img = self._add_slogan(base_img, self.slogan)
        
        # Convert back to RGB for saving
        if base_img.mode == 'RGBA':
            rgb_img = Image.new('RGB', base_img.size, (255, 255, 255))
            rgb_img.paste(base_img, mask=base_img.split()[3])
            base_img = rgb_img
        
        return base_img
    
    def _load_image(self, path_or_url):
        """Load image from file path or URL"""
        if isinstance(path_or_url, str) and (path_or_url.startswith('http://') or path_or_url.startswith('https://')):
            # Download from URL
            response = requests.get(path_or_url, timeout=30)
            response.raise_for_status()
            img = Image.open(io.BytesIO(response.content))
        else:
            # Load from file
            img = Image.open(path_or_url)
        
        return img
    
    def _resize_logo(self, logo_img, target_width):
        """Resize logo maintaining aspect ratio"""
        original_width, original_height = logo_img.size
        aspect_ratio = original_height / original_width
        target_height = int(target_width * aspect_ratio)
        
        return logo_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
    
    def _calculate_logo_position(self, base_size, logo_size, position, padding):
        """Calculate logo position based on specified corner or center"""
        base_width, base_height = base_size
        logo_width, logo_height = logo_size
        
        positions = {
            'bottom-left': (padding, base_height - logo_height - padding),
            'bottom-right': (base_width - logo_width - padding, base_height - logo_height - padding),
            'top-left': (padding, padding),
            'top-right': (base_width - logo_width - padding, padding),
            'middle-top': ((base_width - logo_width) // 2, padding),  # Horizontally centered, top
            'middle': ((base_width - logo_width) // 2, (base_height - logo_height) // 2),  # Full center
        }
        
        return positions.get(position, positions['bottom-right'])
    
    def _get_gradient_color(self):
        """Get gradient color from settings or brand analysis"""
        # Use custom gradient color if set
        if self.gradient_color and self.gradient_color != '#3B82F6':
            return self._hex_to_rgb(self.gradient_color)
        
        # Try to get from brand analysis
        if hasattr(self.company_profile, 'brand_analysis') and self.company_profile.brand_analysis:
            primary_color = self.company_profile.brand_analysis.get('primary_color')
            if primary_color:
                return self._hex_to_rgb(primary_color)
        
        # Default cyan color
        return (59, 130, 246)  # #3B82F6
    
    def _hex_to_rgb(self, hex_color):
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def _add_top_gradient(self, img, gradient_color):
        """Add top gradient overlay"""
        width, height = img.size
        
        # Create gradient overlay (top portion) - use configured height
        gradient_height = int(height * (self.gradient_height_percent / 100))
        gradient = Image.new('RGBA', (width, gradient_height), (0, 0, 0, 0))
        
        # Draw gradient from solid to transparent
        for y in range(gradient_height):
            # Alpha decreases from top (220) to bottom (0)
            alpha = int(220 * (1 - y / gradient_height))
            color_with_alpha = gradient_color + (alpha,)
            draw = ImageDraw.Draw(gradient)
            draw.rectangle([(0, y), (width, y+1)], fill=color_with_alpha)
        
        # Paste gradient onto image
        img.paste(gradient, (0, 0), gradient)
        return img
    
    def _add_bottom_gradient(self, img, gradient_color):
        """Add bottom gradient overlay"""
        width, height = img.size
        
        # Create gradient overlay (bottom portion) - use configured height
        gradient_height = int(height * (self.gradient_height_percent / 100))
        gradient_y = height - gradient_height
        
        gradient = Image.new('RGBA', (width, gradient_height), (0, 0, 0, 0))
        
        # Draw gradient from transparent to solid
        for y in range(gradient_height):
            # Alpha increases from top (0) to bottom (220)
            alpha = int(220 * (y / gradient_height))
            color_with_alpha = gradient_color + (alpha,)
            draw = ImageDraw.Draw(gradient)
            draw.rectangle([(0, y), (width, y+1)], fill=color_with_alpha)
        
        # Paste gradient onto image
        img.paste(gradient, (0, gradient_y), gradient)
        return img
    
    def _add_logo(self, img, logo_img):
        """Add logo to image based on position"""
        width, height = img.size
        
        # Resize logo
        logo_height = int(height * (self.logo_size_percent / 100))
        logo_resized = self._resize_logo_to_height(logo_img, logo_height)
        logo_width = logo_resized.size[0]
        
        # Calculate logo position
        if self.logo_position == 'top-center':
            logo_x = (width - logo_width) // 2
            logo_y = self.padding
        elif self.logo_position == 'bottom-center':
            logo_x = (width - logo_width) // 2
            logo_y = height - logo_height - self.padding
        elif self.logo_position == 'top-left':
            logo_x = self.padding
            logo_y = self.padding
        elif self.logo_position == 'top-right':
            logo_x = width - logo_width - self.padding
            logo_y = self.padding
        elif self.logo_position == 'bottom-left':
            logo_x = self.padding
            logo_y = height - logo_height - self.padding
        elif self.logo_position == 'bottom-right':
            logo_x = width - logo_width - self.padding
            logo_y = height - logo_height - self.padding
        else:
            # Default: top-center
            logo_x = (width - logo_width) // 2
            logo_y = self.padding
        
        # Paste logo
        if logo_resized.mode == 'RGBA':
            img.paste(logo_resized, (logo_x, logo_y), logo_resized)
        else:
            img.paste(logo_resized, (logo_x, logo_y))
        
        # Company name removed - not shown on posts
        
        return img
    
    def _add_slogan(self, img, slogan):
        """Add slogan text to image based on position"""
        width, height = img.size
        
        draw = ImageDraw.Draw(img)
        font_size = int(height * (self.slogan_size_percent / 100))
        font = self._get_font(font_size)
        
        # Get text bounding box
        bbox = draw.textbbox((0, 0), slogan, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Center text horizontally
        text_x = (width - text_width) // 2
        
        # Position based on slogan_position
        if self.slogan_position == 'bottom-center':
            # Position in bottom gradient area
            gradient_height = int(height * 0.20)
            text_y = height - gradient_height // 2 - text_height // 2
        else:  # top-center
            # Position in top gradient area
            gradient_height = int(height * 0.25)
            text_y = gradient_height // 2 - text_height // 2
        
        # Draw slogan in white
        draw.text(
            (text_x, text_y),
            slogan,
            font=font,
            fill=(255, 255, 255, 255)
        )
        
        return img
    
    def _resize_logo_to_height(self, logo_img, target_height):
        """Resize logo to specific height maintaining aspect ratio"""
        original_width, original_height = logo_img.size
        aspect_ratio = original_width / original_height
        target_width = int(target_height * aspect_ratio)
        
        return logo_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
    
    def _get_font(self, size):
        """Get a nice sans-serif font"""
        # Try to find system fonts
        font_names = [
            'arial.ttf',
            'Arial.ttf',
            'helvetica.ttf',
            'Helvetica.ttf',
            'DejaVuSans.ttf',
            'SegoeUI.ttf',
            'segoeui.ttf',
        ]
        
        # Common font paths on different OS
        font_paths = [
            'C:/Windows/Fonts/',  # Windows
            '/usr/share/fonts/truetype/',  # Linux
            '/System/Library/Fonts/',  # macOS
            '/Library/Fonts/',  # macOS
        ]
        
        # Try to load a font
        for path in font_paths:
            for font_name in font_names:
                try:
                    font_path = os.path.join(path, font_name)
                    if os.path.exists(font_path):
                        return ImageFont.truetype(font_path, size)
                except:
                    continue
        
        # Fallback to default font
        try:
            return ImageFont.truetype("arial.ttf", size)
        except:
            # Last resort: default bitmap font
            return ImageFont.load_default()
    
    def save_branded_image(self, branded_image, format='PNG', quality=95):
        """
        Save branded image to a BytesIO object
        
        Args:
            branded_image: PIL Image object
            format: Image format (PNG, JPEG, etc.)
            quality: Quality for JPEG (1-100)
            
        Returns:
            BytesIO object containing the image data
        """
        output = io.BytesIO()
        
        if format.upper() == 'JPEG':
            # Convert to RGB if saving as JPEG (JPEG doesn't support transparency)
            if branded_image.mode in ('RGBA', 'LA', 'P'):
                rgb_image = Image.new('RGB', branded_image.size, (255, 255, 255))
                if branded_image.mode == 'P':
                    branded_image = branded_image.convert('RGBA')
                rgb_image.paste(branded_image, mask=branded_image.split()[3] if branded_image.mode == 'RGBA' else None)
                branded_image = rgb_image
            
            branded_image.save(output, format='JPEG', quality=quality, optimize=True)
        else:
            branded_image.save(output, format=format, optimize=True)
        
        output.seek(0)
        return output
    
    @staticmethod
    def apply_branding_to_file(company_profile, image_path_or_url, output_path=None):
        """
        Convenience method to apply branding and save to file
        
        Args:
            company_profile: CompanyProfile instance
            image_path_or_url: Path or URL to base image
            output_path: Where to save branded image (optional)
            
        Returns:
            Path to saved branded image or BytesIO if output_path is None
        """
        service = ImageBrandingService(company_profile)
        branded_img = service.apply_branding(image_path_or_url)
        
        if output_path:
            # Determine format from extension
            ext = Path(output_path).suffix.lower()
            format_map = {
                '.jpg': 'JPEG',
                '.jpeg': 'JPEG',
                '.png': 'PNG',
                '.webp': 'WEBP',
            }
            format = format_map.get(ext, 'PNG')
            
            # Save to file
            if format == 'JPEG':
                if branded_img.mode in ('RGBA', 'LA', 'P'):
                    rgb_image = Image.new('RGB', branded_img.size, (255, 255, 255))
                    if branded_img.mode == 'P':
                        branded_img = branded_img.convert('RGBA')
                    rgb_image.paste(branded_img, mask=branded_img.split()[3] if branded_img.mode == 'RGBA' else None)
                    branded_img = rgb_image
                branded_img.save(output_path, format='JPEG', quality=95, optimize=True)
            else:
                branded_img.save(output_path, format=format, optimize=True)
            
            return output_path
        else:
            # Return BytesIO
            return service.save_branded_image(branded_img)

