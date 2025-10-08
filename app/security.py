from app import extensions
from flask_login import UserMixin
import bcrypt
from functools import wraps
from flask import request, flash, redirect, url_for
from flask_login import current_user
from werkzeug.utils import secure_filename
import os
from bson import ObjectId

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data.get('_id'))
        self.email = user_data.get('email')
        self.username = user_data.get('username')
        self.password_hash = user_data.get('password')
        self.first_name = user_data.get('first_name', '')
        self.last_name = user_data.get('last_name', '')
        self.role = user_data.get('role', 'user')
        self.subscription_status = user_data.get('subscription_status', 'free')


def is_admin(self):
        return self.role == 'admin'

def is_premium(self):
        return self.subscription_status == 'premium'
        

def load_user(user_id):
  
    try:
        user_data = extensions.db.users.find_one({'_id': ObjectId(user_id)})
    except Exception:
        user_data = extensions.db.users.find_one({'_id': user_id})

    if not user_data:
        return None

    ADMIN_EMAILS = {"yogeshbhongade17@gmail.com"}

    if user_data.get("email") in ADMIN_EMAILS:
        user_data["role"] = "admin"
        user_data["subscription_status"] = "premium"

    return User(user_data)

def authenticate_user(email_or_username, password):
    user_data = extensions.db.users.find_one({
        "$or": [{"email": email_or_username}, {"username": email_or_username}]
    })
    if not user_data:
        return None
    stored_hash = user_data.get('password') or user_data.get('password_hash')
    if not stored_hash:
        return None
    if isinstance(stored_hash, str):
        stored_hash = stored_hash.encode('utf-8')
    try:
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
            return User(user_data)
    except Exception:
        return None
    return None

def create_user(email, username, password, first_name, last_name):
    if extensions.db.users.find_one({'email': email}):
        return None, 'Email already exists'
    if extensions.db.users.find_one({'username': username}):
        return None, 'Username already exists'
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    user_data = {
        'email': email,
        'username': username,
        'password': hashed_password,
        'first_name': first_name,
        'last_name': last_name
    }
    result = extensions.db.users.insert_one(user_data)
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
