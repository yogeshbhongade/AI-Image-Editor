import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'supersecretkey')
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
    MONGO_DB = os.getenv('MONGO_DB', 'image_editor')
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
    RQ_QUEUE_NAME = os.getenv('RQ_QUEUE_NAME', 'image_tasks')
    RQ_JOB_TIMEOUT = int(os.getenv('RQ_JOB_TIMEOUT', 300))
    MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', 10))
    MAX_FILES_PER_USER = int(os.getenv('MAX_FILES_PER_USER', 100))
    ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost').split(',')
    UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '../uploads'))
    PROCESSED_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '../processed'))
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    CONTENT_SECURITY_POLICY = os.getenv('CONTENT_SECURITY_POLICY', "default-src 'self'; img-src 'self' data: blob: https://lh3.googleusercontent.com https://razorpay.com https://checkout.razorpay.com; script-src 'self' 'unsafe-inline' checkout.razorpay.com; style-src 'self' 'unsafe-inline' fonts.googleapis.com; style-src-elem 'self' cdnjs.cloudflare.com; font-src 'self' fonts.gstatic.com cdnjs.cloudflare.com; connect-src 'self' https:; frame-src https://api.razorpay.com; object-src 'none'; media-src 'self' https:;")
    # Razorpay
    RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID')
    RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET')
    RAZORPAY_WEBHOOK_SECRET = os.getenv('RAZORPAY_WEBHOOK_SECRET')
    RAZORPAY_CURRENCY = os.getenv('RAZORPAY_CURRENCY', 'INR')
    PREMIUM_PLAN_AMOUNT = int(os.getenv('PREMIUM_PLAN_AMOUNT', '29900'))
    PREMIUM_PLAN_INTERVAL = os.getenv('PREMIUM_PLAN_INTERVAL', 'monthly')
    PAYMENT_SUCCESS_URL = os.getenv('PAYMENT_SUCCESS_URL', 'http://localhost:5000/payment/success')
    PAYMENT_CANCEL_URL = os.getenv('PAYMENT_CANCEL_URL', 'http://localhost:5000/payment/cancel')
    RAZORPAY_PLAN_ID = os.getenv('RAZORPAY_PLAN_ID')
    # AI Providers
    HF_API_TOKEN = os.getenv('HF_API_TOKEN')
    HF_MODEL = os.getenv('HF_MODEL', 'stabilityai/stable-diffusion-xl-base-1.0')
    AI_PRIMARY_PROVIDER = os.getenv('AI_PRIMARY_PROVIDER', 'huggingface')
    AI_FALLBACK_PROVIDER = os.getenv('AI_FALLBACK_PROVIDER', '')
    AI_MAX_RETRIES = int(os.getenv('AI_MAX_RETRIES', 2))
    # Security
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True').lower() in ('true', '1', 'yes')
    SESSION_COOKIE_HTTPONLY = os.getenv('SESSION_COOKIE_HTTPONLY', 'True').lower() in ('true', '1', 'yes')
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
    SESSION_PERMANENT = os.getenv('SESSION_PERMANENT', 'False').lower() in ('true', '1', 'yes')
    RATE_LIMIT_STORAGE_URL = os.getenv('RATE_LIMIT_STORAGE_URL')
