"""
AI API routes
Handles AI image generation and editing operations
"""

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user

from app.services.ai_service import AIService
from app.services.queue_service import QueueService
from app.models.subscription import SubscriptionService
from app.core.exceptions import ValidationError, SubscriptionError, UsageLimitError

ai_bp = Blueprint('ai', __name__)


@ai_bp.route('/generate-page')
@login_required
def generate_page():
    """AI image generation page"""
    return render_template('generate.html')


@ai_bp.route('/generate', methods=['POST'])
@login_required
def generate_image():
    """Generate image from text prompt"""
    try:
        queue_service = QueueService()
        subscription_service = SubscriptionService()
        ai_service = AIService()
        
        # Check subscription
        subscription = subscription_service.get_user_subscription(current_user.id)
        if not subscription.is_premium:
            raise SubscriptionError('Premium subscription required for AI image generation', 'premium')
        
        # Check usage limits
        if not subscription_service.can_perform_action(current_user.id, 'generation'):
            raise UsageLimitError('generation', 3, 3)
        
        # Get request data
        data = request.get_json()
        if not data:
            raise ValidationError('No data provided')
        
        prompt = data.get('prompt', '').strip()
        if not prompt:
            raise ValidationError('Prompt is required')
        
        width = int(data.get('width', 512))
        height = int(data.get('height', 512))
        steps = int(data.get('steps', 30))
        
        # Validate parameters
        if not ai_service.validate_generation_params(width, height, steps):
            raise ValidationError('Invalid generation parameters')
        
        # Prepare parameters
        parameters = {
            'prompt': prompt,
            'width': width,
            'height': height,
            'steps': steps,
            'session_id': data.get('session_id'),
            'edit_status': 'permanent' if subscription.is_premium else 'temporary'
        }
        
        # Queue the job
        job_id = queue_service.enqueue_ai_task(
            user_id=current_user.id,
            task_type='generate',
            parameters=parameters,
            is_premium=subscription.is_premium
        )
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'AI generation started'
        })
        
    except (ValidationError, SubscriptionError, UsageLimitError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': 'Generation failed'}), 500


@ai_bp.route('/edit', methods=['POST'])
@login_required
def edit_image():
    """Edit image using AI"""
    try:
        queue_service = QueueService()
        subscription_service = SubscriptionService()
        ai_service = AIService()
        
        # Check subscription
        subscription = subscription_service.get_user_subscription(current_user.id)
        if not subscription.is_premium:
            raise SubscriptionError('Premium subscription required for AI image editing', 'premium')
        
        # Check usage limits
        if not subscription_service.can_perform_action(current_user.id, 'ai'):
            raise UsageLimitError('ai', 5, 5)
        
        # Get request data
        data = request.get_json()
        if not data:
            raise ValidationError('No data provided')
        
        prompt = data.get('prompt', '').strip()
        filename = data.get('filename')
        
        if not prompt or not filename:
            raise ValidationError('Prompt and filename are required')
        
        strength = float(data.get('strength', 0.75))
        steps = int(data.get('steps', 30))
        
        # Validate parameters
        if not ai_service.validate_editing_params(strength, steps):
            raise ValidationError('Invalid editing parameters')
        
        # Prepare parameters
        parameters = {
            'prompt': prompt,
            'filename': filename,
            'processed': data.get('processed'),
            'strength': strength,
            'steps': steps,
            'session_id': data.get('session_id'),
            'sequence': data.get('sequence'),
            'edit_status': 'permanent' if subscription.is_premium else 'temporary'
        }
        
        # Queue the job
        job_id = queue_service.enqueue_ai_task(
            user_id=current_user.id,
            task_type='edit',
            parameters=parameters,
            is_premium=subscription.is_premium
        )
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'AI editing started'
        })
        
    except (ValidationError, SubscriptionError, UsageLimitError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': 'AI editing failed'}), 500


@ai_bp.route('/examples')
def get_examples():
    """Get AI prompt examples"""
    ai_service = AIService()
    examples = ai_service.get_suggested_prompts()
    
    return jsonify({
        'success': True,
        'examples': examples
    })


@ai_bp.route('/model-info')
def get_model_info():
    """Get AI model information"""
    ai_service = AIService()
    info = ai_service.get_model_info()
    
    return jsonify({
        'success': True,
        'model_info': info
    })
