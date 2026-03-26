"""
Clinical safety disclaimer and human-in-the-loop messaging.

All API responses include a disclaimer. This module centralizes the text
and any future localization or customization.
"""

CLINICAL_DISCLAIMER = (
    "This system is a clinical decision support tool, not an autonomous diagnostic system. "
    "All recommendations must be reviewed by a qualified healthcare professional. "
    "The system should not be used as the sole basis for treatment decisions. "
    "Regular validation against clinical outcomes is required."
)


def get_clinical_disclaimer() -> str:
    """Return the standard clinical disclaimer for display in API and UI."""
    return CLINICAL_DISCLAIMER
