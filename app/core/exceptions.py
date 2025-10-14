"""
Custom exceptions for the AI Image Editor application
Provides specific error types for better error handling
"""


class ImageEditorError(Exception):
    """Base exception for all image editor errors"""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code or 'GENERAL_ERROR'
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary for API responses"""
        return {
            'error': True,
            'message': self.message,
            'error_code': self.error_code,
            'details': self.details
        }


class ValidationError(ImageEditorError):
    """Raised when input validation fails"""
    
    def __init__(self, message: str, field: str = None, value=None):
        super().__init__(
            message=message,
            error_code='VALIDATION_ERROR',
            details={'field': field, 'value': value}
        )


class ProcessingError(ImageEditorError):
    """Raised when image processing fails"""
    
    def __init__(self, message: str, operation: str = None, filename: str = None):
        super().__init__(
            message=message,
            error_code='PROCESSING_ERROR',
            details={'operation': operation, 'filename': filename}
        )


class AuthenticationError(ImageEditorError):
    """Raised when authentication fails"""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_code='AUTH_ERROR'
        )


class AuthorizationError(ImageEditorError):
    """Raised when user lacks permission"""
    
    def __init__(self, message: str = "Access denied", required_permission: str = None):
        super().__init__(
            message=message,
            error_code='AUTHORIZATION_ERROR',
            details={'required_permission': required_permission}
        )


class FileNotFoundError(ImageEditorError):
    """Raised when a file is not found"""
    
    def __init__(self, filename: str):
        super().__init__(
            message=f"File not found: {filename}",
            error_code='FILE_NOT_FOUND',
            details={'filename': filename}
        )


class FileSizeError(ValidationError):
    """Raised when file size exceeds limits"""
    
    def __init__(self, size: int, max_size: int):
        super().__init__(
            message=f"File size {size} bytes exceeds maximum {max_size} bytes",
            field='file_size'
        )
        self.details.update({'size': size, 'max_size': max_size})


class FileTypeError(ValidationError):
    """Raised when file type is not allowed"""
    
    def __init__(self, file_type: str, allowed_types: list):
        super().__init__(
            message=f"File type '{file_type}' not allowed. Allowed types: {', '.join(allowed_types)}",
            field='file_type'
        )
        self.details.update({'file_type': file_type, 'allowed_types': allowed_types})


class UsageLimitError(ImageEditorError):
    """Raised when usage limits are exceeded"""
    
    def __init__(self, usage_type: str, limit: int, current: int):
        super().__init__(
            message=f"Usage limit exceeded for {usage_type}. Limit: {limit}, Current: {current}",
            error_code='USAGE_LIMIT_ERROR',
            details={'usage_type': usage_type, 'limit': limit, 'current': current}
        )


class SubscriptionError(ImageEditorError):
    """Raised when subscription-related errors occur"""
    
    def __init__(self, message: str, required_tier: str = None):
        super().__init__(
            message=message,
            error_code='SUBSCRIPTION_ERROR',
            details={'required_tier': required_tier}
        )


class AIServiceError(ImageEditorError):
    """Raised when AI service errors occur"""
    
    def __init__(self, message: str, service: str = None, status_code: int = None):
        super().__init__(
            message=message,
            error_code='AI_SERVICE_ERROR',
            details={'service': service, 'status_code': status_code}
        )


class QueueError(ImageEditorError):
    """Raised when queue operations fail"""
    
    def __init__(self, message: str, queue_name: str = None):
        super().__init__(
            message=message,
            error_code='QUEUE_ERROR',
            details={'queue_name': queue_name}
        )
