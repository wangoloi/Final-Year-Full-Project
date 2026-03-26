"""
Custom exceptions for the insulin dosage prediction system.

Enables precise error handling and testability without relying on generic exceptions.
"""


class InsulinSystemError(Exception):
    """Base exception for all package-specific errors."""

    pass


class DataValidationError(InsulinSystemError):
    """Raised when dataset validation fails (missing columns, invalid types, etc.)."""

    pass


class DataLoadError(InsulinSystemError):
    """Raised when dataset cannot be loaded (file not found, read error)."""

    pass


class ConfigurationError(InsulinSystemError):
    """Raised when configuration is invalid or inconsistent."""

    pass


class OutOfBoundsError(InsulinSystemError):
    """Raised when a value falls outside clinical or configured bounds."""

    pass


class PipelineError(InsulinSystemError):
    """Raised when a pipeline step fails."""

    pass
