"""
AI service for image generation and editing
Handles integration with Hugging Face and other AI providers
"""

import os
import requests
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from app.core.config import get_config
from app.core.exceptions import AIServiceError, ValidationError
from app.core.utils import sanitize_prompt


class AIService:
    """Service for AI-powered image operations"""
    
    def __init__(self):
        self.config = get_config()
        self.api_token = self.config.HF_API_TOKEN
        self.model = self.config.HF_MODEL
        self.max_retries = self.config.AI_MAX_RETRIES
    
    def generate_image(self, prompt: str, width: int = 512, height: int = 512, 
                      steps: int = 30) -> str:
        """Generate image from text prompt"""
        if not self.api_token:
            raise AIServiceError("Hugging Face API token not configured")
        
        # Validate and sanitize prompt
        prompt = sanitize_prompt(prompt)
        if not prompt:
            raise ValidationError("Valid prompt is required")
        
        # Validate dimensions
        if not (256 <= width <= 1024 and 256 <= height <= 1024):
            raise ValidationError("Image dimensions must be between 256 and 1024 pixels")
        
        # Validate steps
        if not (10 <= steps <= 100):
            raise ValidationError("Steps must be between 10 and 100")
        
        try:
            # Prepare API request
            model_url = f"https://api-inference.huggingface.co/models/{self.model}"
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "num_inference_steps": steps,
                    "width": width,
                    "height": height,
                    "guidance_scale": 7.5,
                    "negative_prompt": "blurry, low quality, distorted, deformed"
                }
            }
            
            # Make API request with retries
            response = self._make_request_with_retry(model_url, headers, payload)
            
            # Save generated image
            output_filename = f"generated_{uuid.uuid4().hex[:12]}.jpg"
            output_path = self.config.get_processed_path(output_filename)
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            return output_filename
            
        except requests.RequestException as e:
            raise AIServiceError(f"API request failed: {str(e)}", "huggingface")
        except Exception as e:
            raise AIServiceError(f"Image generation failed: {str(e)}")
    
    def edit_image(self, source_path: str, prompt: str, strength: float = 0.75, 
                   steps: int = 30) -> str:
        """Edit existing image using AI"""
        if not self.api_token:
            raise AIServiceError("Hugging Face API token not configured")
        
        if not os.path.exists(source_path):
            raise ValidationError(f"Source image not found: {source_path}")
        
        # Validate and sanitize prompt
        prompt = sanitize_prompt(prompt)
        if not prompt:
            raise ValidationError("Valid prompt is required")
        
        # Validate parameters
        if not (0.1 <= strength <= 1.0):
            raise ValidationError("Strength must be between 0.1 and 1.0")
        
        if not (10 <= steps <= 100):
            raise ValidationError("Steps must be between 10 and 100")
        
        try:
            # For image-to-image, we'll use a simpler approach
            # In production, you'd want to use specific img2img models
            model_url = f"https://api-inference.huggingface.co/models/{self.model}"
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            # Read source image
            with open(source_path, 'rb') as f:
                image_data = f.read()
            
            # For now, we'll treat this as text-to-image with the prompt
            # In a more advanced setup, you'd send the image data as well
            payload = {
                "inputs": f"{prompt}, based on uploaded image",
                "parameters": {
                    "num_inference_steps": steps,
                    "strength": strength,
                    "guidance_scale": 7.5
                }
            }
            
            # Make API request with retries
            response = self._make_request_with_retry(model_url, headers, payload)
            
            # Save edited image
            base_name = os.path.splitext(os.path.basename(source_path))[0]
            output_filename = f"{base_name}_ai_edit_{uuid.uuid4().hex[:8]}.jpg"
            output_path = self.config.get_processed_path(output_filename)
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            return output_filename
            
        except requests.RequestException as e:
            raise AIServiceError(f"API request failed: {str(e)}", "huggingface")
        except Exception as e:
            raise AIServiceError(f"Image editing failed: {str(e)}")
    
    def _make_request_with_retry(self, url: str, headers: Dict, payload: Dict) -> requests.Response:
        """Make API request with retry logic"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=120)
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 503:
                    # Model is loading, wait and retry
                    if attempt < self.max_retries:
                        import time
                        time.sleep(10 * (attempt + 1))  # Exponential backoff
                        continue
                    else:
                        raise AIServiceError("Model is still loading after retries", status_code=503)
                else:
                    raise AIServiceError(f"API returned status {response.status_code}", status_code=response.status_code)
                    
            except requests.Timeout as e:
                last_exception = e
                if attempt < self.max_retries:
                    continue
            except requests.RequestException as e:
                last_exception = e
                if attempt < self.max_retries:
                    continue
        
        # If we get here, all retries failed
        raise AIServiceError(f"All retry attempts failed: {str(last_exception)}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current AI model"""
        return {
            'model': self.model,
            'provider': 'huggingface',
            'configured': bool(self.api_token),
            'max_retries': self.max_retries
        }
    
    def validate_generation_params(self, width: int, height: int, steps: int) -> bool:
        """Validate image generation parameters"""
        try:
            return (256 <= width <= 1024 and 
                   256 <= height <= 1024 and 
                   10 <= steps <= 100)
        except (ValueError, TypeError):
            return False
    
    def validate_editing_params(self, strength: float, steps: int) -> bool:
        """Validate image editing parameters"""
        try:
            return (0.1 <= strength <= 1.0 and 
                   10 <= steps <= 100)
        except (ValueError, TypeError):
            return False
    
    def get_suggested_prompts(self, category: str = None) -> Dict[str, list]:
        """Get suggested prompts for different categories"""
        prompts = {
            'nature': [
                'A serene mountain landscape at sunset with vibrant colors',
                'Tropical beach with crystal clear water and palm trees',
                'Mystical forest with glowing mushrooms and fireflies',
                'Northern lights over a snowy landscape'
            ],
            'abstract': [
                'Colorful geometric shapes floating in space',
                'Swirling galaxy with nebula clouds',
                'Abstract digital art with neon colors',
                'Fractal patterns with metallic textures'
            ],
            'fantasy': [
                'Magical floating castle in the clouds',
                'Dragon flying over medieval village',
                'Enchanted garden with glowing flowers',
                'Crystal cave with bioluminescent plants'
            ],
            'sci_fi': [
                'Futuristic cityscape with flying vehicles',
                'Space station orbiting an alien planet',
                'Cyberpunk street with neon signs',
                'Robot in a high-tech laboratory'
            ],
            'objects': [
                'Nano banana - a tiny banana with intricate details',
                'Miniature city built inside a coffee cup',
                'Elaborate cake with impossible architecture',
                'Jeweled crown with magical properties'
            ]
        }
        
        if category and category in prompts:
            return {category: prompts[category]}
        
        return prompts
