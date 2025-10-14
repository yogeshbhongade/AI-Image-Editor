"""
Image model and service layer
Handles all image-related database operations and business logic
"""

from datetime import datetime, timedelta
from bson import ObjectId
from typing import Optional, Dict, Any, List
import os

class ImageModel:
    """Image model for database operations"""
    
    def __init__(self, data: Dict[str, Any]):
        self.id = str(data.get('_id'))
        self.filename = data.get('filename')
        self.original_filename = data.get('original_filename')
        self.processed_filename = data.get('processed_filename')
        self.source_filename = data.get('source_filename')
        self.operation = data.get('operation')
        self.user_id = data.get('uploaded_by') or data.get('created_by')
        self.created_at = data.get('uploaded_at') or data.get('created_at')
        self.file_size = data.get('file_size', 0)
        self.session_id = data.get('session_id')
        self.sequence = data.get('sequence', 0)
        self.edit_status = data.get('edit_status', 'temporary')
        self.expires_at = data.get('expires_at')
        self.parameters = data.get('parameters', {})
    
    @property
    def is_expired(self) -> bool:
        """Check if image has expired"""
        if self.edit_status == 'permanent':
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'processed_filename': self.processed_filename,
            'operation': self.operation,
            'user_id': self.user_id,
            'created_at': self.created_at,
            'file_size': self.file_size,
            'session_id': self.session_id,
            'sequence': self.sequence,
            'edit_status': self.edit_status,
            'expires_at': self.expires_at,
            'is_expired': self.is_expired,
            'parameters': self.parameters
        }


class ImageService:
    """Service layer for image operations"""
    
    def __init__(self):
        self._db = None
        self._config = None
        self._uploads_collection = None
        self._processed_collection = None
        self._downloads_collection = None
    
    @property
    def db(self):
        if self._db is None:
            from app.core.database import get_db
            self._db = get_db()
        return self._db
    
    @property
    def config(self):
        if self._config is None:
            from app.core.config import get_config
            self._config = get_config()
        return self._config
    
    @property
    def uploads_collection(self):
        if self._uploads_collection is None:
            self._uploads_collection = self.db.uploads
        return self._uploads_collection
    
    @property
    def processed_collection(self):
        if self._processed_collection is None:
            self._processed_collection = self.db.processed
        return self._processed_collection
    
    @property
    def downloads_collection(self):
        if self._downloads_collection is None:
            self._downloads_collection = self.db.downloads
        return self._downloads_collection
    
    def save_upload(self, filename: str, original_filename: str, user_id: str, 
                   file_size: int) -> ImageModel:
        """Save uploaded image to database"""
        upload_data = {
            'filename': filename,
            'original_filename': original_filename,
            'uploaded_by': user_id,
            'uploaded_at': datetime.utcnow(),
            'file_size': file_size,
            'file_path': os.path.join(self.config.UPLOAD_FOLDER, filename)
        }
        
        result = self.uploads_collection.insert_one(upload_data)
        upload_data['_id'] = result.inserted_id
        
        return ImageModel(upload_data)
    
    def save_processed_image(self, processed_filename: str, source_filename: str,
                           operation: str, user_id: str, session_id: str,
                           sequence: int, edit_status: str = 'temporary',
                           parameters: Dict = None) -> ImageModel:
        """Save processed image to database"""
        file_path = os.path.join(self.config.PROCESSED_FOLDER, processed_filename)
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        
        # Set expiration for temporary edits
        expires_at = None
        if edit_status == 'temporary':
            expires_at = datetime.utcnow() + timedelta(hours=24)
        
        processed_data = {
            'processed_filename': processed_filename,
            'source_filename': source_filename,
            'operation': operation,
            'created_by': user_id,
            'created_at': datetime.utcnow(),
            'session_id': session_id,
            'sequence': sequence,
            'edit_status': edit_status,
            'expires_at': expires_at,
            'file_size': file_size,
            'file_path': file_path,
            'parameters': parameters or {}
        }
        
        result = self.processed_collection.insert_one(processed_data)
        processed_data['_id'] = result.inserted_id
        
        return ImageModel(processed_data)
    
    def get_user_uploads(self, user_id: str, limit: int = 50) -> List[ImageModel]:
        """Get user's uploaded images"""
        uploads = list(self.uploads_collection.find(
            {'uploaded_by': user_id}
        ).sort('uploaded_at', -1).limit(limit))
        
        return [ImageModel(upload) for upload in uploads]
    
    def get_user_processed_images(self, user_id: str, limit: int = 50) -> List[ImageModel]:
        """Get user's processed images"""
        processed = list(self.processed_collection.find(
            {'created_by': user_id}
        ).sort('created_at', -1).limit(limit))
        
        return [ImageModel(img) for img in processed]
    
    def get_session_history(self, session_id: str, user_id: str) -> List[ImageModel]:
        """Get editing history for a session"""
        history = list(self.processed_collection.find({
            'session_id': session_id,
            'created_by': user_id
        }).sort('sequence', 1))
        
        return [ImageModel(img) for img in history]
    
    def get_history_state(self, session_id: str, user_id: str, position: int) -> Optional[ImageModel]:
        """Get specific history state"""
        state = self.processed_collection.find_one({
            'session_id': session_id,
            'created_by': user_id,
            'sequence': position
        })
        
        return ImageModel(state) if state else None
    
    def get_processed_image(self, filename: str, user_id: str) -> Optional[ImageModel]:
        """Get processed image by filename and user"""
        image = self.processed_collection.find_one({
            'processed_filename': filename,
            'created_by': user_id
        })
        
        return ImageModel(image) if image else None
    
    def log_download(self, filename: str, user_id: str, original_filename: str = None,
                    file_size: int = 0) -> bool:
        """Log image download"""
        try:
            download_data = {
                'user_id': user_id,
                'filename': filename,
                'original_filename': original_filename,
                'download_timestamp': datetime.utcnow(),
                'file_size': file_size
            }
            
            self.downloads_collection.insert_one(download_data)
            return True
        except Exception:
            return False
    
    def cleanup_expired_images(self) -> int:
        """Clean up expired temporary images"""
        try:
            # Find expired images
            expired_images = list(self.processed_collection.find({
                'edit_status': 'temporary',
                'expires_at': {'$lt': datetime.utcnow()}
            }))
            
            deleted_count = 0
            for image in expired_images:
                # Delete file from disk
                file_path = image.get('file_path')
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except:
                        pass
                
                # Delete from database
                self.processed_collection.delete_one({'_id': image['_id']})
                deleted_count += 1
            
            return deleted_count
        except Exception:
            return 0
    
    def get_user_storage_usage(self, user_id: str) -> Dict[str, int]:
        """Get user's storage usage statistics"""
        try:
            # Calculate total file sizes
            upload_size = sum(
                doc.get('file_size', 0) 
                for doc in self.uploads_collection.find({'uploaded_by': user_id})
            )
            
            processed_size = sum(
                doc.get('file_size', 0)
                for doc in self.processed_collection.find({'created_by': user_id})
            )
            
            return {
                'upload_size': upload_size,
                'processed_size': processed_size,
                'total_size': upload_size + processed_size
            }
        except Exception:
            return {'upload_size': 0, 'processed_size': 0, 'total_size': 0}
