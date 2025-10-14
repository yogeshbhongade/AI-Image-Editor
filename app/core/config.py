"""
Configuration management
Centralized configuration for the application
"""

import os
from dotenv import load_dotenv
from typing import List

# Load environment variables
load_dotenv()


class Config:
    """Application configuration class"""
    
    # Flask Configuration
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database Configuration
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
    MONGO_DB = os.getenv('MONGO_DB', 'image_editor')
    
    # Redis Configuration
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
    
    # Queue Configuration
    RQ_QUEUE_NAME = os.getenv('RQ_QUEUE_NAME', 'image_tasks')
    RQ_JOB_TIMEOUT = int(os.getenv('RQ_JOB_TIMEOUT', 300))
    
    # File Upload Configuration
    MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', 10))
    MAX_FILES_PER_USER = int(os.getenv('MAX_FILES_PER_USER', 100))
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # Directory Configuration
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    UPLOAD_FOLDER = os.path.abspath(os.path.join(BASE_DIR, 'uploads'))
    PROCESSED_FOLDER = os.path.abspath(os.path.join(BASE_DIR, 'processed'))
    
    # Security Configuration
    ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost').split(',')
    CONTENT_SECURITY_POLICY = os.getenv(
        'CONTENT_SECURITY_POLICY',
        "default-src 'self'; img-src 'self' data: blob: https:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' fonts.googleapis.com cdnjs.cloudflare.com; font-src 'self' fonts.gstatic.com cdnjs.cloudflare.com; connect-src 'self' https:; frame-src https:; object-src 'none'; media-src 'self' https:;"
    )
    
    # Session Configuration
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1', 'yes')
    SESSION_COOKIE_HTTPONLY = os.getenv('SESSION_COOKIE_HTTPONLY', 'True').lower() in ('true', '1', 'yes')
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
    SESSION_PERMANENT = os.getenv('SESSION_PERMANENT', 'False').lower() in ('true', '1', 'yes')
    
    # Rate Limiting
    RATE_LIMIT_STORAGE_URL = os.getenv('RATE_LIMIT_STORAGE_URL')
    
    # AI Configuration
    HF_API_TOKEN = os.getenv('HF_API_TOKEN')
    HF_MODEL = os.getenv('HF_MODEL', 'stabilityai/stable-diffusion-xl-base-1.0')
    AI_PRIMARY_PROVIDER = os.getenv('AI_PRIMARY_PROVIDER', 'huggingface')
    AI_FALLBACK_PROVIDER = os.getenv('AI_FALLBACK_PROVIDER', '')
    AI_MAX_RETRIES = int(os.getenv('AI_MAX_RETRIES', 2))
    
    # Payment Configuration (Razorpay)
    RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID')
    RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET')
    RAZORPAY_WEBHOOK_SECRET = os.getenv('RAZORPAY_WEBHOOK_SECRET')
    RAZORPAY_CURRENCY = os.getenv('RAZORPAY_CURRENCY', 'INR')
    PREMIUM_PLAN_AMOUNT = int(os.getenv('PREMIUM_PLAN_AMOUNT', '29900'))  # Amount in paise
    PREMIUM_PLAN_INTERVAL = os.getenv('PREMIUM_PLAN_INTERVAL', 'monthly')
    PAYMENT_SUCCESS_URL = os.getenv('PAYMENT_SUCCESS_URL', 'http://localhost:5000/payment/success')
    PAYMENT_CANCEL_URL = os.getenv('PAYMENT_CANCEL_URL', 'http://localhost:5000/payment/cancel')
    RAZORPAY_PLAN_ID = os.getenv('RAZORPAY_PLAN_ID')
    
    # Image Processing Configuration
    MAX_IMAGE_DIMENSION = int(os.getenv('MAX_IMAGE_DIMENSION', 5000))
    JPEG_QUALITY = int(os.getenv('JPEG_QUALITY', 90))
    
    # Admin Configuration
    ADMIN_EMAILS = set(os.getenv('ADMIN_EMAILS', 'yogeshbhongade17@gmail.com').split(','))
    
    @classmethod
    def validate_config(cls) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        # Check required directories
        for folder in [cls.UPLOAD_FOLDER, cls.PROCESSED_FOLDER]:
            if not os.path.exists(folder):
                try:
                    os.makedirs(folder, exist_ok=True)
                except Exception as e:
                    issues.append(f"Cannot create directory {folder}: {e}")
        
        # Check AI configuration
        if not cls.HF_API_TOKEN:
            issues.append("HF_API_TOKEN not configured - AI features will not work")
        
        # Check payment configuration
        if not cls.RAZORPAY_KEY_ID or not cls.RAZORPAY_KEY_SECRET:
            issues.append("Razorpay credentials not configured - payments will not work")
        
        # Check file size limits
        if cls.MAX_FILE_SIZE_MB > 50:
            issues.append("MAX_FILE_SIZE_MB is very large - consider reducing for better performance")
        
        return issues
    
    @classmethod
    def get_upload_path(cls, filename: str) -> str:
        """Get full path for uploaded file"""
        return os.path.join(cls.UPLOAD_FOLDER, filename)
    
    @classmethod
    def get_processed_path(cls, filename: str) -> str:
        """Get full path for processed file"""
        return os.path.join(cls.PROCESSED_FOLDER, filename)


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    MONGO_DB = 'image_editor_test'


# Configuration mapping
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(config_name: str = None) -> Config:
    """Get configuration class based on environment"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'default')
    
    return config_map.get(config_name, DevelopmentConfig)
