"""
API package for AI Image Editor
Contains all route blueprints and API endpoints
"""

from flask import Flask

from .auth import auth_bp
from .core import core_bp
from .images import images_bp
from .ai import ai_bp
from .admin import admin_bp
from .subscription import subscription_bp


def register_blueprints(app: Flask):
    """Register all blueprints with the Flask app"""
    
    # Core routes (home, dashboard, etc.)
    app.register_blueprint(core_bp)
    
    # Authentication routes
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # Image processing routes
    app.register_blueprint(images_bp, url_prefix='/api/images')
    
    # AI routes
    app.register_blueprint(ai_bp, url_prefix='/api/ai')
    
    # Subscription/Payment routes
    app.register_blueprint(subscription_bp)
    
    # Admin routes
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    print("✅ All blueprints registered successfully")
