"""
Core API routes
Handles main application pages and core functionality
"""

from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user

from app.models.user import UserService
from app.models.subscription import SubscriptionService
from app.services.file_service import FileService

core_bp = Blueprint('core', __name__)


@core_bp.route('/')
def home():
    """Home page"""
    return render_template('home.html')


@core_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    user_service = UserService()
    file_service = FileService()
    
    # Get user statistics
    user_stats = user_service.get_user_stats(current_user.id)
    storage_stats = file_service.get_storage_stats(current_user.id)
    
    # Get recent files
    recent_files = file_service.get_user_files(current_user.id, limit=10)
    
    return render_template('dashboard.html',
                         user_stats=user_stats,
                         storage_stats=storage_stats,
                         recent_files=recent_files)


@core_bp.route('/editing')
@core_bp.route('/editing/<filename>')
@login_required
def editing(filename=None):
    """Image editing interface"""
    processed_filename = None
    
    if filename:
        # Verify user has access to this file
        file_service = FileService()
        if not file_service.validate_file_access(filename, current_user.id, 'upload'):
            return render_template('error.html', error='File not found or access denied'), 404
    
    return render_template('editing.html', 
                         filename=filename,
                         processed_filename=processed_filename)


@core_bp.route('/my-images')
@login_required
def my_images():
    """User's image gallery"""
    file_service = FileService()
    
    # Get user's files
    files = file_service.get_user_files(current_user.id, limit=100)
    
    return render_template('my_images.html', files=files)


@core_bp.route('/downloads')
@login_required
def downloads():
    """User downloads page"""
    return render_template('downloads.html')


@core_bp.route('/limits/current')
@login_required
def get_current_limits():
    """Get current user limits and usage statistics"""
    try:
        from app.models.subscription import SubscriptionService
        
        subscription_service = SubscriptionService()
        
        # Get user subscription
        subscription = subscription_service.get_user_subscription(current_user.id)
        
        # Get usage limits
        limits = subscription_service.get_usage_limits(current_user.id)
        
        # Get current usage
        current_usage = subscription_service.get_current_usage(current_user.id)
        
        # Get usage stats
        usage_stats = subscription_service.get_usage_stats(current_user.id)
        
        # Transform limits to match frontend expectations
        frontend_limits = {
            'edit_daily': limits.get('edit', 50),
            'ai_daily': limits.get('ai', 5),
            'download_daily': limits.get('download', 20),
            'generation_daily': limits.get('generation', 3)
        }
        
        return jsonify({
            'success': True,
            'subscription_status': subscription.tier,
            'is_premium': subscription.is_premium,
            'limits': limits,  # Keep original for other uses
            'current_usage': current_usage,
            'usage_stats': usage_stats,
            'expires_at': subscription.expires_at.isoformat() if subscription.expires_at else None,
            # Add frontend-compatible format
            'edit_daily': frontend_limits['edit_daily'],
            'ai_daily': frontend_limits['ai_daily'],
            'download_daily': frontend_limits['download_daily'],
            'generation_daily': frontend_limits['generation_daily']
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Failed to load limits',
            'subscription_status': 'free',
            'is_premium': False,
            'limits': {'edit': 50, 'ai': 5, 'download': 20, 'generation': 3},
            'current_usage': {'edit': 0, 'ai': 0, 'download': 0, 'generation': 0},
            'usage_stats': {'used': {'edit': 0, 'ai': 0}, 'remaining': {'edit': 50, 'ai': 5}},
            # Add frontend-compatible format for fallback
            'edit_daily': 50,
            'ai_daily': 5,
            'download_daily': 20,
            'generation_daily': 3
        }), 200  # Return 200 with fallback data instead of error


@core_bp.route('/usage/check')
@login_required
def usage_check():
    """Get current usage for the user - simplified endpoint for usage-manager.js"""
    try:
        from app.models.subscription import SubscriptionService
        
        subscription_service = SubscriptionService()
        current_usage = subscription_service.get_current_usage(current_user.id)
        
        # Return in the format expected by usage-manager.js
        return jsonify({
            'edit': current_usage.get('edit', 0),
            'ai': current_usage.get('ai', 0),
            'download': current_usage.get('download', 0)
        })
        
    except Exception as e:
        # Return default usage on error
        return jsonify({
            'edit': 0,
            'ai': 0,
            'download': 0
        })


@core_bp.route('/debug/usage')
@login_required
def debug_usage():
    """Debug endpoint to check usage and limits"""
    try:
        from app.models.subscription import SubscriptionService
        
        subscription_service = SubscriptionService()
        
        # Get all the data
        subscription = subscription_service.get_user_subscription(current_user.id)
        limits = subscription_service.get_usage_limits(current_user.id)
        current_usage = subscription_service.get_current_usage(current_user.id)
        
        # Check if user can perform edit action
        can_edit = subscription_service.can_perform_action(current_user.id, 'edit')
        
        return jsonify({
            'user_id': current_user.id,
            'subscription': {
                'tier': subscription.tier,
                'is_premium': subscription.is_premium,
                'is_active': subscription.is_active
            },
            'limits': limits,
            'current_usage': current_usage,
            'can_edit': can_edit,
            'debug_info': {
                'edit_limit': limits.get('edit', 0),
                'edit_used': current_usage.get('edit', 0),
                'remaining': limits.get('edit', 0) - current_usage.get('edit', 0)
            }
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'user_id': current_user.id
        }), 500


@core_bp.route('/debug/reset-usage', methods=['POST'])
@login_required
def reset_usage():
    """Reset usage for current user (debug only)"""
    try:
        from app.models.subscription import SubscriptionService
        from datetime import datetime
        
        subscription_service = SubscriptionService()
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Delete all usage records for today for this user
        result = subscription_service.usage_collection.delete_many({
            'user_id': current_user.id,
            'date': today_start
        })
        
        return jsonify({
            'success': True,
            'message': f'Reset {result.deleted_count} usage records for user {current_user.id}'
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500


@core_bp.route('/debug/frontend-limits')
@login_required
def debug_frontend_limits():
    """Debug endpoint to test frontend limits format"""
    try:
        from app.models.subscription import SubscriptionService
        
        subscription_service = SubscriptionService()
        
        # Get the data as the frontend would receive it
        limits_response = get_current_limits()
        usage_response = usage_check()
        
        return jsonify({
            'limits_endpoint_response': limits_response.get_json(),
            'usage_endpoint_response': usage_response.get_json(),
            'frontend_should_work': True
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500


@core_bp.route('/help')
def help_page():
    """Help and documentation page"""
    return render_template('help.html')


@core_bp.route('/settings')
@login_required
def settings():
    """User settings page"""
    return render_template('settings.html')


@core_bp.route('/create-subscription', methods=['POST'])
@login_required
def create_subscription_redirect():
    """Redirect to subscription blueprint for payment.js compatibility"""
    from app.api.subscription import create_subscription_order
    return create_subscription_order()


@core_bp.route('/api/stats/user')
@login_required
def user_stats():
    """Get comprehensive user statistics"""
    user_service = UserService()
    file_service = FileService()
    subscription_service = SubscriptionService()
    
    stats = {
        'user': user_service.get_user_stats(current_user.id),
        'storage': file_service.get_storage_stats(current_user.id),
        'usage': subscription_service.get_usage_stats(current_user.id)
    }
    
    return jsonify(stats)
