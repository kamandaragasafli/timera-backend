"""
Supabase Storage Upload Service
Handles image uploads to Supabase Storage
"""

import uuid
import requests
import logging
from django.conf import settings
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)


class SupabaseUploadService:
    """Service for uploading images to Supabase Storage"""
    
    def __init__(self):
        """Initialize Supabase upload service with credentials"""
        self.supabase_url = getattr(settings, 'SUPABASE_URL', None)
        self.supabase_service_key = getattr(settings, 'SUPABASE_SERVICE_ROLE_KEY', None)
        self.bucket_name = getattr(settings, 'SUPABASE_BUCKET', 'timera-media')
        self.folder = 'post_images/'
        
        if not self.supabase_url or not self.supabase_service_key:
            logger.warning("⚠️ Supabase credentials not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in settings.")
    
    def _get_content_type(self, image_path_or_bytes, filename=None):
        """
        Determine content type from file extension or image format
        
        Args:
            image_path_or_bytes: File path or bytes
            filename: Optional filename to determine extension
            
        Returns:
            Content-Type string (e.g., 'image/png', 'image/jpeg')
        """
        # If filename provided, use extension
        if filename:
            ext = filename.lower().split('.')[-1]
            content_types = {
                'png': 'image/png',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'webp': 'image/webp',
                'gif': 'image/gif'
            }
            if ext in content_types:
                return content_types[ext]
        
        # Try to determine from image bytes
        try:
            if isinstance(image_path_or_bytes, bytes):
                img = Image.open(BytesIO(image_path_or_bytes))
            else:
                img = Image.open(image_path_or_bytes)
            
            format_to_mime = {
                'PNG': 'image/png',
                'JPEG': 'image/jpeg',
                'WEBP': 'image/webp',
                'GIF': 'image/gif'
            }
            return format_to_mime.get(img.format, 'image/png')
        except Exception as e:
            logger.warning(f"Could not determine content type from image: {e}")
            return 'image/png'  # Default to PNG
    
    def upload_image(self, image_source, filename=None, content_type=None):
        """
        Upload image to Supabase Storage
        
        Args:
            image_source: Can be:
                - File path (str): Path to local image file
                - BytesIO: Image bytes
                - bytes: Raw image bytes
                - PIL Image: PIL Image object
            filename: Optional filename. If not provided, UUID will be used
            content_type: Optional content type. If not provided, will be auto-detected
            
        Returns:
            dict: {
                'success': bool,
                'url': str (public URL if successful),
                'error': str (error message if failed),
                'file_path': str (path in Supabase)
            }
        """
        if not self.supabase_url or not self.supabase_service_key:
            return {
                'success': False,
                'error': 'Supabase credentials not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in settings.',
                'url': None,
                'file_path': None
            }
        
        try:
            # Generate filename if not provided
            if not filename:
                filename = f"{uuid.uuid4()}.png"
            else:
                # Ensure filename has extension
                if '.' not in filename:
                    filename = f"{filename}.png"
            
            # Construct file path in Supabase
            file_path = f"{self.folder}{filename}"
            
            # Read image data
            image_bytes = None
            if isinstance(image_source, str):
                # File path
                with open(image_source, 'rb') as f:
                    image_bytes = f.read()
                if not content_type:
                    content_type = self._get_content_type(image_source, filename)
            elif isinstance(image_source, bytes):
                # Raw bytes
                image_bytes = image_source
                if not content_type:
                    content_type = self._get_content_type(image_bytes, filename)
            elif hasattr(image_source, 'read'):
                # BytesIO or file-like object
                image_bytes = image_source.read()
                if not content_type:
                    content_type = self._get_content_type(image_bytes, filename)
            elif hasattr(image_source, 'save'):
                # PIL Image
                buffer = BytesIO()
                image_source.save(buffer, format='PNG')
                image_bytes = buffer.getvalue()
                content_type = 'image/png'
            else:
                return {
                    'success': False,
                    'error': f'Unsupported image source type: {type(image_source)}',
                    'url': None,
                    'file_path': None
                }
            
            if not image_bytes:
                return {
                    'success': False,
                    'error': 'Could not read image data',
                    'url': None,
                    'file_path': None
                }
            
            # Upload to Supabase Storage
            # Use the correct endpoint for uploading files
            upload_url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}/{file_path}"
            
            headers = {
                'Authorization': f'Bearer {self.supabase_service_key}',
                'Content-Type': content_type,
                'x-upsert': 'true',  # Overwrite if exists
                'Cache-Control': 'public, max-age=31536000',  # Cache for 1 year
                # Ensure Supabase stores the content-type metadata
                'x-content-type': content_type
            }
            
            logger.info(f"📤 Uploading image to Supabase: {file_path} (Content-Type: {content_type})")
            
            try:
                response = requests.put(
                    upload_url,
                    data=image_bytes,
                    headers=headers,
                    timeout=30
                )
            except requests.exceptions.ConnectionError as e:
                error_msg = f"Supabase bağlantı xətası: DNS çözümlənmədi və ya internet bağlantısı yoxdur. Hostname: {self.supabase_url}"
                logger.error(f"❌ {error_msg}")
                logger.error(f"   Original error: {str(e)}")
                return {
                    'success': False,
                    'error': error_msg,
                    'url': None,
                    'file_path': file_path
                }
            except requests.exceptions.Timeout as e:
                error_msg = f"Supabase yükləmə zaman aşımı: 30 saniyə ərzində cavab alına bilmədi"
                logger.error(f"❌ {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'url': None,
                    'file_path': file_path
                }
            except Exception as e:
                error_msg = f"Supabase yükləmə xətası: {str(e)}"
                logger.error(f"❌ {error_msg}", exc_info=True)
                return {
                    'success': False,
                    'error': error_msg,
                    'url': None,
                    'file_path': file_path
                }
            
            if response.status_code not in [200, 201]:
                error_msg = f"Supabase upload failed: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', error_msg)
                except:
                    error_msg = response.text or error_msg
                
                logger.error(f"❌ {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'url': None,
                    'file_path': file_path
                }
            
            # Get public URL
            # Supabase public URL format: {supabase_url}/storage/v1/object/public/{bucket}/{path}
            public_url = f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{file_path}"
            
            logger.info(f"✅ Image uploaded successfully: {public_url}")
            
            return {
                'success': True,
                'url': public_url,
                'error': None,
                'file_path': file_path
            }
            
        except FileNotFoundError as e:
            error_msg = f"Image file not found: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'url': None,
                'file_path': None
            }
        except Exception as e:
            error_msg = f"Error uploading to Supabase: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return {
                'success': False,
                'error': error_msg,
                'url': None,
                'file_path': None
            }
    
    def get_image_bytes(self, image_url):
        """
        Download image from URL and return as bytes
        
        Args:
            image_url: Public URL of the image
            
        Returns:
            bytes: Image bytes, or None if failed
        """
        try:
            response = requests.get(image_url, timeout=30)
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"❌ Failed to download image from {image_url}: {response.status_code}")
                return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ DNS/Connection error downloading image from {image_url}: {str(e)}")
            return None
        except requests.exceptions.Timeout as e:
            logger.error(f"❌ Timeout downloading image from {image_url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Error downloading image from {image_url}: {str(e)}")
            return None


# Singleton instance
_upload_service = None

def get_upload_service():
    """Get singleton instance of SupabaseUploadService"""
    global _upload_service
    if _upload_service is None:
        _upload_service = SupabaseUploadService()
    return _upload_service


def upload_image_to_supabase(image_source, filename=None, content_type=None):
    """
    Convenience function to upload image to Supabase
    
    Args:
        image_source: Image source (file path, bytes, BytesIO, or PIL Image)
        filename: Optional filename
        content_type: Optional content type
        
    Returns:
        dict: Upload result with 'success', 'url', 'error', 'file_path'
    """
    service = get_upload_service()
    return service.upload_image(image_source, filename, content_type)

