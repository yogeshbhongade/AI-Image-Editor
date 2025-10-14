from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from app.core.config import get_config
from app.core.database import init_db
from app.models.user import UserService


def create_app(config_name=None):
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Load configuration
    config = get_config(config_name)
    app.config.from_object(config)
    
    # Validate configuration
    config_issues = config.validate_config()
    if config_issues:
        print("⚠️ Configuration issues found:")
        for issue in config_issues:
            print(f"  - {issue}")
    
    # Initialize database
    init_db(app)
    
    # Initialize CSRF protection
    csrf = CSRFProtect()
    csrf.init_app(app)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    # User loader for Flask-Login
    user_service = UserService()
    
    @login_manager.user_loader
    def load_user(user_id):
        return user_service.get_user_by_id(user_id)
    
    # Register blueprints
    from app.api import register_blueprints
    register_blueprints(app)
    
    # Register error handlers
    from app.api.error_handlers import register_error_handlers
    register_error_handlers(app)
    
    return app
