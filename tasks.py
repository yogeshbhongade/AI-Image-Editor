import os
import uuid
from datetime import datetime
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import requests
from app import extensions
from app.config import Config
import tempfile
import json

def process_image_task(user_id, operation, filename, edit_status='temporary', processed=None, value=None, width=None, height=None, session_id=None, sequence=None):
    """Process basic image operations like resize, rotate, filters, etc."""
    try:
        # Determine source file path
        if processed:
            source_path = os.path.join(Config.PROCESSED_FOLDER, processed)
        else:
            source_path = os.path.join(Config.UPLOAD_FOLDER, filename)
        
        if not os.path.exists(source_path):
            return {'success': False, 'error': 'Source image not found'}
        
        # Open image
        with Image.open(source_path) as img:
            # Convert to RGB if necessary (for JPEG compatibility)
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Apply the requested operation
            processed_img = apply_image_operation(img, operation, value, width, height)
            
            # Generate output filename
            base_name = os.path.splitext(filename)[0]
            ext = '.jpg'  # Standardize to JPG for compatibility
            output_filename = f"{base_name}_{operation}_{uuid.uuid4().hex[:8]}{ext}"
            output_path = os.path.join(Config.PROCESSED_FOLDER, output_filename)
            
            # Save processed image
            processed_img.save(output_path, 'JPEG', quality=90)
            
            # Store in database
            doc = {
                'processed_filename': output_filename,
                'source_filename': filename,
                'operation': operation,
                'output_path': output_path,
                'created_by': user_id,
                'created_at': datetime.utcnow(),
                'session_id': session_id,
                'sequence': sequence,
                'edit_status': edit_status,
                'file_size': os.path.getsize(output_path),
                'parameters': {
                    'value': value,
                    'width': width,
                    'height': height
                }
            }
            
            result = extensions.db.processed.insert_one(doc)
            
            return {
                'success': True,
                'processed_filename': output_filename,
                'document_id': str(result.inserted_id),
                'operation': operation
            }
            
    except Exception as e:
        return {'success': False, 'error': f'Processing failed: {str(e)}'}

def apply_image_operation(img, operation, value, width, height):
    """Apply specific image operations"""
    
    if operation == 'resize':
        if width and height:
            return img.resize((int(width), int(height)), Image.Resampling.LANCZOS)
        return img
    
    elif operation == 'rotate':
        angle = float(value) if value else 90
        return img.rotate(angle, expand=True, fillcolor='white')
    
    elif operation == 'flip_horizontal':
        return img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    
    elif operation == 'flip_vertical':
        return img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    
    elif operation == 'brightness':
        enhancer = ImageEnhance.Brightness(img)
        factor = float(value) if value else 1.2
        return enhancer.enhance(factor)
    
    elif operation == 'contrast':
        enhancer = ImageEnhance.Contrast(img)
        factor = float(value) if value else 1.2
        return enhancer.enhance(factor)
    
    elif operation == 'saturation':
        enhancer = ImageEnhance.Color(img)
        factor = float(value) if value else 1.2
        return enhancer.enhance(factor)
    
    elif operation == 'sharpness':
        enhancer = ImageEnhance.Sharpness(img)
        factor = float(value) if value else 1.2
        return enhancer.enhance(factor)
    
    elif operation == 'blur':
        radius = float(value) if value else 2.0
        return img.filter(ImageFilter.GaussianBlur(radius=radius))
    
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
        grayscale = ImageOps.grayscale(img)
        sepia = ImageOps.colorize(grayscale, '#704214', '#C0A080')
        return sepia
    
    elif operation == 'invert':
        return ImageOps.invert(img)
    
    elif operation == 'posterize':
        bits = int(value) if value else 4
        return ImageOps.posterize(img, bits)
    
    elif operation == 'solarize':
        threshold = int(value) if value else 128
        return ImageOps.solarize(img, threshold)
    
    elif operation == 'crop':
        # For crop, we'd need coordinates. For now, crop center square
        width, height = img.size
        size = min(width, height)
        left = (width - size) // 2
        top = (height - size) // 2
        return img.crop((left, top, left + size, top + size))
    
    elif operation == 'enhance':
        # Auto enhance - combination of brightness and contrast
        enhancer1 = ImageEnhance.Brightness(img)
        enhanced = enhancer1.enhance(1.1)
        enhancer2 = ImageEnhance.Contrast(enhanced)
        return enhancer2.enhance(1.1)
    
    else:
        # Default: return original image
        return img

def process_ai_edit_task(user_id, prompt, filename, processed=None, strength=0.75, steps=30, session_id=None, sequence=None, edit_status='temporary'):
    """Process AI-powered image edits using Hugging Face API"""
    try:
        # Get API token from config
        api_token = Config.HF_API_TOKEN
        if not api_token:
            return {'success': False, 'error': 'Hugging Face API token not configured'}
        
        # Determine source file path
        if processed:
            source_path = os.path.join(Config.PROCESSED_FOLDER, processed)
        else:
            source_path = os.path.join(Config.UPLOAD_FOLDER, filename)
        
        if not os.path.exists(source_path):
            return {'success': False, 'error': 'Source image not found'}
        
        # Use Hugging Face API for AI image editing
        model_url = f"https://api-inference.huggingface.co/models/{Config.HF_MODEL}"
        
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        
        # Read and encode the image
        with open(source_path, 'rb') as f:
            image_data = f.read()
        
        # For image-to-image generation, we'll use a simple approach
        # In a more advanced setup, you'd use specific img2img models
        payload = {
            "inputs": prompt,
            "parameters": {
                "num_inference_steps": steps,
                "strength": strength
            }
        }
        
        response = requests.post(model_url, headers=headers, json=payload, timeout=60)
        
        if response.status_code != 200:
            return {'success': False, 'error': f'API request failed: {response.status_code}'}
        
        # Save the generated image
        base_name = os.path.splitext(filename)[0]
        output_filename = f"{base_name}_ai_edit_{uuid.uuid4().hex[:8]}.jpg"
        output_path = os.path.join(Config.PROCESSED_FOLDER, output_filename)
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        # Store in database
        doc = {
            'processed_filename': output_filename,
            'source_filename': filename,
            'operation': 'ai_edit',
            'output_path': output_path,
            'created_by': user_id,
            'created_at': datetime.utcnow(),
            'session_id': session_id,
            'sequence': sequence,
            'edit_status': edit_status,
            'file_size': os.path.getsize(output_path),
            'parameters': {
                'prompt': prompt,
                'strength': strength,
                'steps': steps
            }
        }
        
        result = extensions.db.processed.insert_one(doc)
        
        return {
            'success': True,
            'processed_filename': output_filename,
            'document_id': str(result.inserted_id),
            'operation': 'ai_edit'
        }
        
    except Exception as e:
        return {'success': False, 'error': f'AI processing failed: {str(e)}'}

def batch_process_images(user_id, operation, filenames, **kwargs):
    """Process multiple images with the same operation"""
    results = []
    
    for filename in filenames:
        try:
            result = process_image_task(
                user_id=user_id,
                operation=operation,
                filename=filename,
                **kwargs
            )
            results.append({
                'filename': filename,
                'result': result
            })
        except Exception as e:
            results.append({
                'filename': filename,
                'result': {'success': False, 'error': str(e)}
            })
    
    return {
        'success': True,
        'batch_results': results,
        'processed_count': len([r for r in results if r['result'].get('success')])
    }