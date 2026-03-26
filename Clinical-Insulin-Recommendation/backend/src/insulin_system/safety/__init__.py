"""
Ethical and safety framework for GlucoSense Clinical Support.

- Audit logging for all predictions and recommendations
- Out-of-distribution and confidence checks
- Clinical disclaimer and human-in-the-loop requirements
"""

from .audit import audit_log, log_prediction
from .disclaimer import get_clinical_disclaimer

__all__ = ["audit_log", "log_prediction", "get_clinical_disclaimer"]
