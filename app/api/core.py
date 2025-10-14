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
        
        return jsonify({
            'success': True,
            'subscription_status': subscription.tier,
            'is_premium': subscription.is_premium,
            'limits': limits,
            'current_usage': current_usage,
            'usage_stats': usage_stats,
            'expires_at': subscription.expires_at.isoformat() if subscription.expires_at else None
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Failed to load limits',
            'subscription_status': 'free',
            'is_premium': False,
            'limits': {'edit': 50, 'ai': 0},
            'current_usage': {'edit': 0, 'ai': 0},
            'usage_stats': {'used': {'edit': 0, 'ai': 0}, 'remaining': {'edit': 50, 'ai': 0}}
        }), 200  # Return 200 with fallback data instead of error


@core_bp.route('/help')
def help_page():
    """Help and documentation page"""
    return render_template('help.html')


@core_bp.route('/settings')
@login_required
def settings():
    """User settings page"""
    return render_template('settings.html')


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
