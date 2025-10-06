"""
Background task processing for image operations.
This module handles all image processing tasks using RQ (Redis Queue).
"""

import os
import io
import requests
from datetime import datetime, timedelta
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from app.config import Config

def get_db():
    """Get database connection from extensions."""
    from app import extensions
    return extensions.db

def process_image_task(user_id, operation, filename, edit_status='temporary',
                       processed=None, value=None, width=None, height=None,
                       session_id=None, sequence=None, **kwargs):
    """
    Process image with the specified operation.

    Args:
        user_id: User ID performing the operation
        operation: Operation to perform (rotate, flip, crop, etc.)
        filename: Original filename
        edit_status: 'temporary' or 'permanent'
        processed: Previously processed filename (for chaining operations)
        value: Operation-specific value (brightness, rotation angle, etc.)
        width: Width for resize/crop
        height: Height for resize/crop
        session_id: Session ID for history tracking
        sequence: Sequence number in edit history
        **kwargs: Additional operation-specific parameters

    Returns:
        dict: Result containing processed_filename and metadata
    """
    db = get_db()

    try:
        # Determine source file
        if processed:
            source_path = os.path.join(Config.PROCESSED_FOLDER, processed)
            source_filename = processed
        else:
            source_path = os.path.join(Config.UPLOAD_FOLDER, filename)
            source_filename = filename

        if not os.path.exists(source_path):
            return {
                'success': False,
                'error': f'Source file not found: {source_filename}'
            }

        # Load image
        img = Image.open(source_path)

        # Ensure RGB mode for operations that require it
        if img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')

        # Perform operation
        if operation == 'rotate':
            angle = int(value) if value else 90
            img = img.rotate(-angle, expand=True)

        elif operation == 'flip_h':
            img = img.transpose(Image.FLIP_LEFT_RIGHT)

        elif operation == 'flip_v':
            img = img.transpose(Image.FLIP_TOP_BOTTOM)

        elif operation == 'grayscale':
            img = ImageOps.grayscale(img)
            img = img.convert('RGB')

        elif operation == 'brightness':
            factor = float(value) if value else 1.0
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(factor)

        elif operation == 'contrast':
            factor = float(value) if value else 1.0
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(factor)

        elif operation == 'saturation':
            factor = float(value) if value else 1.0
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(factor)

        elif operation == 'sharpness':
            factor = float(value) if value else 1.0
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(factor)

        elif operation == 'blur':
            radius = float(value) if value else 2.0
            img = img.filter(ImageFilter.GaussianBlur(radius))

        elif operation == 'sharpen':
            img = img.filter(ImageFilter.SHARPEN)

        elif operation == 'emboss':
            img = img.filter(ImageFilter.EMBOSS)

        elif operation == 'edges':
            img = img.filter(ImageFilter.FIND_EDGES)

        elif operation == 'enhance':
            img = img.filter(ImageFilter.DETAIL)

        elif operation == 'crop':
            x = kwargs.get('x', 0)
            y = kwargs.get('y', 0)
            if not width or not height:
                # Default center crop
                w, h = img.size
                crop_size = min(w, h)
                x = (w - crop_size) // 2
                y = (h - crop_size) // 2
                width = height = crop_size
            img = img.crop((x, y, x + width, y + height))

        elif operation == 'resize':
            if not width or not height:
                return {'success': False, 'error': 'Width and height required for resize'}
            img = img.resize((width, height), Image.Resampling.LANCZOS)

        else:
            return {'success': False, 'error': f'Unknown operation: {operation}'}

        # Generate output filename
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
        name, ext = os.path.splitext(filename)
        output_filename = f"{name}_{operation}_{timestamp}.jpg"
        output_path = os.path.join(Config.PROCESSED_FOLDER, output_filename)

        # Ensure processed folder exists
        os.makedirs(Config.PROCESSED_FOLDER, exist_ok=True)

        # Save processed image
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        img.save(output_path, 'JPEG', quality=90, optimize=True)

        # Calculate expiration for temporary edits
        expires_at = None
        if edit_status == 'temporary':
            expires_at = datetime.utcnow() + timedelta(hours=24)

        # Store in database
        processed_doc = {
            'user_id': str(user_id),
            'source_filename': source_filename,
            'processed_filename': output_filename,
            'operation': operation,
            'output_path': output_path,
            'session_id': session_id,
            'sequence': sequence or 0,
            'edit_status': edit_status,
            'expires_at': expires_at,
            'params': {
                'value': value,
                'width': width,
                'height': height,
                **kwargs
            },
            'created_at': datetime.utcnow()
        }

        # For MongoDB compatibility (will migrate to Supabase)
        if hasattr(db, 'processed_images'):
            db.processed_images.insert_one(processed_doc)

        # Store in history if session_id provided
        if session_id:
            history_doc = {
                'user_id': str(user_id),
                'session_id': session_id,
                'filename': filename,
                'processed_filename': output_filename,
                'operation': operation,
                'sequence': sequence or 0,
                'params': processed_doc['params'],
                'edit_status': edit_status,
                'expires_at': expires_at,
                'created_at': datetime.utcnow()
            }
            if hasattr(db, 'edit_history'):
                db.edit_history.insert_one(history_doc)

        return {
            'success': True,
            'processed_filename': output_filename,
            'session_id': session_id,
            'sequence': sequence or 0,
            'edit_status': edit_status,
            'expires_at': expires_at.isoformat() if expires_at else None,
            'params': processed_doc['params'],
            'message': f'{operation.title()} applied successfully!'
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'Error processing image: {str(e)}'
        }


def process_ai_edit_task(user_id, prompt, filename, processed=None,
                         strength=0.75, steps=30, session_id=None,
                         sequence=None, edit_status='temporary'):
    """
    Process AI-powered image editing using Hugging Face API.

    Args:
        user_id: User ID performing the operation
        prompt: Text prompt describing desired edit
        filename: Original filename
        processed: Previously processed filename
        strength: Strength of the AI edit (0.0-1.0)
        steps: Number of inference steps
        session_id: Session ID for history tracking
        sequence: Sequence number in edit history
        edit_status: 'temporary' or 'permanent'

    Returns:
        dict: Result containing processed_filename and metadata
    """
    db = get_db()

    try:
        # Determine source file
        if processed:
            source_path = os.path.join(Config.PROCESSED_FOLDER, processed)
            source_filename = processed
        else:
            source_path = os.path.join(Config.UPLOAD_FOLDER, filename)
            source_filename = filename

        if not os.path.exists(source_path):
            return {
                'success': False,
                'error': f'Source file not found: {source_filename}'
            }

        # Check if API token is configured
        if not Config.HF_API_TOKEN:
            return {
                'success': False,
                'error': 'AI features require API configuration. Please contact administrator.'
            }

        # Read image file
        with open(source_path, 'rb') as f:
            image_data = f.read()

        # Call Hugging Face API for image-to-image
        api_url = f"https://api-inference.huggingface.co/models/{Config.HF_MODEL}"
        headers = {"Authorization": f"Bearer {Config.HF_API_TOKEN}"}

        payload = {
            "inputs": prompt,
            "parameters": {
                "strength": strength,
                "num_inference_steps": steps
            }
        }

        # Send request with image
        files = {"file": image_data}
        response = requests.post(
            api_url,
            headers=headers,
            files=files,
            json=payload,
            timeout=120
        )

        if response.status_code != 200:
            error_msg = response.json().get('error', 'AI processing failed')
            return {
                'success': False,
                'error': f'AI API error: {error_msg}'
            }

        # Generate output filename
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
        name, ext = os.path.splitext(filename)
        output_filename = f"{name}_ai_{timestamp}.jpg"
        output_path = os.path.join(Config.PROCESSED_FOLDER, output_filename)

        # Ensure processed folder exists
        os.makedirs(Config.PROCESSED_FOLDER, exist_ok=True)

        # Save AI-processed image
        ai_image = Image.open(io.BytesIO(response.content))
        if ai_image.mode == 'RGBA':
            ai_image = ai_image.convert('RGB')
        ai_image.save(output_path, 'JPEG', quality=90, optimize=True)

        # Calculate expiration
        expires_at = None
        if edit_status == 'temporary':
            expires_at = datetime.utcnow() + timedelta(hours=24)

        # Store in database
        processed_doc = {
            'user_id': str(user_id),
            'source_filename': source_filename,
            'processed_filename': output_filename,
            'operation': 'ai_edit',
            'output_path': output_path,
            'session_id': session_id,
            'sequence': sequence or 0,
            'edit_status': edit_status,
            'expires_at': expires_at,
            'params': {
                'prompt': prompt,
                'strength': strength,
                'steps': steps
            },
            'created_at': datetime.utcnow()
        }

        if hasattr(db, 'processed_images'):
            db.processed_images.insert_one(processed_doc)

        # Store in history
        if session_id:
            history_doc = {
                'user_id': str(user_id),
                'session_id': session_id,
                'filename': filename,
                'processed_filename': output_filename,
                'operation': 'ai_edit',
                'sequence': sequence or 0,
                'params': processed_doc['params'],
                'edit_status': edit_status,
                'expires_at': expires_at,
                'created_at': datetime.utcnow()
            }
            if hasattr(db, 'edit_history'):
                db.edit_history.insert_one(history_doc)

        return {
            'success': True,
            'processed_filename': output_filename,
            'session_id': session_id,
            'sequence': sequence or 0,
            'edit_status': edit_status,
            'expires_at': expires_at.isoformat() if expires_at else None,
            'params': processed_doc['params'],
            'message': 'AI edit applied successfully!'
        }

    except requests.Timeout:
        return {
            'success': False,
            'error': 'AI processing timed out. Please try again.'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Error during AI processing: {str(e)}'
        }


def process_ai_generate_task(user_id, prompt, width=512, height=512,
                              steps=30, session_id=None, edit_status='temporary'):
    """
    Generate new image from text prompt (nano banana style feature).

    Args:
        user_id: User ID performing the operation
        prompt: Text prompt describing desired image
        width: Output image width
        height: Output image height
        steps: Number of inference steps
        session_id: Session ID for tracking
        edit_status: 'temporary' or 'permanent'

    Returns:
        dict: Result containing generated_filename and metadata
    """
    db = get_db()

    try:
        if not Config.HF_API_TOKEN:
            return {
                'success': False,
                'error': 'AI generation requires API configuration. Please contact administrator.'
            }

        # Use text-to-image model
        api_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
        headers = {"Authorization": f"Bearer {Config.HF_API_TOKEN}"}

        payload = {
            "inputs": prompt,
            "parameters": {
                "width": width,
                "height": height,
                "num_inference_steps": steps
            }
        }

        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=120
        )

        if response.status_code != 200:
            error_msg = response.json().get('error', 'AI generation failed')
            return {
                'success': False,
                'error': f'AI API error: {error_msg}'
            }

        # Generate output filename
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
        output_filename = f"generated_{timestamp}.jpg"
        output_path = os.path.join(Config.PROCESSED_FOLDER, output_filename)

        # Ensure processed folder exists
        os.makedirs(Config.PROCESSED_FOLDER, exist_ok=True)

        # Save generated image
        generated_image = Image.open(io.BytesIO(response.content))
        if generated_image.mode == 'RGBA':
            generated_image = generated_image.convert('RGB')
        generated_image.save(output_path, 'JPEG', quality=90, optimize=True)

        # Calculate expiration
        expires_at = None
        if edit_status == 'temporary':
            expires_at = datetime.utcnow() + timedelta(hours=24)

        # Store in database
        processed_doc = {
            'user_id': str(user_id),
            'source_filename': 'generated',
            'processed_filename': output_filename,
            'operation': 'ai_generate',
            'output_path': output_path,
            'session_id': session_id,
            'sequence': 0,
            'edit_status': edit_status,
            'expires_at': expires_at,
            'params': {
                'prompt': prompt,
                'width': width,
                'height': height,
                'steps': steps
            },
            'created_at': datetime.utcnow()
        }

        if hasattr(db, 'processed_images'):
            db.processed_images.insert_one(processed_doc)

        return {
            'success': True,
            'processed_filename': output_filename,
            'generated_filename': output_filename,
            'session_id': session_id,
            'edit_status': edit_status,
            'expires_at': expires_at.isoformat() if expires_at else None,
            'params': processed_doc['params'],
            'message': 'Image generated successfully!'
        }

    except requests.Timeout:
        return {
            'success': False,
            'error': 'AI generation timed out. Please try again.'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Error during AI generation: {str(e)}'
        }
