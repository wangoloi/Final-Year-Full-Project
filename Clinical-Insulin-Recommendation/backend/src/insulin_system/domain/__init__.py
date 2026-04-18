"""
Business logic layer: domain validation and rules.

No database or framework dependencies. Pure, testable logic.
"""

from .constants import (
    AGE_MAX,
    AGE_MIN,
    GENDER_VALUES,
)
from .validation import (
    ValidationError,
    get_required_fields_for_recommendation,
    validate_age,
    validate_assessment_input,
    validate_gender,
)

__all__ = [
    "AGE_MAX",
    "AGE_MIN",
    "GENDER_VALUES",
    "ValidationError",
    "validate_age",
    "validate_assessment_input",
    "validate_gender",
    "get_required_fields_for_recommendation",
]
