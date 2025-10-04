from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
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
