"""
Unit tests for GlucoSense API: schemas, validators, and endpoint behaviour.

Requires: pytest, fastapi, pydantic. Run with: pytest tests/test_api.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from insulin_system.api.schemas import PatientInput, PredictionResponse, CLINICAL_DISCLAIMER
from insulin_system.api.validators import validate_patient_input, patient_input_to_dataframe


def test_patient_input_to_row_dict():
    """PatientInput serializes to schema-ordered row dict."""
    p = PatientInput(
        patient_id="P001",
        age=45.0,
        glucose_level=120.0,
        BMI=25.0,
        gender="male",
    )
    row = p.to_row_dict()
    assert "patient_id" in row or "patient_id" in [k for k in row.keys() if "patient" in k.lower()]
    assert row.get("age") == 45.0
    assert row.get("glucose_level") == 120.0
    assert row.get("BMI") == 25.0


def test_validate_patient_input_accepts_minimal():
    """Validation accepts minimal required fields."""
    body = {
        "age": 50,
        "gender": "Male",
        "food_intake": "Medium",
        "previous_medications": "None",
        "glucose_level": 100,
        "BMI": 24,
    }
    patient, warnings, errors = validate_patient_input(body)
    assert isinstance(patient, PatientInput)
    assert patient.age == 50.0
    assert patient.glucose_level == 100.0
    assert not errors


def test_validate_patient_input_rejects_invalid():
    """Validation raises on invalid structure (e.g. not a dict)."""
    with pytest.raises((ValueError, TypeError, Exception)):
        validate_patient_input("not a dict")


def test_patient_input_to_dataframe():
    """patient_input_to_dataframe returns a single-row DataFrame."""
    p = PatientInput(age=30, glucose_level=110, BMI=22)
    df = patient_input_to_dataframe(p)
    assert len(df) == 1
    assert "age" in df.columns or "glucose_level" in df.columns


def test_clinical_disclaimer_present():
    """API responses include clinical disclaimer."""
    assert "clinical decision support" in CLINICAL_DISCLAIMER.lower()
    assert "healthcare professional" in CLINICAL_DISCLAIMER.lower()


def test_prediction_response_model():
    """PredictionResponse validates required fields."""
    r = PredictionResponse(
        predicted_class="steady",
        confidence=0.85,
        uncertainty_entropy=0.5,
        probability_breakdown={"steady": 0.85, "up": 0.1, "down": 0.03, "no": 0.02},
        feature_names_used=["age", "glucose_level"],
    )
    assert r.predicted_class == "steady"
    assert r.confidence == 0.85
    assert r.clinical_disclaimer
