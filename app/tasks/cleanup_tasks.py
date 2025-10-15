"""Cleanup tasks for background job queue"""

import os
from datetime import datetime, timedelta
from app.core.config import get_config
from app.core.database import get_db


def cleanup_expired_files_task():
    """Clean up expired temporary files"""
    try:
        config = get_config()
        db = get_db()
        
        # Clean up files older than 24 hours
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        # Find expired processed files
        expired_files = db.processed.find({
            'edit_status': 'temporary',
            'created_at': {'$lt': cutoff_time}
        })
        
        deleted_count = 0
        for file_doc in expired_files:
            try:
                # Delete physical file
                if 'output_path' in file_doc and os.path.exists(file_doc['output_path']):
                    os.remove(file_doc['output_path'])
                    deleted_count += 1
                
                # Remove database record
                db.processed.delete_one({'_id': file_doc['_id']})
                
            except Exception as e:
                print(f"Error deleting file {file_doc.get('processed_filename')}: {e}")
        
        return {
            'success': True,
            'deleted_count': deleted_count,
            'message': f'Cleaned up {deleted_count} expired files'
        }
        
    except Exception as e:
        return {'success': False, 'error': f'Cleanup failed: {str(e)}'}


def cleanup_old_jobs_task():
    """Clean up old job records from the database"""
    try:
        db = get_db()
        
        # Clean up jobs older than 7 days
        cutoff_time = datetime.utcnow() - timedelta(days=7)
        
        # Delete old job records
        result = db.jobs.delete_many({
            'created_at': {'$lt': cutoff_time}
        })
        
        return {
            'success': True,
            'deleted_count': result.deleted_count,
            'message': f'Cleaned up {result.deleted_count} old job records'
        }
        
    except Exception as e:
        return {'success': False, 'error': f'Job cleanup failed: {str(e)}'}
