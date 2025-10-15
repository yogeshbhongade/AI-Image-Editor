"""
Image processing API routes
Handles image upload, processing, serving, and download operations
"""

from flask import Blueprint, request, jsonify, send_file
from flask_login import login_required, current_user

from app.services.file_service import FileService
from app.services.queue_service import QueueService
from app.models.image import ImageService
from app.models.subscription import SubscriptionService
from app.core.exceptions import ValidationError, AuthorizationError, UsageLimitError

images_bp = Blueprint('images', __name__)


@images_bp.route('/upload', methods=['POST'])
@login_required
def upload_image():
    """Upload a new image"""
    try:
        file_service = FileService()
        subscription_service = SubscriptionService()
        
        # Check upload limits
        if not subscription_service.can_perform_action(current_user.id, 'edit'):
            limits = subscription_service.get_usage_limits(current_user.id)
            current_usage = subscription_service.get_current_usage(current_user.id)
            raise UsageLimitError('edit', limits.get('edit', 50), current_usage.get('edit', 0))
        
        # Get uploaded file
        if 'file' not in request.files:
            raise ValidationError('No file provided')
        
        file = request.files['file']
        if not file or not file.filename:
            raise ValidationError('No file selected')
        
        # Save upload
        result = file_service.save_upload(file, current_user.id)
        
        return jsonify({
            'success': True,
            'filename': result['filename'],
            'original_filename': result['original_filename'],
            'file_size': result['file_size'],
            'image_info': result['image_info'],
            'message': 'Image uploaded successfully'
        })
        
    except (ValidationError, UsageLimitError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': 'Upload failed'}), 500


@images_bp.route('/process', methods=['POST'])
@login_required
def process_image():
    """Queue image processing operation"""
    try:
        queue_service = QueueService()
        subscription_service = SubscriptionService()
        
        # Get request data
        data = request.get_json()
        if not data:
            raise ValidationError('No data provided')
        
        operation = data.get('operation')
        filename = data.get('filename')
        
        if not operation or not filename:
            raise ValidationError('Operation and filename are required')
        
        # Check usage limits
        if not subscription_service.can_perform_action(current_user.id, 'edit'):
            limits = subscription_service.get_usage_limits(current_user.id)
            current_usage = subscription_service.get_current_usage(current_user.id)
            raise UsageLimitError('edit', limits.get('edit', 50), current_usage.get('edit', 0))
        
        # Check if operation requires premium
        subscription = subscription_service.get_user_subscription(current_user.id)
        premium_operations = {'emboss', 'edges', 'enhance', 'posterize', 'solarize'}
        
        if operation in premium_operations and not subscription.is_premium:
            return jsonify({
                'success': False,
                'error': 'Premium subscription required for this operation',
                'upgrade_required': True
            }), 402
        
        # Prepare parameters
        parameters = {
            'processed': data.get('processed'),
            'value': data.get('value'),
            'width': data.get('width'),
            'height': data.get('height'),
            'session_id': data.get('session_id'),
            'sequence': data.get('sequence'),
            'edit_status': 'permanent' if subscription.is_premium else 'temporary'
        }
        
        # Queue the job
        job_id = queue_service.enqueue_image_processing(
            user_id=current_user.id,
            operation=operation,
            filename=filename,
            parameters=parameters,
            is_premium=subscription.is_premium
        )
        
        # Increment usage counter after successful job creation
        subscription_service.increment_usage(current_user.id, 'edit')
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Processing started'
        })
        
    except (ValidationError, UsageLimitError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': 'Processing failed'}), 500


@images_bp.route('/job-status/<job_id>')
@login_required
def get_job_status(job_id):
    """Get status of processing job"""
    try:
        queue_service = QueueService()
        status = queue_service.get_job_status(job_id)
        
        # Verify job belongs to current user
        if status.get('metadata', {}).get('user_id') != current_user.id:
            raise AuthorizationError('Access denied to this job')
        
        return jsonify(status)
        
    except AuthorizationError as e:
        return jsonify({'error': str(e)}), 403
    except Exception as e:
        return jsonify({'error': 'Failed to get job status'}), 500


@images_bp.route('/history/<session_id>')
@login_required
def get_history(session_id):
    """Get editing history for session"""
    try:
        image_service = ImageService()
        
        # Get session history
        history = image_service.get_session_history(session_id, current_user.id)
        
        # Format for frontend
        formatted_history = []
        for item in history:
            formatted_history.append({
                'operation': item.operation,
                'processed_filename': item.processed_filename,
                'sequence': item.sequence,
                'edit_status': item.edit_status,
                'expires_at': item.expires_at.isoformat() if item.expires_at else None,
                'history_id': item.id,
                'params': item.parameters
            })
        
        return jsonify({
            'success': True,
            'history': formatted_history
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': 'Failed to load history'}), 500


@images_bp.route('/history/navigate/<session_id>/<int:position>')
@login_required
def navigate_history(session_id, position):
    """Navigate to specific position in history"""
    try:
        image_service = ImageService()
        
        # Get history state
        state = image_service.get_history_state(session_id, current_user.id, position)
        
        if not state:
            return jsonify({'success': False, 'error': 'History state not found'}), 404
        
        return jsonify({
            'success': True,
            'state': {
                'processed_filename': state.processed_filename,
                'sequence': state.sequence,
                'operation': state.operation,
                'edit_status': state.edit_status,
                'expires_at': state.expires_at.isoformat() if state.expires_at else None
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': 'Failed to navigate history'}), 500


@images_bp.route('/serve/uploaded/<filename>')
@login_required
def serve_uploaded(filename):
    """Serve uploaded image file"""
    try:
        file_service = FileService()
        return file_service.serve_uploaded_file(filename, current_user.id)
    except AuthorizationError:
        return jsonify({'error': 'Access denied'}), 403
    except Exception:
        return jsonify({'error': 'File not found'}), 404


@images_bp.route('/serve/processed/<filename>')
@login_required
def serve_processed(filename):
    """Serve processed image file"""
    try:
        file_service = FileService()
        return file_service.serve_processed_file(filename, current_user.id)
    except AuthorizationError:
        return jsonify({'error': 'Access denied'}), 403
    except Exception:
        return jsonify({'error': 'File not found'}), 404


@images_bp.route('/download/<filename>')
@login_required
def download_file(filename):
    """Download processed image file"""
    try:
        file_service = FileService()
        subscription_service = SubscriptionService()
        
        # Check download limits
        if not subscription_service.can_perform_action(current_user.id, 'download'):
            raise UsageLimitError('download', 20, 20)
        
        # Increment usage and serve file
        subscription_service.increment_usage(current_user.id, 'download')
        return file_service.download_file(filename, current_user.id)
        
    except UsageLimitError as e:
        return jsonify({'error': str(e), 'upgrade_required': True}), 429
    except AuthorizationError:
        return jsonify({'error': 'Access denied'}), 403
    except Exception:
        return jsonify({'error': 'File not found'}), 404


@images_bp.route('/delete/<filename>', methods=['DELETE'])
@login_required
def delete_file(filename):
    """Delete image file"""
    try:
        file_service = FileService()
        file_type = request.args.get('type', 'processed')
        
        success = file_service.delete_file(filename, current_user.id, file_type)
        
        if success:
            return jsonify({'success': True, 'message': 'File deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to delete file'}), 500
            
    except AuthorizationError:
        return jsonify({'error': 'Access denied'}), 403
    except Exception:
        return jsonify({'error': 'Delete operation failed'}), 500


@images_bp.route('/info/<filename>')
@login_required
def get_file_info(filename):
    """Get detailed file information"""
    try:
        file_service = FileService()
        file_type = request.args.get('type', 'processed')
        
        info = file_service.get_file_info(filename, current_user.id, file_type)
        
        if info:
            return jsonify({'success': True, 'info': info})
        else:
            return jsonify({'success': False, 'error': 'File not found'}), 404
            
    except Exception:
        return jsonify({'error': 'Failed to get file info'}), 500
