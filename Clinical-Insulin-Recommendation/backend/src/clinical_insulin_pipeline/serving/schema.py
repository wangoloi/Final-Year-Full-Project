"""
Structured input schema for inference (matches training feature engineering).
System-generated timestamp is decomposed to cyclical features by the bundle preprocessor.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class InsulinPredictionInput:
    """User-facing fields aligned with Ugandan clinical UI prompts."""

    # Timestamp for cyclical encoding (defaults to "now" if omitted)
    timestamp: Optional[datetime] = None

    # Biometrics
    age_years: Optional[float] = None  # not in CSV; optional extension
    bmi: float = 25.0
    hba1c: float = 6.5
    blood_pressure_systolic: float = 130.0
    blood_pressure_diastolic: float = 80.0

    # Wearable / lifestyle (dataset columns)
    glucose_level: float = 120.0
    heart_rate: float = 70.0
    activity_level: float = 50.0
    calories_burned: float = 200.0
    sleep_duration: float = 7.0
    step_count: float = 5000.0
    diet_quality_score: float = 7.0
    stress_level: float = 5.0
    medication_intake: int = 0  # 0/1

    extra: Dict[str, Any] = field(default_factory=dict)

    def to_feature_row_dict(self) -> Dict[str, Any]:
        """Build a single-row dict of raw sensor/clinical fields (before time decomposition)."""
        ts = self.timestamp or datetime.now()
        return {
            "Timestamp": ts,
            "Glucose_Level": self.glucose_level,
            "Heart_Rate": self.heart_rate,
            "Activity_Level": self.activity_level,
            "Calories_Burned": self.calories_burned,
            "Sleep_Duration": self.sleep_duration,
            "Step_Count": self.step_count,
            "Medication_Intake": int(self.medication_intake),
            "Diet_Quality_Score": self.diet_quality_score,
            "Stress_Level": self.stress_level,
            "BMI": self.bmi,
            "HbA1c": self.hba1c,
            "Blood_Pressure_Systolic": self.blood_pressure_systolic,
            "Blood_Pressure_Diastolic": self.blood_pressure_diastolic,
            **self.extra,
        }


def postprocess_dose(raw: float) -> float:
    """Clamp to [0, 10] and round to nearest 0.5 IU."""
    from ..config import DOSE_MAX, DOSE_MIN, DOSE_ROUND_STEP

    x = max(DOSE_MIN, min(DOSE_MAX, float(raw)))
    return round(x / DOSE_ROUND_STEP) * DOSE_ROUND_STEP
