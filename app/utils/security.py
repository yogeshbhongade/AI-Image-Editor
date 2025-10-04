from .extensions import users_col
from flask_login import UserMixin
import bcrypt
from functools import wraps
from flask import request, flash, redirect, url_for
from flask_login import current_user
from werkzeug.utils import secure_filename
import os

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data.get('_id'))
        self.email = user_data.get('email')
        self.username = user_data.get('username')
        self.password_hash = user_data.get('password')
        self.first_name = user_data.get('first_name', '')
        self.last_name = user_data.get('last_name', '')

def load_user(user_id):
    user_data = users_col.find_one({'_id': user_id})
    return User(user_data) if user_data else None

def authenticate_user(email_or_username, password):
    user_data = users_col.find_one({"$or": [{"email": email_or_username}, {"username": email_or_username}]})
    if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data['password']):
        return User(user_data)
    return None

def create_user(email, username, password, first_name, last_name):
    if users_col.find_one({'email': email}):
        return None, 'Email already exists'
    if users_col.find_one({'username': username}):
        return None, 'Username already exists'
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    user_data = {
        'email': email,
        'username': username,
        'password': hashed_password,
        'first_name': first_name,
        'last_name': last_name
    }
    result = users_col.insert_one(user_data)
    user_data['_id'] = result.inserted_id
    return User(user_data), 'User created successfully'

def is_ajax_request():
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'

def premium_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or getattr(current_user, 'subscription_status', 'free') != 'premium':
            flash('Premium subscription required.', 'error')
            return redirect(url_for('core.pricing'))
        return f(*args, **kwargs)
    return decorated

def validate_image_file(file):
    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower()
    if ext not in {'.png', '.jpg', '.jpeg', '.gif'}:
        return False
    return True
