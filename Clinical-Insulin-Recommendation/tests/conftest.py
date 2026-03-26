"""Pytest fixtures for data processing tests."""

import sys
from pathlib import Path

import pandas as pd
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "src"))

from insulin_system.config.schema import DataSchema


@pytest.fixture
def schema():
    return DataSchema()


@pytest.fixture
def sample_raw_df(schema):
    """Minimal valid DataFrame matching schema."""
    return pd.DataFrame({
        schema.PATIENT_ID: [1, 2, 3],
        "gender": ["male", "female", "male"],
        "age": [30, 45, 60],
        "family_history": ["yes", "no", "yes"],
        "glucose_level": [100.0, 120.0, 140.0],
        "physical_activity": [5.0, 3.0, 7.0],
        "food_intake": ["high", "medium", "low"],
        "previous_medications": ["none", "oral", "insulin"],
        "BMI": [24.0, 28.0, 22.0],
        "HbA1c": [6.5, 7.2, 5.8],
        "weight": [70.0, 80.0, 65.0],
        "insulin_sensitivity": [1.0, 0.9, 1.1],
        "sleep_hours": [7.0, 6.0, 8.0],
        "creatinine": [0.9, 1.0, 1.1],
        "iob": [0.0, 0.0, 0.0],
        "anticipated_carbs": [0.0, 0.0, 0.0],
        schema.TARGET: ["steady", "up", "down"],
    })


@pytest.fixture
def data_path():
    return Path(__file__).resolve().parent.parent / "data" / "SmartSensor_DiabetesMonitoring.csv"
