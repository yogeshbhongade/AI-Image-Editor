"""
Utility functions for the AI Image Editor application
Common helper functions used across the application
"""

import os
import uuid
import hashlib
import mimetypes
from datetime import datetime
from typing import Optional, Tuple, List
from werkzeug.utils import secure_filename as werkzeug_secure_filename
from PIL import Image

from .config import get_config
from .exceptions import ValidationError, FileTypeError, FileSizeError


def generate_filename(original_filename: str, prefix: str = '', suffix: str = '') -> str:
    """Generate a unique filename while preserving extension"""
    config = get_config()
    
    # Get file extension
    name, ext = os.path.splitext(original_filename)
    if not ext:
        ext = '.jpg'  # Default extension
    
    # Generate unique identifier
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    unique_id = uuid.uuid4().hex[:8]
    
    # Construct filename
    parts = [prefix, timestamp, unique_id, suffix]
    filename_base = '_'.join(filter(None, parts))
    
    return f"{filename_base}{ext.lower()}"


def secure_filename(filename: str) -> str:
    """Secure filename with additional validation"""
    if not filename:
        raise ValidationError("Filename cannot be empty")
    
    # Use werkzeug's secure_filename
    secured = werkzeug_secure_filename(filename)
    
    if not secured:
        raise ValidationError("Invalid filename")
    
    # Additional validation
    if len(secured) > 255:
        name, ext = os.path.splitext(secured)
        secured = name[:250] + ext
    
    return secured


def validate_image_file(file, max_size_mb: int = None) -> Tuple[bool, str]:
    """Validate uploaded image file"""
    config = get_config()
    max_size = max_size_mb or config.MAX_FILE_SIZE_MB
    
    try:
        # Check if file exists
        if not file or not file.filename:
            raise ValidationError("No file provided")
        
        # Secure filename
        filename = secure_filename(file.filename)
        
        # Check file extension
        _, ext = os.path.splitext(filename.lower())
        if ext[1:] not in config.ALLOWED_EXTENSIONS:
            raise FileTypeError(ext[1:], list(config.ALLOWED_EXTENSIONS))
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # Reset file pointer
        
        max_size_bytes = max_size * 1024 * 1024
        if file_size > max_size_bytes:
            raise FileSizeError(file_size, max_size_bytes)
        
        # Validate image content
        try:
            with Image.open(file) as img:
                img.verify()
            file.seek(0)  # Reset after verification
        except Exception:
            raise ValidationError("Invalid image file")
        
        return True, "File is valid"
        
    except (ValidationError, FileTypeError, FileSizeError) as e:
        return False, str(e)
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def get_file_hash(file_path: str) -> Optional[str]:
    """Generate MD5 hash of file"""
    try:
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return None


def get_image_info(file_path: str) -> dict:
    """Get image information"""
    try:
        with Image.open(file_path) as img:
            return {
                'width': img.width,
                'height': img.height,
                'format': img.format,
                'mode': img.mode,
                'size': os.path.getsize(file_path)
            }
    except Exception:
        return {}


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def validate_coordinates(x: int, y: int, width: int, height: int, 
                        img_width: int, img_height: int) -> bool:
    """Validate crop coordinates"""
    if x < 0 or y < 0 or width <= 0 or height <= 0:
        return False
    
    if x + width > img_width or y + height > img_height:
        return False
    
    return True


def sanitize_prompt(prompt: str) -> str:
    """Sanitize AI prompt input"""
    if not prompt:
        return ""
    
    # Remove excessive whitespace
    prompt = ' '.join(prompt.split())
    
    # Limit length
    if len(prompt) > 500:
        prompt = prompt[:500]
    
    # Remove potentially harmful content (basic filtering)
    harmful_words = ['script', 'javascript', 'eval', 'exec']
    for word in harmful_words:
        prompt = prompt.replace(word, '')
    
    return prompt.strip()


def create_thumbnail(image_path: str, thumbnail_path: str, size: Tuple[int, int] = (200, 200)) -> bool:
    """Create thumbnail of image"""
    try:
        with Image.open(image_path) as img:
            img.thumbnail(size, Image.Resampling.LANCZOS)
            img.save(thumbnail_path, 'JPEG', quality=85)
        return True
    except Exception:
        return False


def cleanup_temp_files(directory: str, max_age_hours: int = 24) -> int:
    """Clean up temporary files older than max_age_hours"""
    if not os.path.exists(directory):
        return 0
    
    cutoff_time = datetime.utcnow().timestamp() - (max_age_hours * 3600)
    deleted_count = 0
    
    try:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                if os.path.getmtime(file_path) < cutoff_time:
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except Exception:
                        continue
    except Exception:
        pass
    
    return deleted_count


def get_mime_type(file_path: str) -> str:
    """Get MIME type of file"""
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or 'application/octet-stream'


def is_safe_path(path: str, base_path: str) -> bool:
    """Check if path is safe (no directory traversal)"""
    try:
        abs_base = os.path.abspath(base_path)
        abs_path = os.path.abspath(os.path.join(base_path, path))
        return abs_path.startswith(abs_base)
    except Exception:
        return False


def paginate_results(query_result: List, page: int = 1, per_page: int = 20) -> dict:
    """Paginate query results"""
    total = len(query_result)
    start = (page - 1) * per_page
    end = start + per_page
    
    items = query_result[start:end]
    
    return {
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page,
        'has_prev': page > 1,
        'has_next': end < total,
        'prev_num': page - 1 if page > 1 else None,
        'next_num': page + 1 if end < total else None
    }
