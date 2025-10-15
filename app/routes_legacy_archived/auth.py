from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from app import extensions
from app.security import authenticate_user, create_user

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
