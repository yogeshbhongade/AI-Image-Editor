"""
Error handlers for the API
Provides consistent error responses across the application
"""

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from app.core.exceptions import (
    ImageEditorError, ValidationError, ProcessingError,
    AuthenticationError, AuthorizationError, FileNotFoundError,
    UsageLimitError, SubscriptionError, AIServiceError, QueueError
)


def register_error_handlers(app: Flask):
    """Register error handlers with the Flask app"""
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        if request.is_json or request.path.startswith('/api/'):
            return jsonify(e.to_dict()), 400
        return render_template('error.html', error=str(e)), 400
    
    @app.errorhandler(ProcessingError)
    def handle_processing_error(e):
        if request.is_json or request.path.startswith('/api/'):
            return jsonify(e.to_dict()), 500
        return render_template('error.html', error=str(e)), 500
    
    @app.errorhandler(AuthenticationError)
    def handle_auth_error(e):
        if request.is_json or request.path.startswith('/api/'):
            return jsonify(e.to_dict()), 401
        return render_template('login.html', error=str(e)), 401
    
    @app.errorhandler(AuthorizationError)
    def handle_authorization_error(e):
        if request.is_json or request.path.startswith('/api/'):
            return jsonify(e.to_dict()), 403
        return render_template('error.html', error=str(e)), 403
    
    @app.errorhandler(FileNotFoundError)
    def handle_file_not_found_error(e):
        if request.is_json or request.path.startswith('/api/'):
            return jsonify(e.to_dict()), 404
        return render_template('error.html', error=str(e)), 404
    
    @app.errorhandler(UsageLimitError)
    def handle_usage_limit_error(e):
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({**e.to_dict(), 'upgrade_required': True}), 429
        return render_template('pricing.html', error=str(e)), 429
    
    @app.errorhandler(SubscriptionError)
    def handle_subscription_error(e):
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({**e.to_dict(), 'upgrade_required': True}), 402
        return render_template('pricing.html', error=str(e)), 402
    
    @app.errorhandler(AIServiceError)
    def handle_ai_service_error(e):
        if request.is_json or request.path.startswith('/api/'):
            return jsonify(e.to_dict()), 503
        return render_template('error.html', error=str(e)), 503
    
    @app.errorhandler(QueueError)
    def handle_queue_error(e):
        if request.is_json or request.path.startswith('/api/'):
            return jsonify(e.to_dict()), 503
        return render_template('error.html', error=str(e)), 503
    
    @app.errorhandler(ImageEditorError)
    def handle_general_error(e):
        if request.is_json or request.path.startswith('/api/'):
            return jsonify(e.to_dict()), 500
        return render_template('error.html', error=str(e)), 500
    
    @app.errorhandler(404)
    def handle_404_error(e):
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'error': True,
                'message': 'Resource not found',
                'error_code': 'NOT_FOUND'
            }), 404
        return render_template('error.html', error='Page not found'), 404
    
    @app.errorhandler(500)
    def handle_500_error(e):
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'error': True,
                'message': 'Internal server error',
                'error_code': 'INTERNAL_ERROR'
            }), 500
        return render_template('error.html', error='Internal server error'), 500
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'error': True,
                'message': e.description,
                'error_code': e.name.upper().replace(' ', '_')
            }), e.code
        return render_template('error.html', error=e.description), e.code
    
    print("✅ Error handlers registered successfully")
