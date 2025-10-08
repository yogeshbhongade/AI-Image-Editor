from flask import Blueprint, render_template, request, jsonify, abort
from flask_login import login_required, current_user
from bson import ObjectId
from app import extensions

bp = Blueprint('core', __name__)

@bp.route('/')
def home():
    return render_template('home.html')

@bp.route('/help')
def help_page():
    return render_template('help.html')

@bp.route('/dashboard')
@login_required
def dashboard():
    upload_count = extensions.db.uploads.count_documents({'uploaded_by': current_user.id})
    processed_count = extensions.db.processed.count_documents({'created_by': current_user.id})
    recent_uploads = list(extensions.db.uploads.find({'uploaded_by': current_user.id}).sort('uploaded_at', -1).limit(10))
    recent_processed = list(extensions.db.processed.find({'created_by': current_user.id}).sort('created_at', -1).limit(10))
    return render_template('dashboard.html',
                           upload_count=upload_count,
                           processed_count=processed_count,
                           recent_uploads=recent_uploads,
                           recent_processed=recent_processed)

@bp.route('/downloads')
@login_required
def downloads():
    page = int(request.args.get('page', 1))
    per_page = 20
    skip = (page - 1) * per_page
    q = {'user_id': str(current_user.id)}
    total = extensions.db.downloads.count_documents(q)
    downloads = list(extensions.db.downloads.find(q).sort('download_timestamp', -1).skip(skip).limit(per_page))
    return render_template('downloads.html', downloads=downloads, page=page, per_page=per_page, total=total)

@bp.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

@bp.route('/admin')
@login_required
def admin():
    # Restrict access to admins only
    if getattr(current_user, 'role', '') != 'admin':
        abort(403)
    total_users = extensions.db.users.count_documents({})
    total_uploads = extensions.db.uploads.count_documents({})
    total_processed = extensions.db.processed.count_documents({})
    recent_users = list(extensions.db.users.find({}).sort('created_at', -1).limit(10))
    return render_template('admin.html',
                         total_users=total_users,
                         total_uploads=total_uploads,
                         total_processed=total_processed,
                         recent_users=recent_users)

@bp.route('/pricing')
def pricing():
    return render_template('pricing.html')

@bp.route('/limits/current')
@login_required
def current_limits():
    """Return current user limits for frontend"""
   
    limits = {
        'edit_daily': 50,
        'ai_daily': 10,
        'download_daily': 100,
        'premium_tools': False,
    }

    # If current_user is premium / admin -> grant effectively unlimited access
    if getattr(current_user, 'subscription_status', 'free') == 'premium' or getattr(current_user, 'role', '') == 'admin':
        # Use a very large integer instead of Infinity for JSON safety,
        # and set premium_tools flag so the frontend displays "Unlimited".
        limits = {
            'edit_daily': 999999999,
            'ai_daily': 999999999,
            'download_daily': 999999999,
            'premium_tools': True,
        }

    return jsonify(limits)

@bp.route('/usage/check')  
@login_required
def usage_check():
    """Return current usage stats for frontend"""
    # Premium users: show zero usage (effectively unlimited)
    if getattr(current_user, 'subscription_status', 'free') == 'premium' or getattr(current_user, 'role', '') == 'admin':
        return jsonify({
            'edit': 0,
            'ai': 0,
            'download': 0
        })

    usage = None
    try:
        usage = extensions.usage_col.find_one({'user_id': str(current_user.id)}) or {}
    except Exception:
        usage = {}
    if not usage:
        # try ObjectId form if stored that way
        try:
            usage = extensions.usage_col.find_one({'user_id': ObjectId(current_user.id)}) or {}
        except Exception:
            usage = {}

    return jsonify({
        'edit': int(usage.get('edit', 0)),
        'ai': int(usage.get('ai', 0)),
        'download': int(usage.get('download', 0))
    })
