"""
Image processing service
Handles all image manipulation operations
"""

import os
import json
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from typing import Dict, Any, Optional, Tuple
import uuid

from app.core.config import get_config
from app.core.exceptions import ProcessingError, ValidationError
from app.core.utils import validate_coordinates


class ImageProcessorService:
    """Service for image processing operations"""
    
    def __init__(self):
        self.config = get_config()
    
    def process_image(self, source_path: str, operation: str, parameters: Dict[str, Any]) -> str:
        """Process image with given operation and parameters"""
        try:
            if not os.path.exists(source_path):
                raise ProcessingError(f"Source image not found: {source_path}")
            
            # Open and prepare image
            with Image.open(source_path) as img:
                # Convert to RGB if necessary for JPEG compatibility
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Apply operation
                processed_img = self._apply_operation(img, operation, parameters)
                
                # Generate output filename
                base_name = os.path.splitext(os.path.basename(source_path))[0]
                output_filename = f"{base_name}_{operation}_{uuid.uuid4().hex[:8]}.jpg"
                output_path = self.config.get_processed_path(output_filename)
                
                # Save processed image
                processed_img.save(output_path, 'JPEG', quality=self.config.JPEG_QUALITY)
                
                return output_filename
                
        except Exception as e:
            raise ProcessingError(f"Image processing failed: {str(e)}", operation)
    
    def _apply_operation(self, img: Image.Image, operation: str, params: Dict[str, Any]) -> Image.Image:
        """Apply specific image operation"""
        
        if operation == 'resize':
            return self._resize_image(img, params)
        elif operation == 'rotate':
            return self._rotate_image(img, params)
        elif operation in ('flip_horizontal', 'flip_h'):
            return img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        elif operation in ('flip_vertical', 'flip_v'):
            return img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        elif operation == 'crop':
            return self._crop_image(img, params)
        elif operation == 'brightness':
            return self._adjust_brightness(img, params)
        elif operation == 'contrast':
            return self._adjust_contrast(img, params)
        elif operation == 'saturation':
            return self._adjust_saturation(img, params)
        elif operation == 'sharpness':
            return self._adjust_sharpness(img, params)
        elif operation == 'blur':
            return self._blur_image(img, params)
        elif operation == 'sharpen':
            return img.filter(ImageFilter.SHARPEN)
        elif operation == 'emboss':
            return img.filter(ImageFilter.EMBOSS)
        elif operation == 'edges':
            return img.filter(ImageFilter.FIND_EDGES)
        elif operation == 'smooth':
            return img.filter(ImageFilter.SMOOTH)
        elif operation == 'grayscale':
            return ImageOps.grayscale(img).convert('RGB')
        elif operation == 'sepia':
            return self._sepia_effect(img)
        elif operation == 'invert':
            return ImageOps.invert(img)
        elif operation == 'posterize':
            return self._posterize_image(img, params)
        elif operation == 'solarize':
            return self._solarize_image(img, params)
        elif operation == 'enhance':
            return self._auto_enhance(img)
        else:
            raise ProcessingError(f"Unknown operation: {operation}")
    
    def _resize_image(self, img: Image.Image, params: Dict[str, Any]) -> Image.Image:
        """Resize image to specified dimensions"""
        width = params.get('width')
        height = params.get('height')
        
        if not width or not height:
            raise ValidationError("Width and height required for resize operation")
        
        width, height = int(width), int(height)
        
        if width <= 0 or height <= 0:
            raise ValidationError("Width and height must be positive")
        
        if width > self.config.MAX_IMAGE_DIMENSION or height > self.config.MAX_IMAGE_DIMENSION:
            raise ValidationError(f"Dimensions exceed maximum allowed: {self.config.MAX_IMAGE_DIMENSION}")
        
        return img.resize((width, height), Image.Resampling.LANCZOS)
    
    def _rotate_image(self, img: Image.Image, params: Dict[str, Any]) -> Image.Image:
        """Rotate image by specified angle"""
        angle = float(params.get('value', 90))
        return img.rotate(angle, expand=True, fillcolor='white')
    
    def _crop_image(self, img: Image.Image, params: Dict[str, Any]) -> Image.Image:
        """Crop image using coordinates"""
        width = params.get('width')
        height = params.get('height')
        value = params.get('value')
        
        if width and height and value:
            try:
                # Parse coordinates from value parameter
                coords = json.loads(value) if isinstance(value, str) else value
                x = int(coords.get('x', 0))
                y = int(coords.get('y', 0))
                w = int(width)
                h = int(height)
                
                # Validate coordinates
                if not validate_coordinates(x, y, w, h, img.width, img.height):
                    raise ValidationError("Invalid crop coordinates")
                
                return img.crop((x, y, x + w, y + h))
                
            except (json.JSONDecodeError, ValueError, KeyError):
                pass
        
        # Fallback to center square crop
        img_width, img_height = img.size
        size = min(img_width, img_height)
        left = (img_width - size) // 2
        top = (img_height - size) // 2
        return img.crop((left, top, left + size, top + size))
    
    def _adjust_brightness(self, img: Image.Image, params: Dict[str, Any]) -> Image.Image:
        """Adjust image brightness"""
        factor = float(params.get('value', 1.2))
        factor = max(0.1, min(3.0, factor))  # Clamp between 0.1 and 3.0
        enhancer = ImageEnhance.Brightness(img)
        return enhancer.enhance(factor)
    
    def _adjust_contrast(self, img: Image.Image, params: Dict[str, Any]) -> Image.Image:
        """Adjust image contrast"""
        factor = float(params.get('value', 1.2))
        factor = max(0.1, min(3.0, factor))  # Clamp between 0.1 and 3.0
        enhancer = ImageEnhance.Contrast(img)
        return enhancer.enhance(factor)
    
    def _adjust_saturation(self, img: Image.Image, params: Dict[str, Any]) -> Image.Image:
        """Adjust image saturation"""
        factor = float(params.get('value', 1.2))
        factor = max(0.0, min(3.0, factor))  # Clamp between 0.0 and 3.0
        enhancer = ImageEnhance.Color(img)
        return enhancer.enhance(factor)
    
    def _adjust_sharpness(self, img: Image.Image, params: Dict[str, Any]) -> Image.Image:
        """Adjust image sharpness"""
        factor = float(params.get('value', 1.2))
        factor = max(0.0, min(3.0, factor))  # Clamp between 0.0 and 3.0
        enhancer = ImageEnhance.Sharpness(img)
        return enhancer.enhance(factor)
    
    def _blur_image(self, img: Image.Image, params: Dict[str, Any]) -> Image.Image:
        """Apply blur filter to image"""
        radius = float(params.get('value', 2.0))
        radius = max(0.1, min(10.0, radius))  # Clamp between 0.1 and 10.0
        return img.filter(ImageFilter.GaussianBlur(radius=radius))
    
    def _sepia_effect(self, img: Image.Image) -> Image.Image:
        """Apply sepia effect to image"""
        grayscale = ImageOps.grayscale(img)
        return ImageOps.colorize(grayscale, '#704214', '#C0A080')
    
    def _posterize_image(self, img: Image.Image, params: Dict[str, Any]) -> Image.Image:
        """Apply posterize effect"""
        bits = int(params.get('value', 4))
        bits = max(1, min(8, bits))  # Clamp between 1 and 8
        return ImageOps.posterize(img, bits)
    
    def _solarize_image(self, img: Image.Image, params: Dict[str, Any]) -> Image.Image:
        """Apply solarize effect"""
        threshold = int(params.get('value', 128))
        threshold = max(0, min(255, threshold))  # Clamp between 0 and 255
        return ImageOps.solarize(img, threshold)
    
    def _auto_enhance(self, img: Image.Image) -> Image.Image:
        """Apply automatic enhancement (brightness + contrast)"""
        # Slight brightness boost
        enhancer1 = ImageEnhance.Brightness(img)
        enhanced = enhancer1.enhance(1.1)
        
        # Slight contrast boost
        enhancer2 = ImageEnhance.Contrast(enhanced)
        return enhancer2.enhance(1.1)
    
    def get_image_info(self, image_path: str) -> Dict[str, Any]:
        """Get information about an image"""
        try:
            with Image.open(image_path) as img:
                return {
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode,
                    'size': os.path.getsize(image_path)
                }
        except Exception as e:
            raise ProcessingError(f"Failed to get image info: {str(e)}")
    
    def validate_operation_params(self, operation: str, params: Dict[str, Any]) -> bool:
        """Validate parameters for specific operation"""
        try:
            if operation == 'resize':
                width = int(params.get('width', 0))
                height = int(params.get('height', 0))
                return width > 0 and height > 0 and width <= self.config.MAX_IMAGE_DIMENSION and height <= self.config.MAX_IMAGE_DIMENSION
            
            elif operation == 'crop':
                width = int(params.get('width', 0))
                height = int(params.get('height', 0))
                return width > 0 and height > 0
            
            elif operation in ['brightness', 'contrast', 'saturation', 'sharpness']:
                value = float(params.get('value', 1.0))
                return 0.1 <= value <= 3.0
            
            elif operation == 'blur':
                value = float(params.get('value', 1.0))
                return 0.1 <= value <= 10.0
            
            elif operation == 'posterize':
                value = int(params.get('value', 4))
                return 1 <= value <= 8
            
            elif operation == 'solarize':
                value = int(params.get('value', 128))
                return 0 <= value <= 255
            
            elif operation == 'rotate':
                # Validate rotation angle
                value = float(params.get('value', 90))
                return -360 <= value <= 360
            
            # Operations without parameters
            elif operation in ['flip_horizontal', 'flip_vertical', 'sharpen', 'emboss', 
                             'edges', 'smooth', 'grayscale', 'sepia', 'invert', 'enhance']:
                return True
            
            return False
            
        except (ValueError, TypeError):
            return False
