"""
Patient context update from request body.

Single responsibility: upsert patient context from API body.
"""
from typing import Any, Dict

from ..storage import upsert_patient_context


def update_patient_context_from_body(body: Dict[str, Any]) -> None:
    """Extract patient context from body and upsert to storage."""
    name = body.get("patient_name") or "Current Patient"
    condition = body.get("condition") or "Type 1 Diabetes"
    gl = body.get("glucose_level")
    carbs = body.get("carbohydrates") or body.get("food_intake")
    activity = body.get("physical_activity")

    has_updates = gl is not None or carbs is not None or activity is not None or name or condition
    if not has_updates:
        return

    try:
        upsert_patient_context(
            name=str(name),
            condition=str(condition),
            glucose=int(gl) if gl is not None else None,
            carbohydrates=_safe_int(carbs),
            activity_minutes=_safe_int(activity),
        )
    except Exception:
        pass


def _safe_int(val: Any) -> int | None:
    """Coerce to int if valid; else None."""
    if val is None:
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, str) and val.isdigit():
        return int(val)
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return None
