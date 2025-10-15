"""
Admin API routes
Handles administrative functions and system management
"""

from datetime import datetime
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user

from app.models.user import UserService
from app.services.file_service import FileService
from app.services.queue_service import QueueService
from app.core.exceptions import AuthorizationError

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    """Decorator to require admin access"""
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            raise AuthorizationError("Admin access required")
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function


@admin_bp.route('/')
@login_required
@admin_required
def admin_dashboard():
    """Admin dashboard"""
    from datetime import datetime
    from app.core.database import get_db
    
    user_service = UserService()
    file_service = FileService()
    queue_service = QueueService()
    
    # Get system statistics
    db = get_db()
    
    stats = {
        'users': {
            'total': db.users.count_documents({}),
            'premium': db.users.count_documents({'subscription_status': 'premium'}),
            'active_today': db.users.count_documents({
                'last_login': {'$gte': datetime.utcnow().replace(hour=0, minute=0, second=0)}
            })
        },
        'images': {
            'uploads': db.uploads.count_documents({}),
            'processed': db.processed.count_documents({}),
            'downloads': db.downloads.count_documents({})
        },
        'queue': queue_service.get_queue_stats()
    }
    
    # Get recent users
    recent_users = list(db.users.find({}).sort('created_at', -1).limit(10))
    
    return render_template('admin.html', stats=stats, recent_users=recent_users)


@admin_bp.route('/api/stats')
@login_required
@admin_required
def get_system_stats():
    """Get comprehensive system statistics"""
    from app.core.database import get_db
    from datetime import datetime, timedelta
    
    db = get_db()
    now = datetime.utcnow()
    
    stats = {
        'users': {
            'total': db.users.count_documents({}),
            'premium': db.users.count_documents({'subscription_status': 'premium'}),
            'free': db.users.count_documents({'subscription_status': 'free'}),
            'new_today': db.users.count_documents({
                'created_at': {'$gte': now.replace(hour=0, minute=0, second=0)}
            }),
            'new_this_week': db.users.count_documents({
                'created_at': {'$gte': now - timedelta(days=7)}
            })
        },
        'images': {
            'total_uploads': db.uploads.count_documents({}),
            'total_processed': db.processed.count_documents({}),
            'total_downloads': db.downloads.count_documents({}),
            'uploads_today': db.uploads.count_documents({
                'uploaded_at': {'$gte': now.replace(hour=0, minute=0, second=0)}
            }),
            'processed_today': db.processed.count_documents({
                'created_at': {'$gte': now.replace(hour=0, minute=0, second=0)}
            })
        },
        'storage': {
            'total_upload_size': 0,  # Would need aggregation pipeline
            'total_processed_size': 0,  # Would need aggregation pipeline
        },
        'queue': QueueService().get_queue_stats()
    }
    
    return jsonify(stats)


@admin_bp.route('/api/users')
@login_required
@admin_required
def get_users():
    """Get user list with pagination"""
    from app.core.database import get_db
    
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    search = request.args.get('search', '')
    
    db = get_db()
    
    # Build query
    query = {}
    if search:
        query['$or'] = [
            {'email': {'$regex': search, '$options': 'i'}},
            {'username': {'$regex': search, '$options': 'i'}},
            {'first_name': {'$regex': search, '$options': 'i'}},
            {'last_name': {'$regex': search, '$options': 'i'}}
        ]
    
    # Get total count
    total = db.users.count_documents(query)
    
    # Get users with pagination
    users = list(db.users.find(query, {
        'password': 0  # Exclude password hash
    }).sort('created_at', -1).skip((page - 1) * per_page).limit(per_page))
    
    # Convert ObjectId to string
    for user in users:
        user['_id'] = str(user['_id'])
        if user.get('created_at'):
            user['created_at'] = user['created_at'].isoformat()
        if user.get('last_login'):
            user['last_login'] = user['last_login'].isoformat()
    
    return jsonify({
        'users': users,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    })


@admin_bp.route('/api/cleanup', methods=['POST'])
@login_required
@admin_required
def run_cleanup():
    """Run system cleanup"""
    try:
        from app.tasks.cleanup_tasks import full_cleanup_task
        
        # Run cleanup synchronously for admin
        result = full_cleanup_task()
        
        return jsonify({
            'success': True,
            'result': result,
            'message': 'Cleanup completed successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Cleanup failed: {str(e)}'
        }), 500


@admin_bp.route('/api/user/<user_id>/subscription', methods=['POST'])
@login_required
@admin_required
def update_user_subscription(user_id):
    """Update user subscription status"""
    try:
        data = request.get_json()
        subscription_status = data.get('subscription_status')
        
        if subscription_status not in ['free', 'premium']:
            return jsonify({'error': 'Invalid subscription status'}), 400
        
        user_service = UserService()
        success = user_service.update_subscription(user_id, subscription_status)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'User subscription updated to {subscription_status}'
            })
        else:
            return jsonify({'error': 'Failed to update subscription'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/system/health')
@login_required
@admin_required
def system_health():
    """Get system health status"""
    try:
        from app.core.database import get_db, get_redis
        
        health = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'services': {}
        }
        
        # Check MongoDB
        try:
            db = get_db()
            db.command('ping')
            health['services']['mongodb'] = {'status': 'healthy', 'message': 'Connected'}
        except Exception as e:
            health['services']['mongodb'] = {'status': 'unhealthy', 'message': str(e)}
            health['status'] = 'degraded'
        
        # Check Redis
        try:
            redis_conn = get_redis()
            if redis_conn:
                redis_conn.ping()
                health['services']['redis'] = {'status': 'healthy', 'message': 'Connected'}
            else:
                health['services']['redis'] = {'status': 'unavailable', 'message': 'Not configured'}
        except Exception as e:
            health['services']['redis'] = {'status': 'unhealthy', 'message': str(e)}
            health['status'] = 'degraded'
        
        # Check AI service
        from app.services.ai_service import AIService
        ai_service = AIService()
        ai_info = ai_service.get_model_info()
        if ai_info['configured']:
            health['services']['ai'] = {'status': 'healthy', 'message': 'API configured'}
        else:
            health['services']['ai'] = {'status': 'unavailable', 'message': 'API not configured'}
        
        return jsonify(health)
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500
