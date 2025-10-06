from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from app import extensions
from app.security import authenticate_user, create_user
import bcrypt

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('core.dashboard'))
    if request.method == 'POST':
        email_or_username = request.form.get('email_or_username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        if not email_or_username or not password:
            flash('Please fill in all fields', 'error')
            return render_template('login.html')
        user = authenticate_user(email_or_username, password)
        if user:
            login_user(user, remember=remember)
            flash(f'Welcome back, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('core.dashboard'))
        else:
            flash('Invalid email/username or password', 'error')
    return render_template('login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('core.dashboard'))
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')
        if not all([email, username, password, confirm_password]):
            flash('Please fill in all required fields', 'error')
            return render_template('register.html')
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('register.html')
        user, message = create_user(email, username, password, first_name, last_name)
        if user:
            login_user(user)
            flash(f'Welcome to ImageCraft, {user.username}!', 'success')
            return redirect(url_for('core.dashboard'))
        else:
            flash(message, 'error')
    return render_template('register.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'success')
    return redirect(url_for('core.home'))

@bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Update user profile information."""
    try:
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()

        extensions.db.users.update_one(
            {'_id': current_user.id},
            {
                '$set': {
                    'first_name': first_name,
                    'last_name': last_name
                }
            }
        )

        current_user.first_name = first_name
        current_user.last_name = last_name

        flash('Profile updated successfully', 'success')
        return redirect(url_for('auth.profile'))
    except Exception as e:
        flash(f'Error updating profile: {str(e)}', 'error')
        return redirect(url_for('auth.profile'))

@bp.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password."""
    try:
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not all([current_password, new_password, confirm_password]):
            flash('All password fields are required', 'error')
            return redirect(url_for('auth.profile'))

        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return redirect(url_for('auth.profile'))

        if len(new_password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return redirect(url_for('auth.profile'))

        user_data = extensions.db.users.find_one({'_id': current_user.id})
        stored_hash = user_data.get('password') or user_data.get('password_hash')

        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode('utf-8')

        if not bcrypt.checkpw(current_password.encode('utf-8'), stored_hash):
            flash('Current password is incorrect', 'error')
            return redirect(url_for('auth.profile'))

        new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

        extensions.db.users.update_one(
            {'_id': current_user.id},
            {'$set': {'password': new_hash}}
        )

        flash('Password changed successfully', 'success')
        return redirect(url_for('auth.profile'))

    except Exception as e:
        flash(f'Error changing password: {str(e)}', 'error')
        return redirect(url_for('auth.profile'))

@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Password reset request page."""
    if current_user.is_authenticated:
        return redirect(url_for('core.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')

        if not email:
            flash('Email is required', 'error')
            return render_template('forgot_password.html')

        user_data = extensions.db.users.find_one({'email': email})

        if user_data:
            flash('If an account exists with this email, a password reset link has been sent. (Note: Email functionality not yet implemented)', 'info')
        else:
            flash('If an account exists with this email, a password reset link has been sent.', 'info')

        return redirect(url_for('auth.login'))

    return render_template('forgot_password.html')
