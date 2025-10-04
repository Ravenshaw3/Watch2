"""Custom exceptions for the Watch2 Media Server."""

from fastapi import HTTPException, status


class MediaServerException(Exception):
    """Base exception for Watch2 Media Server."""
    
    def __init__(self, detail: str, error_code: str = None, status_code: int = 500):
        self.detail = detail
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(detail)


class MediaFileNotFound(MediaServerException):
    """Raised when a media file is not found"""
    
    def __init__(self, file_id: str):
        super().__init__(
            detail=f"Media file with ID {file_id} not found",
            error_code="MEDIA_FILE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND
        )


class UnsupportedMediaFormat(MediaServerException):
    """Raised when media format is not supported"""
    
    def __init__(self, format: str):
        super().__init__(
            detail=f"Unsupported media format: {format}",
            error_code="UNSUPPORTED_MEDIA_FORMAT",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class MediaProcessingError(MediaServerException):
    """Raised when media processing fails"""
    
    def __init__(self, detail: str):
        super().__init__(
            detail=f"Media processing error: {detail}",
            error_code="MEDIA_PROCESSING_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class UserNotFound(MediaServerException):
    """Raised when user is not found"""
    
    def __init__(self, user_id: str):
        super().__init__(
            detail=f"User with ID {user_id} not found",
            error_code="USER_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND
        )


class AuthenticationError(MediaServerException):
    """Raised when authentication fails"""
    
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            detail=detail,
            error_code="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class AuthorizationError(MediaServerException):
    """Raised when authorization fails"""
    
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            detail=detail,
            error_code="AUTHORIZATION_ERROR",
            status_code=status.HTTP_403_FORBIDDEN
        )


class ValidationError(MediaServerException):
    """Raised when validation fails"""
    
    def __init__(self, detail: str):
        super().__init__(
            detail=detail,
            error_code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )
