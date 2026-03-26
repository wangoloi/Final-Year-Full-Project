"""Custom exceptions - clear error handling."""
from fastapi import HTTPException


class AppError(Exception):
    """Base application error."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ValidationError(AppError):
    """Validation failed."""

    def __init__(self, message: str):
        super().__init__(message, 400)


class NotFoundError(AppError):
    """Resource not found."""

    def __init__(self, message: str, status_code: int = 404):
        super().__init__(message, status_code)


class AuthError(AppError):
    """Authentication failed."""

    def __init__(self, message: str):
        super().__init__(message, 401)


def to_http_exception(exc: AppError) -> HTTPException:
    """Convert AppError to HTTPException."""
    return HTTPException(status_code=exc.status_code, detail=exc.message)
