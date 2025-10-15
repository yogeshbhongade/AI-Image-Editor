"""
File service for handling uploads, downloads, and file operations
Manages secure file operations and storage
"""

import os
import shutil
from typing import Optional, Dict, Any, List
from werkzeug.datastructures import FileStorage
from flask import send_file, abort

from app.core.config import get_config
from app.core.exceptions import FileNotFoundError, ValidationError, AuthorizationError
from app.core.utils import generate_filename, validate_image_file, secure_filename, get_image_info
from app.models.image import ImageService
from app.models.user import UserService


class FileService:
    """Service for file operations"""
    
    def __init__(self):
        self.config = get_config()
        self.image_service = ImageService()
        self.user_service = UserService()
    
    def save_upload(self, file: FileStorage, user_id: str) -> Dict[str, Any]:
        """Save uploaded file and return file info"""
        # Validate file
        is_valid, error_msg = validate_image_file(file, self.config.MAX_FILE_SIZE_MB)
        if not is_valid:
            raise ValidationError(error_msg)
        
        # Generate secure filename
        original_filename = secure_filename(file.filename)
        filename = generate_filename(original_filename, prefix='upload')
        
        # Save file
        file_path = self.config.get_upload_path(filename)
        file.save(file_path)
        
        # Get file info
        file_size = os.path.getsize(file_path)
        image_info = get_image_info(file_path)
        
        # Save to database
        image_model = self.image_service.save_upload(
            filename=filename,
            original_filename=original_filename,
            user_id=user_id,
            file_size=file_size
        )
        
        return {
            'filename': filename,
            'original_filename': original_filename,
            'file_size': file_size,
            'image_info': image_info,
            'model': image_model.to_dict()
        }
    
    def serve_uploaded_file(self, filename: str, user_id: str):
        """Serve uploaded file with security checks"""
        # Verify file belongs to user
        uploads = self.image_service.get_user_uploads(user_id)
        user_files = [upload.filename for upload in uploads]
        
        if filename not in user_files:
            raise AuthorizationError("Access denied to this file")
        
        file_path = self.config.get_upload_path(filename)
        if not os.path.exists(file_path):
            raise FileNotFoundError(filename)
        
        # Use proper mimetype detection
        from app.core.utils import get_mime_type
        mime_type = get_mime_type(file_path)
        return send_file(file_path, mimetype=mime_type)
    
    def serve_processed_file(self, filename: str, user_id: str):
        """Serve processed file with security checks"""
        # Verify file belongs to user
        image = self.image_service.get_processed_image(filename, user_id)
        
        if not image:
            raise AuthorizationError("Access denied to this file")
        
        file_path = self.config.get_processed_path(filename)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(filename)
        
        # Use proper mimetype detection
        from app.core.utils import get_mime_type
        mime_type = get_mime_type(file_path)
        return send_file(file_path, mimetype=mime_type)
    
    def download_file(self, filename: str, user_id: str):
        """Download file with logging"""
        # Verify file belongs to user
        image = self.image_service.get_processed_image(filename, user_id)
        
        if not image:
            raise AuthorizationError("Access denied to this file")
        
        file_path = self.config.get_processed_path(filename)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(filename)
        
        # Log download
        self.image_service.log_download(
            filename=filename,
            user_id=user_id,
            original_filename=image.source_filename,
            file_size=image.file_size
        )
        
        # Use proper mimetype detection
        from app.core.utils import get_mime_type
        mime_type = get_mime_type(file_path)
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype=mime_type
        )
    
    def delete_file(self, filename: str, user_id: str, file_type: str = 'processed') -> bool:
        """Delete file with security checks"""
        try:
            if file_type == 'processed':
                # Verify ownership
                image = self.image_service.get_processed_image(filename, user_id)
                if not image:
                    raise AuthorizationError("Access denied to this file")
                
                file_path = self.config.get_processed_path(filename)
                
                # Delete from database
                from app.core.database import get_db
                db = get_db()
                db.processed.delete_one({
                    'processed_filename': filename,
                    'created_by': user_id
                })
                
            else:  # uploaded file
                # Verify ownership
                uploads = self.image_service.get_user_uploads(user_id)
                user_files = [upload.filename for upload in uploads]
                
                if filename not in user_files:
                    raise AuthorizationError("Access denied to this file")
                
                file_path = self.config.get_upload_path(filename)
                
                # Delete from database
                from app.core.database import get_db
                db = get_db()
                db.uploads.delete_one({
                    'filename': filename,
                    'uploaded_by': user_id
                })
            
            # Delete physical file
            if os.path.exists(file_path):
                os.remove(file_path)
            
            return True
            
        except Exception:
            return False
    
    def get_user_files(self, user_id: str, file_type: str = 'all', limit: int = 50) -> List[Dict]:
        """Get user's files"""
        files = []
        
        if file_type in ['all', 'uploads']:
            uploads = self.image_service.get_user_uploads(user_id, limit)
            for upload in uploads:
                files.append({
                    'type': 'upload',
                    'filename': upload.filename,
                    'original_filename': upload.original_filename,
                    'created_at': upload.created_at,
                    'file_size': upload.file_size
                })
        
        if file_type in ['all', 'processed']:
            processed = self.image_service.get_user_processed_images(user_id, limit)
            for proc in processed:
                files.append({
                    'type': 'processed',
                    'filename': proc.processed_filename,
                    'source_filename': proc.source_filename,
                    'operation': proc.operation,
                    'created_at': proc.created_at,
                    'file_size': proc.file_size,
                    'edit_status': proc.edit_status,
                    'expires_at': proc.expires_at
                })
        
        # Sort by creation date
        files.sort(key=lambda x: x['created_at'], reverse=True)
        
        return files
    
    def cleanup_expired_files(self) -> Dict[str, int]:
        """Clean up expired files"""
        deleted_count = self.image_service.cleanup_expired_images()
        
        return {
            'deleted_files': deleted_count,
            'message': f"Cleaned up {deleted_count} expired files"
        }
    
    def get_storage_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user's storage usage statistics"""
        usage = self.image_service.get_user_storage_usage(user_id)
        user_stats = self.user_service.get_user_stats(user_id)
        
        return {
            'storage_usage': usage,
            'file_counts': user_stats,
            'limits': {
                'max_file_size_mb': self.config.MAX_FILE_SIZE_MB,
                'max_files_per_user': self.config.MAX_FILES_PER_USER
            }
        }
    
    def validate_file_access(self, filename: str, user_id: str, file_type: str = 'processed') -> bool:
        """Validate if user has access to file"""
        try:
            if file_type == 'processed':
                image = self.image_service.get_processed_image(filename, user_id)
                return image is not None
            else:
                uploads = self.image_service.get_user_uploads(user_id)
                user_files = [upload.filename for upload in uploads]
                return filename in user_files
        except Exception:
            return False
    
    def get_file_info(self, filename: str, user_id: str, file_type: str = 'processed') -> Optional[Dict]:
        """Get detailed file information"""
        try:
            if file_type == 'processed':
                image = self.image_service.get_processed_image(filename, user_id)
                if not image:
                    return None
                
                file_path = self.config.get_processed_path(filename)
                if os.path.exists(file_path):
                    image_info = get_image_info(file_path)
                    return {
                        **image.to_dict(),
                        'image_info': image_info,
                        'file_exists': True
                    }
                else:
                    return {
                        **image.to_dict(),
                        'file_exists': False
                    }
            else:
                uploads = self.image_service.get_user_uploads(user_id)
                for upload in uploads:
                    if upload.filename == filename:
                        file_path = self.config.get_upload_path(filename)
                        if os.path.exists(file_path):
                            image_info = get_image_info(file_path)
                            return {
                                **upload.to_dict(),
                                'image_info': image_info,
                                'file_exists': True
                            }
                        else:
                            return {
                                **upload.to_dict(),
                                'file_exists': False
                            }
                return None
                
        except Exception:
            return None
    
    def create_backup(self, user_id: str) -> Optional[str]:
        """Create backup of user's files"""
        try:
            import zipfile
            from datetime import datetime
            
            # Create backup filename
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"backup_{user_id}_{timestamp}.zip"
            backup_path = os.path.join(self.config.PROCESSED_FOLDER, backup_filename)
            
            # Get user files
            files = self.get_user_files(user_id)
            
            # Create zip file
            with zipfile.ZipFile(backup_path, 'w') as zipf:
                for file_info in files:
                    if file_info['type'] == 'processed':
                        file_path = self.config.get_processed_path(file_info['filename'])
                    else:
                        file_path = self.config.get_upload_path(file_info['filename'])
                    
                    if os.path.exists(file_path):
                        zipf.write(file_path, file_info['filename'])
            
            return backup_filename
            
        except Exception:
            return None
