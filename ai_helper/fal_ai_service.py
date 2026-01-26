"""
Fal.ai Service
Image-to-Video and Image Editing using Fal.ai models
"""

import logging
from django.conf import settings
import time
import requests
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

# Try to import fal_client
try:
    from fal_client import submit, status, result, Completed, InProgress, Queued
    FAL_CLIENT_AVAILABLE = True
except ImportError as e:
    FAL_CLIENT_AVAILABLE = False
    submit = None
    status = None
    result = None
    Completed = None
    InProgress = None
    Queued = None
    logging.warning(f"fal_client paketi yuklu deyil: {e}")

# Try to import openai
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None
    logging.warning("openai paketi yuklu deyil")

logger = logging.getLogger(__name__)


class FalAIService:
    """Service for Fal.ai image-to-video and image editing"""
    
    def __init__(self, user=None):
        """Initialize Fal.ai service"""
        self.user = user
        self.api_key = getattr(settings, 'FAL_AI_API_KEY', None)
        
        if not FAL_CLIENT_AVAILABLE:
            raise ImportError("fal_client paketi yüklü deyil. Zəhmət olmasa install edin: pip install fal-client")
        
        if not self.api_key:
            logger.warning("Fal.ai API key not configured")
        else:
            # Set API key as environment variable for fal_client
            import os
            os.environ['FAL_KEY'] = self.api_key
            logger.info("Fal.ai service initialized")
    
    def image_to_video(self, image_url, prompt=None, duration=5, fps=24):
        """
        Convert image to video using fal-ai/kling-video/v2.6/pro/image-to-video
        
        Args:
            image_url: URL of the input image
            prompt: Optional text prompt describing the video motion
            duration: Video duration in seconds (default: 5)
            fps: Frames per second (default: 24)
        
        Returns:
            dict: {
                'video_url': str,
                'status': str,
                'job_id': str
            }
        """
        if not FAL_CLIENT_AVAILABLE:
            raise ImportError("fal_client paketi yüklü deyil. Zəhmət olmasa install edin: pip install fal-client")
            
        if not self.api_key:
            raise ValueError("Fal.ai API key not configured")
        
        logger.info(f"Converting image to video: {image_url}")
        
        try:
            # Prepare request payload
            payload = {
                "image_url": image_url,
                "duration": duration,
                "fps": fps,
            }
            
            if prompt:
                payload["prompt"] = prompt
            
            # Submit job to Fal.ai
            application = "fal-ai/kling-video/v2.6/pro/image-to-video"
            logger.info(f"Submitting job to {application}...")
            handle = submit(application, arguments=payload)
            
            job_id = handle.request_id
            logger.info(f"Job submitted: {job_id}")
            
            # Poll for result (video generation can take time)
            max_wait_time = 300  # 5 minutes max
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                status_obj = status(application, job_id)
                elapsed = int(time.time() - start_time)
                
                # Log every 10 seconds or on status change
                if elapsed % 10 == 0 or isinstance(status_obj, Completed):
                    status_type = type(status_obj).__name__
                    if isinstance(status_obj, Completed):
                        logger.info(f"Status check ({elapsed}s): Video generation COMPLETED!")
                    elif isinstance(status_obj, InProgress):
                        logger.info(f"Status check ({elapsed}s): Video generation in progress... (waiting for completion)")
                    elif isinstance(status_obj, Queued):
                        logger.info(f"Status check ({elapsed}s): Video generation queued, waiting to start...")
                    else:
                        logger.info(f"Status check ({elapsed}s): Status type={status_type}")
                
                if isinstance(status_obj, Completed):
                    result_data = result(application, job_id)
                    video_url = result_data.get('video', {}).get('url') if isinstance(result_data, dict) else result_data.get('video_url') if hasattr(result_data, 'get') else None
                    if not video_url and isinstance(result_data, dict):
                        video_url = result_data.get('video_url')
                    
                    if video_url:
                        logger.info(f"Video generated: {video_url}")
                        return {
                            'video_url': video_url,
                            'status': 'completed',
                            'job_id': job_id
                        }
                    else:
                        logger.error(f"Video URL not found in result: {result_data}")
                        raise ValueError("Video URL not found in API response")
                
                # If not Completed, continue polling (InProgress or Queued)
                # Failed status will raise exception from status() call
                
                # Wait before next poll
                time.sleep(2)
                logger.debug(f"Waiting for video generation... ({int(time.time() - start_time)}s)")
            
            # Timeout
            raise TimeoutError("Video generation timed out")
            
        except Exception as e:
            logger.error(f"Fal.ai image-to-video error: {e}", exc_info=True)
            raise
    
    def edit_image(self, image_url, prompt, strength=0.8):
        """
        Edit image using fal-ai/nano-banana-pro/edit
        
        Args:
            image_url: URL of the input image
            prompt: Text prompt describing the desired edits
            strength: Edit strength (0.0 to 1.0, default: 0.8)
        
        Returns:
            dict: {
                'image_url': str,
                'status': str,
                'job_id': str
            }
        """
        if not FAL_CLIENT_AVAILABLE:
            raise ImportError("fal_client paketi yüklü deyil. Zəhmət olmasa install edin: pip install fal-client")
            
        if not self.api_key:
            raise ValueError("Fal.ai API key not configured")
        
        logger.info(f"Editing image: {image_url}")
        logger.info(f"   Prompt: {prompt}")
        
        try:
            # Prepare request payload
            # Fal.ai API requires image_urls as a list
            payload = {
                "image_urls": [image_url],  # Must be a list
                "prompt": prompt,
                "strength": strength,
            }
            
            # Submit job to Fal.ai
            application = "fal-ai/nano-banana-pro/edit"
            logger.info(f"Submitting job to {application}...")
            handle = submit(application, arguments=payload)
            
            job_id = handle.request_id
            logger.info(f"Job submitted: {job_id}")
            
            # Poll for result
            max_wait_time = 30  # 30 seconds max (reduced for faster failure)
            start_time = time.time()
            last_log_time = 0
            poll_interval = 2  # Check every 2 seconds (reduced frequency)
            
            while time.time() - start_time < max_wait_time:
                try:
                    status_obj = status(application, job_id)
                    elapsed = int(time.time() - start_time)
                    
                    # Better status detection
                    is_completed = isinstance(status_obj, Completed)
                    status_type = type(status_obj).__name__
                    
                    # Log every 10 seconds or on status change
                    if elapsed - last_log_time >= 10 or is_completed:
                        logger.info(f"Status check ({elapsed}s): type={status_type}, is Completed={is_completed}")
                        # Debug: log status object attributes
                        if hasattr(status_obj, '__dict__'):
                            logger.debug(f"Status object: {status_obj.__dict__}")
                        last_log_time = elapsed
                    
                    # Check if completed by multiple methods
                    if is_completed or (hasattr(status_obj, 'status') and status_obj.status == 'completed'):
                        result_data = result(application, job_id)
                        image_url = None
                        if isinstance(result_data, dict):
                            image_url = result_data.get('image', {}).get('url') if isinstance(result_data.get('image'), dict) else result_data.get('image_url') or result_data.get('url')
                        elif hasattr(result_data, 'get'):
                            image_url = result_data.get('image_url') or result_data.get('url')
                        
                        if image_url:
                            logger.info(f"✅ Image edited: {image_url}")
                            return {
                                'image_url': image_url,
                                'status': 'completed',
                                'job_id': job_id
                            }
                        else:
                            logger.error(f"Image URL not found in result: {result_data}")
                            raise ValueError("Image URL not found in API response")
                    
                    # Check for failed status
                    if hasattr(status_obj, 'status') and status_obj.status == 'failed':
                        raise Exception(f"Fal.ai job failed: {getattr(status_obj, 'error', 'Unknown error')}")
                    
                    # If not Completed, continue polling (InProgress or Queued)
                    # Wait before next poll
                    time.sleep(poll_interval)
                    
                except Exception as status_error:
                    # If status check fails, log and continue for a bit, then fail
                    elapsed = int(time.time() - start_time)
                    logger.warning(f"Status check error at {elapsed}s: {str(status_error)}")
                    if elapsed > 15:  # If we've been waiting more than 15s and getting errors, fail faster
                        raise TimeoutError(f"Fal.ai status check failed after {elapsed}s: {str(status_error)}")
                    time.sleep(poll_interval)
            
            # Timeout
            raise TimeoutError(f"Image editing timed out after {max_wait_time} seconds")
            
        except Exception as e:
            logger.error(f"Fal.ai image edit error: {e}", exc_info=True)
            raise
    
    def enhance_prompt(self, user_prompt, product_name=None, product_description=None, context="ad_creative"):
        """
        Enhance user prompt to be more professional and detailed for AI models
        
        Args:
            user_prompt: User's original prompt
            product_name: Optional product name for context
            product_description: Optional product description for context
            context: Context type - "ad_creative" or "video"
        
        Returns:
            str: Enhanced professional prompt
        """
        try:
            if not OPENAI_AVAILABLE:
                logger.warning("OpenAI paketi yuklu deyil, using original prompt")
                return user_prompt
                
            openai_api_key = getattr(settings, 'OPENAI_API_KEY', None)
            if not openai_api_key:
                logger.warning("OpenAI API key not configured, using original prompt")
                return user_prompt
            
            client = openai.OpenAI(api_key=openai_api_key)
            
            # Build context
            context_info = ""
            if product_name:
                context_info += f"Product/Service: {product_name}\n"
            if product_description:
                context_info += f"Description: {product_description}\n"
            
            if context == "ad_creative":
                system_message = """You are a professional marketing and advertising expert. 
Transform user prompts into detailed, professional prompts for AI image generation models.

Your task:
- Enhance the prompt with professional marketing terminology
- Add visual details (lighting, composition, style, mood)
- Include technical photography/design terms
- Make it specific and actionable
- Keep the core intent of the user's request
- Output ONLY the enhanced prompt, no explanations"""
                
                user_message = f"""Transform this user prompt into a professional, detailed prompt for AI image generation:

{context_info}
User Prompt: {user_prompt}

Create a professional marketing/advertising prompt that includes:
- Visual style and composition
- Lighting and mood
- Color palette suggestions
- Professional photography/design terms
- Marketing appeal elements

Output ONLY the enhanced prompt."""
            else:  # video
                system_message = """You are a professional video production expert.
Transform user prompts into detailed, professional prompts for AI video generation models.

Your task:
- Enhance the prompt with professional video terminology
- Add motion and cinematic details
- Include camera movement, transitions, pacing
- Make it specific and actionable
- Keep the core intent of the user's request
- Output ONLY the enhanced prompt, no explanations"""
                
                user_message = f"""Transform this user prompt into a professional, detailed prompt for AI video generation:

{context_info}
User Prompt: {user_prompt}

Create a professional video production prompt that includes:
- Camera movement and angles
- Motion and transitions
- Cinematic style and pacing
- Visual effects and atmosphere
- Professional video terminology

Output ONLY the enhanced prompt."""
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            enhanced_prompt = response.choices[0].message.content.strip()
            enhanced_prompt = enhanced_prompt.strip('"\'')
            
            logger.info(f"Prompt enhanced: {len(user_prompt)} -> {len(enhanced_prompt)} chars")
            logger.debug(f"   Original: {user_prompt}")
            logger.debug(f"   Enhanced: {enhanced_prompt}")
            
            return enhanced_prompt
            
        except Exception as e:
            logger.warning(f"Failed to enhance prompt: {e}, using original")
            return user_prompt
    
    def text_to_image(self, prompt, width=1024, height=1024, num_images=1):
        """
        Generate image from text using fal-ai/nano-banana
        
        Args:
            prompt: Text prompt describing the image
            width: Image width (default: 1024)
            height: Image height (default: 1024)
            num_images: Number of images to generate (default: 1)
        
        Returns:
            dict: {
                'image_url': str or list of str,
                'status': str,
                'job_id': str
            }
        """
        if not FAL_CLIENT_AVAILABLE:
            raise ImportError("fal_client paketi yüklü deyil. Zəhmət olmasa install edin: pip install fal-client")
            
        if not self.api_key:
            raise ValueError("Fal.ai API key not configured")
        
        logger.info(f"Generating image from text: {prompt[:50]}...")
        
        try:
            payload = {
                "prompt": prompt,
                "width": width,
                "height": height,
                "num_images": num_images,
            }
            
            application = "fal-ai/nano-banana"
            logger.info(f"Submitting job to {application}...")
            handle = submit(application, arguments=payload)
            
            job_id = handle.request_id
            logger.info(f"Job submitted: {job_id}")
            
            # Poll for result
            max_wait_time = 120  # 2 minutes max
            start_time = time.time()
            last_log_time = 0
            
            while time.time() - start_time < max_wait_time:
                status_obj = status(application, job_id)
                elapsed = int(time.time() - start_time)
                
                # Log every 10 seconds or on status change
                if elapsed - last_log_time >= 10 or isinstance(status_obj, Completed):
                    logger.info(f"Status check ({elapsed}s): type={type(status_obj).__name__}, is Completed={isinstance(status_obj, Completed)}")
                    last_log_time = elapsed
                
                if isinstance(status_obj, Completed):
                    result_data = result(application, job_id)
                    
                    # Handle different response formats
                    image_url = None
                    if isinstance(result_data, dict):
                        if 'images' in result_data:
                            images = result_data['images']
                            if isinstance(images, list) and len(images) > 0:
                                image_url = images[0].get('url') if isinstance(images[0], dict) else images[0]
                            else:
                                image_url = images.get('url') if isinstance(images, dict) else images
                        elif 'image' in result_data:
                            image_url = result_data['image'].get('url') if isinstance(result_data['image'], dict) else result_data['image']
                        elif 'url' in result_data:
                            image_url = result_data['url']
                    
                    if image_url:
                        logger.info(f"Image generated: {image_url}")
                        return {
                            'image_url': image_url,
                            'status': 'completed',
                            'job_id': job_id
                        }
                    else:
                        logger.error(f"Image URL not found in result: {result_data}")
                        raise ValueError("Image URL not found in API response")
                
                # If not Completed, continue polling (InProgress or Queued)
                # Failed status will raise exception from status() call
                
                # Wait before next poll
                time.sleep(1)
                logger.debug(f"Waiting for image generation... ({int(time.time() - start_time)}s)")
            
            # Timeout
            raise TimeoutError("Image generation timed out")
            
        except Exception as e:
            logger.error(f"Fal.ai text-to-image error: {e}", exc_info=True)
            raise
    
    def image_to_image(self, image_url, prompt, strength=0.8):
        """
        Transform image using fal-ai/nano-banana (image-to-image)
        
        Args:
            image_url: URL of the input image
            prompt: Text prompt describing the transformation
            strength: Transformation strength (0.0 to 1.0, default: 0.8)
        
        Returns:
            dict: {
                'image_url': str,
                'status': str,
                'job_id': str
            }
        """
        if not FAL_CLIENT_AVAILABLE:
            raise ImportError("fal_client paketi yüklü deyil. Zəhmət olmasa install edin: pip install fal-client")
            
        if not self.api_key:
            raise ValueError("Fal.ai API key not configured")
        
        logger.info(f"Transforming image: {image_url}")
        logger.info(f"   Prompt: {prompt}")
        
        try:
            payload = {
                "image_url": image_url,
                "prompt": prompt,
                "strength": strength,
            }
            
            application = "fal-ai/nano-banana"
            logger.info(f"Submitting job to {application} (image-to-image)...")
            handle = submit(application, arguments=payload)
            
            job_id = handle.request_id
            logger.info(f"Job submitted: {job_id}")
            
            # Poll for result
            max_wait_time = 120  # 2 minutes max
            start_time = time.time()
            last_log_time = 0
            
            while time.time() - start_time < max_wait_time:
                status_obj = status(application, job_id)
                elapsed = int(time.time() - start_time)
                
                # Log every 10 seconds or on status change
                if elapsed - last_log_time >= 10 or isinstance(status_obj, Completed):
                    logger.info(f"Status check ({elapsed}s): type={type(status_obj).__name__}, is Completed={isinstance(status_obj, Completed)}")
                    last_log_time = elapsed
                
                if isinstance(status_obj, Completed):
                    result_data = result(application, job_id)
                    
                    # Handle different response formats
                    image_url = None
                    if isinstance(result_data, dict):
                        if 'images' in result_data:
                            images = result_data['images']
                            if isinstance(images, list) and len(images) > 0:
                                image_url = images[0].get('url') if isinstance(images[0], dict) else images[0]
                            else:
                                image_url = images.get('url') if isinstance(images, dict) else images
                        elif 'image' in result_data:
                            image_url = result_data['image'].get('url') if isinstance(result_data['image'], dict) else result_data['image']
                        elif 'url' in result_data:
                            image_url = result_data['url']
                    
                    if image_url:
                        logger.info(f"Image transformed: {image_url}")
                        return {
                            'image_url': image_url,
                            'status': 'completed',
                            'job_id': job_id
                        }
                    else:
                        logger.error(f"Image URL not found in result: {result_data}")
                        raise ValueError("Image URL not found in API response")
                
                # If not Completed, continue polling (InProgress or Queued)
                # Failed status will raise exception from status() call
                
                # Wait before next poll
                time.sleep(1)
                logger.debug(f"Waiting for image transformation... ({int(time.time() - start_time)}s)")
            
            # Timeout
            raise TimeoutError("Image transformation timed out")
            
        except Exception as e:
            logger.error(f"Fal.ai image-to-image error: {e}", exc_info=True)
            raise
    
    def text_to_video(self, prompt, duration=5, fps=24, width=1024, height=576):
        """
        Generate video from text using fal-ai/kling-video
        
        Args:
            prompt: Text prompt describing the video
            duration: Video duration in seconds (default: 5)
            fps: Frames per second (default: 24)
            width: Video width (default: 1024)
            height: Video height (default: 576)
        
        Returns:
            dict: {
                'video_url': str,
                'status': str,
                'job_id': str
            }
        """
        if not FAL_CLIENT_AVAILABLE:
            raise ImportError("fal_client paketi yüklü deyil. Zəhmət olmasa install edin: pip install fal-client")
            
        if not self.api_key:
            raise ValueError("Fal.ai API key not configured")
        
        logger.info(f"Generating video from text: {prompt[:50]}...")
        
        try:
            payload = {
                "prompt": prompt,
                "duration": duration,
                "fps": fps,
                "width": width,
                "height": height,
            }
            
            application = "fal-ai/kling-video"
            logger.info(f"Submitting job to {application}...")
            handle = submit(application, arguments=payload)
            
            job_id = handle.request_id
            logger.info(f"Job submitted: {job_id}")
            
            # Poll for result (video generation can take time)
            max_wait_time = 300  # 5 minutes max
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                status_obj = status(application, job_id)
                elapsed = int(time.time() - start_time)
                
                # Log every 10 seconds or on status change
                if elapsed % 10 == 0 or isinstance(status_obj, Completed):
                    status_type = type(status_obj).__name__
                    if isinstance(status_obj, Completed):
                        logger.info(f"Status check ({elapsed}s): Video generation COMPLETED!")
                    elif isinstance(status_obj, InProgress):
                        logger.info(f"Status check ({elapsed}s): Video generation in progress... (waiting for completion)")
                    elif isinstance(status_obj, Queued):
                        logger.info(f"Status check ({elapsed}s): Video generation queued, waiting to start...")
                    else:
                        logger.info(f"Status check ({elapsed}s): Status type={status_type}")
                
                if isinstance(status_obj, Completed):
                    result_data = result(application, job_id)
                    video_url = None
                    if isinstance(result_data, dict):
                        video_url = result_data.get('video', {}).get('url') if isinstance(result_data.get('video'), dict) else result_data.get('video_url') or result_data.get('url')
                    
                    if video_url:
                        logger.info(f"Video generated: {video_url}")
                        return {
                            'video_url': video_url,
                            'status': 'completed',
                            'job_id': job_id
                        }
                    else:
                        logger.error(f"Video URL not found in result: {result_data}")
                        raise ValueError("Video URL not found in API response")
                
                # If not Completed, continue polling (InProgress or Queued)
                # Failed status will raise exception from status() call
                
                # Wait before next poll
                time.sleep(2)
                logger.debug(f"Waiting for video generation... ({int(time.time() - start_time)}s)")
            
            # Timeout
            raise TimeoutError("Video generation timed out")
            
        except Exception as e:
            logger.error(f"Fal.ai text-to-video error: {e}", exc_info=True)
            raise
    
    def download_and_save(self, url, user_id, prefix="fal_ai"):
        """
        Download file from URL and save to Django storage
        
        Args:
            url: URL of the file to download
            user_id: User ID for organizing files
            prefix: File prefix (default: "fal_ai")
        
        Returns:
            str: URL of saved file
        """
        try:
            logger.info(f"Downloading file: {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Determine file extension from content type or URL
            content_type = response.headers.get('content-type', '')
            if 'video' in content_type or url.endswith('.mp4'):
                ext = 'mp4'
            elif 'image' in content_type or url.endswith(('.png', '.jpg', '.jpeg')):
                ext = 'png' if 'png' in content_type or url.endswith('.png') else 'jpg'
            else:
                ext = 'mp4' if 'video' in url else 'png'
            
            # Save to storage
            filename = f"{prefix}/user_{user_id}_{int(time.time())}.{ext}"
            file_content = ContentFile(response.content)
            path = default_storage.save(filename, file_content)
            saved_url = default_storage.url(path)
            
            logger.info(f"File saved: {saved_url}")
            return saved_url
            
        except Exception as e:
            logger.error(f"Error downloading/saving file: {e}", exc_info=True)
            raise

