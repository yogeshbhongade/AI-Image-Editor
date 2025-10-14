"""
User model and service layer
Handles all user-related database operations and business logic
"""

from flask_login import UserMixin
from datetime import datetime
from bson import ObjectId
import bcrypt
from typing import Optional, Dict, Any

class User(UserMixin):
    """User model for Flask-Login integration"""
    
    def __init__(self, user_data: Dict[str, Any]):
        self.id = str(user_data.get('_id'))
        self.email = user_data.get('email')
        self.username = user_data.get('username')
        self.password_hash = user_data.get('password')
        self.first_name = user_data.get('first_name', '')
        self.last_name = user_data.get('last_name', '')
        self.role = user_data.get('role', 'user')
        self.subscription_status = user_data.get('subscription_status', 'free')
        self.created_at = user_data.get('created_at')
        self.last_login = user_data.get('last_login')
    
    @property
    def is_premium(self) -> bool:
        """Check if user has premium subscription"""
        return self.subscription_status == 'premium'
    
    @property
    def is_admin(self) -> bool:
        """Check if user is admin"""
        return self.role == 'admin'
    
    @property
    def full_name(self) -> str:
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}".strip()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role,
            'subscription_status': self.subscription_status,
            'full_name': self.full_name,
            'is_premium': self.is_premium,
            'is_admin': self.is_admin
        }


class UserService:
    """Service layer for user operations"""
    
    def __init__(self):
        self._db = None
        self._users_collection = None
        
        # Admin emails (should be moved to config)
        self.admin_emails = {"yogeshbhongade17@gmail.com"}
    
    @property
    def db(self):
        if self._db is None:
            from app.core.database import get_db
            self._db = get_db()
        return self._db
    
    @property
    def users_collection(self):
        if self._users_collection is None:
            self._users_collection = self.db.users
        return self._users_collection
    
    def create_user(self, email: str, username: str, password: str, 
                   first_name: str = '', last_name: str = '') -> tuple[Optional[User], str]:
        """Create a new user"""
        try:
            # Check if email exists
            if self.users_collection.find_one({'email': email}):
                return None, 'Email already exists'
            
            # Check if username exists
            if self.users_collection.find_one({'username': username}):
                return None, 'Username already exists'
            
            # Hash password
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            # Create user document
            user_data = {
                'email': email,
                'username': username,
                'password': hashed_password,
                'first_name': first_name,
                'last_name': last_name,
                'subscription_status': 'free',
                'role': 'admin' if email in self.admin_emails else 'user',
                'created_at': datetime.utcnow(),
                'last_login': None
            }
            
            # Insert user
            result = self.users_collection.insert_one(user_data)
            user_data['_id'] = result.inserted_id
            
            return User(user_data), 'User created successfully'
            
        except Exception as e:
            return None, f'Failed to create user: {str(e)}'
    
    def authenticate_user(self, email_or_username: str, password: str) -> Optional[User]:
        """Authenticate user with email/username and password"""
        try:
            # Find user by email or username
            user_data = self.users_collection.find_one({
                "$or": [{"email": email_or_username}, {"username": email_or_username}]
            })
            
            if not user_data:
                return None
            
            # Check password
            stored_hash = user_data.get('password') or user_data.get('password_hash')
            if not stored_hash:
                return None
            
            if isinstance(stored_hash, str):
                stored_hash = stored_hash.encode('utf-8')
            
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                # Update last login
                self.users_collection.update_one(
                    {'_id': user_data['_id']},
                    {'$set': {'last_login': datetime.utcnow()}}
                )
                
                # Apply admin privileges if needed
                if user_data.get("email") in self.admin_emails:
                    user_data["role"] = "admin"
                    user_data["subscription_status"] = "premium"
                
                return User(user_data)
            
            return None
            
        except Exception:
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            # Try ObjectId first
            try:
                user_data = self.users_collection.find_one({'_id': ObjectId(user_id)})
            except:
                user_data = self.users_collection.find_one({'_id': user_id})
            
            if not user_data:
                return None
            
            # Apply admin privileges if needed
            if user_data.get("email") in self.admin_emails:
                user_data["role"] = "admin"
                user_data["subscription_status"] = "premium"
            
            return User(user_data)
            
        except Exception:
            return None
    
    def update_subscription(self, user_id: str, subscription_status: str) -> bool:
        """Update user subscription status"""
        try:
            result = self.users_collection.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {'subscription_status': subscription_status}}
            )
            return result.modified_count > 0
        except Exception:
            return False
    
    def get_user_stats(self, user_id: str) -> Dict[str, int]:
        """Get user statistics"""
        try:
            from app.core.database import get_db
            db = get_db()
            
            stats = {
                'uploads': db.uploads.count_documents({'uploaded_by': user_id}),
                'processed': db.processed.count_documents({'created_by': user_id}),
                'downloads': db.downloads.count_documents({'user_id': user_id})
            }
            
            return stats
        except Exception:
            return {'uploads': 0, 'processed': 0, 'downloads': 0}
