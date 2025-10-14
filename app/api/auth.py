"""
Authentication API routes
Handles user registration, login, logout, and profile management
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, login_required, logout_user, current_user

from app.models.user import UserService
from app.core.exceptions import ValidationError, AuthenticationError

auth_bp = Blueprint('auth', __name__)
user_service = UserService()


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('core.dashboard'))
    
    if request.method == 'POST':
        try:
            email_or_username = request.form.get('email_or_username', '').strip()
            password = request.form.get('password', '')
            remember = bool(request.form.get('remember'))
            
            if not email_or_username or not password:
                raise ValidationError('Please fill in all fields')
            
            user = user_service.authenticate_user(email_or_username, password)
            if not user:
                raise AuthenticationError('Invalid email/username or password')
            
            login_user(user, remember=remember)
            flash(f'Welcome back, {user.username}!', 'success')
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('core.dashboard'))
            
        except (ValidationError, AuthenticationError) as e:
            flash(str(e), 'error')
        except Exception as e:
            flash('Login failed. Please try again.', 'error')
    
    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('core.dashboard'))
    
    if request.method == 'POST':
        try:
            email = request.form.get('email', '').strip()
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            
            # Validation
            if not all([email, username, password, confirm_password]):
                raise ValidationError('Please fill in all required fields')
            
            if password != confirm_password:
                raise ValidationError('Passwords do not match')
            
            if len(password) < 6:
                raise ValidationError('Password must be at least 6 characters long')
            
            if len(username) < 3:
                raise ValidationError('Username must be at least 3 characters long')
            
            # Create user
            user, message = user_service.create_user(
                email=email,
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            if user:
                login_user(user)
                flash(f'Welcome to ImageCraft, {user.username}!', 'success')
                return redirect(url_for('core.dashboard'))
            else:
                flash(message, 'error')
                
        except ValidationError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash('Registration failed. Please try again.', 'error')
    
    return render_template('register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('core.home'))


@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    from app.services.file_service import FileService
    from app.models.subscription import SubscriptionService
    
    file_service = FileService()
    subscription_service = SubscriptionService()
    
    # Get user statistics
    storage_stats = file_service.get_storage_stats(current_user.id)
    usage_stats = subscription_service.get_usage_stats(current_user.id)
    
    return render_template('profile.html', 
                         storage_stats=storage_stats,
                         usage_stats=usage_stats)


@auth_bp.route('/settings')
@login_required
def settings():
    """User settings page"""
    return render_template('settings.html')


# API endpoints for AJAX requests
@auth_bp.route('/api/check-username', methods=['POST'])
def check_username():
    """Check if username is available"""
    try:
        username = request.json.get('username', '').strip()
        if not username:
            return jsonify({'available': False, 'message': 'Username is required'})
        
        # Check if username exists
        from app.core.database import get_db
        db = get_db()
        existing_user = db.users.find_one({'username': username})
        
        if existing_user:
            return jsonify({'available': False, 'message': 'Username is already taken'})
        
        return jsonify({'available': True, 'message': 'Username is available'})
        
    except Exception as e:
        return jsonify({'available': False, 'message': 'Error checking username'}), 500


@auth_bp.route('/api/check-email', methods=['POST'])
def check_email():
    """Check if email is available"""
    try:
        email = request.json.get('email', '').strip()
        if not email:
            return jsonify({'available': False, 'message': 'Email is required'})
        
        # Check if email exists
        from app.core.database import get_db
        db = get_db()
        existing_user = db.users.find_one({'email': email})
        
        if existing_user:
            return jsonify({'available': False, 'message': 'Email is already registered'})
        
        return jsonify({'available': True, 'message': 'Email is available'})
        
    except Exception as e:
        return jsonify({'available': False, 'message': 'Error checking email'}), 500
