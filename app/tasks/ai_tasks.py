"""
AI processing background tasks
Handles AI image generation and editing operations
"""

from datetime import datetime
from typing import Dict, Any

from app.core.config import get_config
from app.core.exceptions import AIServiceError
from app.services.ai_service import AIService
from app.models.image import ImageService
from app.models.subscription import SubscriptionService


def process_ai_generate_task(user_id: str, prompt: str, width: int = 512, 
                           height: int = 512, steps: int = 30,
                           session_id: str = None, edit_status: str = 'temporary') -> Dict[str, Any]:
    """
    Background task for AI image generation
    
    Args:
        user_id: ID of the user requesting the generation
        prompt: Text prompt for image generation
        width: Image width in pixels
        height: Image height in pixels
        steps: Number of inference steps
        session_id: Session ID for history tracking
        edit_status: 'temporary' or 'permanent'
    
    Returns:
        Dict containing generation result
    """
    try:
        config = get_config()
        
        # Initialize services
        ai_service = AIService()
        image_service = ImageService()
        subscription_service = SubscriptionService()
        
        # Update job progress
        from rq import get_current_job
        job = get_current_job()
        if job:
            job.meta['progress'] = 10
            job.save_meta()
        
        # Check subscription for AI features
        subscription = subscription_service.get_user_subscription(user_id)
        if not subscription.is_premium:
            return {
                'success': False,
                'error': 'Premium subscription required for AI image generation',
                'upgrade_required': True
            }
        
        # Check usage limits
        if not subscription_service.can_perform_action(user_id, 'generation'):
            return {
                'success': False,
                'error': 'AI generation limit reached for today',
                'upgrade_required': False
            }
        
        # Validate parameters
        if not ai_service.validate_generation_params(width, height, steps):
            return {
                'success': False,
                'error': 'Invalid generation parameters'
            }
        
        # Update progress
        if job:
            job.meta['progress'] = 30
            job.save_meta()
        
        # Adjust parameters for free users (shouldn't happen due to premium check above)
        if not subscription.is_premium:
            width = min(width, 512)
            height = min(height, 512)
            steps = min(steps, 20)
        
        # Update progress
        if job:
            job.meta['progress'] = 50
            job.save_meta()
        
        # Generate image
        output_filename = ai_service.generate_image(
            prompt=prompt,
            width=width,
            height=height,
            steps=steps
        )
        
        # Update progress
        if job:
            job.meta['progress'] = 80
            job.save_meta()
        
        # Save to database
        image_model = image_service.save_processed_image(
            processed_filename=output_filename,
            source_filename=None,  # No source for generated images
            operation='ai_generate',
            user_id=user_id,
            session_id=session_id or f"gen_{user_id}_{int(datetime.utcnow().timestamp())}",
            sequence=0,  # Generated images start at sequence 0
            edit_status=edit_status,
            parameters={
                'prompt': prompt,
                'width': width,
                'height': height,
                'steps': steps
            }
        )
        
        # Increment usage counter
        subscription_service.increment_usage(user_id, 'generation')
        
        # Update progress
        if job:
            job.meta['progress'] = 100
            job.save_meta()
        
        return {
            'success': True,
            'processed_filename': output_filename,
            'document_id': image_model.id,
            'operation': 'ai_generate',
            'edit_status': edit_status,
            'expires_at': image_model.expires_at.isoformat() if image_model.expires_at else None,
            'session_id': image_model.session_id,
            'sequence': image_model.sequence,
            'parameters': {
                'prompt': prompt,
                'width': width,
                'height': height,
                'steps': steps
            },
            'message': 'AI image generated successfully'
        }
        
    except AIServiceError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.error_code
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'AI generation failed: {str(e)}'
        }


def process_ai_edit_task(user_id: str, prompt: str, filename: str,
                        processed: str = None, strength: float = 0.75,
                        steps: int = 30, session_id: str = None,
                        sequence: int = None, edit_status: str = 'temporary') -> Dict[str, Any]:
    """
    Background task for AI image editing
    
    Args:
        user_id: ID of the user requesting the edit
        prompt: Text prompt for image editing
        filename: Name of the source file
        processed: Existing processed filename to edit
        strength: Strength of the AI editing (0.1-1.0)
        steps: Number of inference steps
        session_id: Session ID for history tracking
        sequence: Sequence number in editing history
        edit_status: 'temporary' or 'permanent'
    
    Returns:
        Dict containing editing result
    """
    try:
        config = get_config()
        
        # Initialize services
        ai_service = AIService()
        image_service = ImageService()
        subscription_service = SubscriptionService()
        
        # Update job progress
        from rq import get_current_job
        job = get_current_job()
        if job:
            job.meta['progress'] = 10
            job.save_meta()
        
        # Check subscription for AI features
        subscription = subscription_service.get_user_subscription(user_id)
        if not subscription.is_premium:
            return {
                'success': False,
                'error': 'Premium subscription required for AI image editing',
                'upgrade_required': True
            }
        
        # Check usage limits
        if not subscription_service.can_perform_action(user_id, 'ai'):
            return {
                'success': False,
                'error': 'AI editing limit reached for today',
                'upgrade_required': False
            }
        
        # Validate parameters
        if not ai_service.validate_editing_params(strength, steps):
            return {
                'success': False,
                'error': 'Invalid editing parameters'
            }
        
        # Update progress
        if job:
            job.meta['progress'] = 30
            job.save_meta()
        
        # Determine source file path
        if processed:
            source_path = config.get_processed_path(processed)
        else:
            source_path = config.get_upload_path(filename)
        
        # Adjust parameters for free users (shouldn't happen due to premium check above)
        if not subscription.is_premium:
            strength = min(max(strength, 0.3), 0.7)  # Clamp between 0.3 and 0.7
            steps = min(steps, 20)
        
        # Update progress
        if job:
            job.meta['progress'] = 50
            job.save_meta()
        
        # Edit image
        output_filename = ai_service.edit_image(
            source_path=source_path,
            prompt=prompt,
            strength=strength,
            steps=steps
        )
        
        # Update progress
        if job:
            job.meta['progress'] = 80
            job.save_meta()
        
        # Determine edit status based on subscription
        if edit_status == 'temporary' and subscription.is_premium:
            edit_status = 'permanent'
        
        # Save to database
        image_model = image_service.save_processed_image(
            processed_filename=output_filename,
            source_filename=filename,
            operation='ai_edit',
            user_id=user_id,
            session_id=session_id or f"sess_{user_id}_{int(datetime.utcnow().timestamp())}",
            sequence=sequence or 1,
            edit_status=edit_status,
            parameters={
                'prompt': prompt,
                'strength': strength,
                'steps': steps
            }
        )
        
        # Increment usage counter
        subscription_service.increment_usage(user_id, 'ai')
        
        # Update progress
        if job:
            job.meta['progress'] = 100
            job.save_meta()
        
        return {
            'success': True,
            'processed_filename': output_filename,
            'document_id': image_model.id,
            'operation': 'ai_edit',
            'edit_status': edit_status,
            'expires_at': image_model.expires_at.isoformat() if image_model.expires_at else None,
            'session_id': image_model.session_id,
            'sequence': image_model.sequence,
            'parameters': {
                'prompt': prompt,
                'strength': strength,
                'steps': steps
            },
            'message': 'AI image editing completed successfully'
        }
        
    except AIServiceError as e:
        return {
            'success': False,
            'error': str(e),
            'error_code': e.error_code
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'AI editing failed: {str(e)}'
        }
