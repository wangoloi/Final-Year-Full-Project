"""
Business logic layer: domain validation and rules.

No database or framework dependencies. Pure, testable logic.
"""

from .constants import (
    AGE_MAX,
    AGE_MIN,
    FOOD_INTAKE_VALUES,
    GENDER_VALUES,
    MEDICATION_NAME_MAX_LENGTH,
    PREVIOUS_MEDICATION_VALUES,
)
from .validation import (
    ValidationError,
    get_required_fields_for_recommendation,
    validate_age,
    validate_assessment_input,
    validate_food_intake,
    validate_gender,
    validate_medication_name,
    validate_previous_medication,
)

__all__ = [
    "AGE_MAX",
    "AGE_MIN",
    "FOOD_INTAKE_VALUES",
    "GENDER_VALUES",
    "MEDICATION_NAME_MAX_LENGTH",
    "PREVIOUS_MEDICATION_VALUES",
    "ValidationError",
    "validate_age",
    "validate_assessment_input",
    "validate_food_intake",
    "validate_gender",
    "validate_medication_name",
    "validate_previous_medication",
    "get_required_fields_for_recommendation",
]
