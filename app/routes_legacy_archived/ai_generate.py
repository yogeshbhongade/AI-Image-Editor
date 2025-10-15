"""
AI Image Generation Routes
Handles text-to-image generation (nano banana style feature)
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from app import extensions
from app.security import premium_required

bp = Blueprint('ai_generate', __name__)


@bp.route('/generate', methods=['GET'])
@login_required
def generate_page():
    """Render the AI image generation page."""
    return render_template('generate.html')


@bp.route('/generate-task', methods=['POST'])
@login_required
def enqueue_generate_task():
    """
    Enqueue AI image generation task.

    Expects JSON payload:
    {
        "prompt": "description of image to generate",
        "width": 512,
        "height": 512,
        "steps": 30
    }
    """
    data = request.get_json(force=True)
    prompt = data.get('prompt', '').strip()

    if not prompt:
        return jsonify({'success': False, 'error': 'Prompt is required'}), 400

    width = int(data.get('width', 512))
    height = int(data.get('height', 512))
    steps = int(data.get('steps', 30))

    # Validate dimensions
    if width < 256 or width > 1024 or height < 256 or height > 1024:
        return jsonify({
            'success': False,
            'error': 'Image dimensions must be between 256 and 1024 pixels'
        }), 400

    # Check subscription for advanced parameters
    if current_user.subscription_status != 'premium':
        # Free users get limited options
        width = min(width, 512)
        height = min(height, 512)
        steps = min(steps, 20)

    session_id = data.get('session_id') or f"gen_{current_user.id}_{int(datetime.utcnow().timestamp())}"
    edit_status = 'permanent' if current_user.subscription_status == 'premium' else 'temporary'

    try:
        from tasks import process_ai_generate_task
        from datetime import datetime

        # Determine which queue to use
        queue_to_use = extensions.premium_queue if current_user.subscription_status == 'premium' else extensions.queue

        job = queue_to_use.enqueue(
            process_ai_generate_task,
            user_id=current_user.id,
            prompt=prompt,
            width=width,
            height=height,
            steps=steps,
            session_id=session_id,
            edit_status=edit_status,
            timeout=180
        )

        return jsonify({
            'success': True,
            'job_id': job.get_id(),
            'session_id': session_id
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to start generation: {str(e)}'
        }), 500


@bp.route('/generate-examples', methods=['GET'])
def get_examples():
    """Get example prompts for inspiration."""
    examples = [
        {
            'category': 'Nature',
            'prompts': [
                'A serene mountain landscape at sunset with vibrant colors',
                'Tropical beach with crystal clear water and palm trees',
                'Mystical forest with glowing mushrooms and fireflies',
                'Northern lights over a snowy landscape'
            ]
        },
        {
            'category': 'Abstract',
            'prompts': [
                'Colorful geometric shapes floating in space',
                'Swirling galaxy with nebula clouds',
                'Abstract digital art with neon colors',
                'Fractal patterns with metallic textures'
            ]
        },
        {
            'category': 'Fantasy',
            'prompts': [
                'Magical floating castle in the clouds',
                'Dragon flying over medieval village',
                'Enchanted garden with glowing flowers',
                'Crystal cave with bioluminescent plants'
            ]
        },
        {
            'category': 'Sci-Fi',
            'prompts': [
                'Futuristic cityscape with flying vehicles',
                'Space station orbiting an alien planet',
                'Cyberpunk street with neon signs',
                'Robot in a high-tech laboratory'
            ]
        },
        {
            'category': 'Food & Objects',
            'prompts': [
                'Nano banana - a tiny banana with intricate details',
                'Miniature city built inside a coffee cup',
                'Elaborate cake with impossible architecture',
                'Jeweled crown with magical properties'
            ]
        }
    ]

    return jsonify({'success': True, 'examples': examples})
