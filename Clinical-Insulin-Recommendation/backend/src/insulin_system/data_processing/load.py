"""
Data loading and validation module.

Single responsibility: load CSV and validate schema/types so that
downstream steps receive a validated DataFrame (or raise clear errors).
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from ..config.schema import ClinicalBounds, DataSchema

# Insulin dose derivation formula: clipping bounds and scaling factors
DERIVE_WEIGHT_CLIP_LOWER_KG = 30
DERIVE_WEIGHT_CLIP_UPPER_KG = 200
DERIVE_GLUCOSE_CLIP_LOWER_MGDL = 70
DERIVE_GLUCOSE_CLIP_UPPER_MGDL = 300
DERIVE_HBA1C_CLIP_LOWER_PCT = 4
DERIVE_HBA1C_CLIP_UPPER_PCT = 15
DERIVE_SENSITIVITY_CLIP_LOWER = 0.3
DERIVE_SENSITIVITY_CLIP_UPPER = 2.0
DERIVE_BASE_WEIGHT_FACTOR = 0.5
DERIVE_GLUCOSE_NORMALIZER = 100
DERIVE_HBA1C_NORMALIZER = 6
DERIVE_SENSITIVITY_OFFSET = 0.3
DERIVE_CAT_SCALE_NO = 0.3
DERIVE_CAT_SCALE_DOWN = 0.7
DERIVE_CAT_SCALE_STEADY = 1.0
DERIVE_CAT_SCALE_UP = 1.4
DERIVE_CAT_SCALE_FILLNA = 1.0
DERIVE_INSULIN_DOSE_CLIP_LOWER = 2.0
DERIVE_INSULIN_DOSE_CLIP_UPPER = 120.0
from ..exceptions import DataLoadError, DataValidationError

logger = logging.getLogger(__name__)


def _insulin_class_from_dose(dose: pd.Series) -> pd.Series:
    """
    Map continuous insulin units to 4-way labels expected by the classifier (no/down/steady/up).

    Zero or missing dose -> "no"; positive doses split by tertiles among rows with dose > 0.
    """
    d = pd.to_numeric(dose, errors="coerce").fillna(0.0)
    out = pd.Series("no", index=d.index, dtype=object)
    pos = d > 0
    if not pos.any():
        return out
    pos_vals = d[pos]
    if pos_vals.nunique() == 1:
        out.loc[pos] = "steady"
        return out
    p33, p66 = np.percentile(pos_vals, [100 / 3, 200 / 3])
    out.loc[pos & (d <= p33)] = "down"
    out.loc[pos & (d > p33) & (d <= p66)] = "steady"
    out.loc[pos & (d > p66)] = "up"
    return out


def normalize_smart_sensor_to_schema(df: pd.DataFrame, schema: Optional[DataSchema] = None) -> pd.DataFrame:
    """
    Convert SmartSensor_DiabetesMonitoring.csv layout to canonical DataSchema columns.

    The bundled dataset uses Patient_ID, Glucose_Level, Activity_Level, etc.
    The ML pipeline was built for a synthetic schema (patient_id, glucose_level, …).
    This maps and synthesizes missing clinical fields so downstream steps stay unchanged.
    """
    sch = schema or DataSchema()
    bounds = ClinicalBounds()
    if df.empty or "Glucose_Level" not in df.columns:
        return df

    out = pd.DataFrame(index=df.index)
    out[sch.PATIENT_ID] = df["Patient_ID"].astype(str)
    out["glucose_level"] = pd.to_numeric(df["Glucose_Level"], errors="coerce")
    out["BMI"] = pd.to_numeric(df["BMI"], errors="coerce")
    out["HbA1c"] = pd.to_numeric(df["HbA1c"], errors="coerce")
    act = pd.to_numeric(df["Activity_Level"], errors="coerce").fillna(0.0).clip(0, 100)
    out["physical_activity"] = act * (15.0 / 100.0)
    out["sleep_hours"] = pd.to_numeric(df["Sleep_Duration"], errors="coerce")
    dose = pd.to_numeric(df["Insulin_Dose"], errors="coerce").fillna(0.0)
    out[sch.TARGET_REGRESSION] = dose

    out["age"] = 45.0
    out["weight"] = (out["BMI"] * 2.89).clip(float(bounds.WEIGHT[0]), float(bounds.WEIGHT[1]))
    out["insulin_sensitivity"] = 1.0
    out["creatinine"] = 1.0
    out["gender"] = "unspecified"
    out["family_history"] = "unspecified"
    out["food_intake"] = "unspecified"
    if "Medication_Intake" in df.columns:
        out["previous_medications"] = (
            pd.to_numeric(df["Medication_Intake"], errors="coerce")
            .fillna(0)
            .map({0: "none", 1: "active"})
            .fillna("none")
        )
    else:
        out["previous_medications"] = "none"

    out[sch.TARGET] = _insulin_class_from_dose(dose)

    logger.info(
        "Normalized SmartSensor CSV to canonical schema (rows=%s, Insulin distribution=%s)",
        len(out),
        out[sch.TARGET].value_counts().to_dict(),
    )
    return out


class DataLoader:
    """
    Loads the insulin dosage dataset from CSV and validates structure.

    Dependency injection: schema and path are injectable for testing.
    """

    def __init__(
        self,
        schema: Optional[DataSchema] = None,
        file_path: Optional[Path] = None,
    ) -> None:
        self._schema = schema or DataSchema()
        self._file_path = file_path

    def load(self, file_path: Optional[Path] = None) -> pd.DataFrame:
        """
        Load dataset from CSV.

        Args:
            file_path: Override path for this call. If None, uses instance path.

        Returns:
            Raw DataFrame as read from CSV.

        Raises:
            DataLoadError: If file is missing or cannot be read.
        """
        path = file_path or self._file_path
        if path is None:
            raise DataLoadError("No file path provided to load.")

        path = Path(path)
        if not path.exists():
            raise DataLoadError(f"Dataset file not found: {path}")

        try:
            df = pd.read_csv(path)
        except Exception as e:
            raise DataLoadError(f"Failed to read CSV from {path}: {e}") from e

        df = normalize_smart_sensor_to_schema(df, self._schema)

        # Add contextual columns if missing (training data typically lacks them; inference provides real values)
        for col, default in [("iob", 0.0), ("anticipated_carbs", 0.0), ("glucose_trend", "stable")]:
            if col not in df.columns:
                df[col] = default
                logger.debug("Added missing contextual column %s with default %s", col, default)

        logger.info("Loaded dataset from %s, shape=%s", path, df.shape)
        return df

    def validate(self, df: pd.DataFrame) -> None:
        """
        Validate that DataFrame has required columns and non-empty.

        Raises:
            DataValidationError: If validation fails.
        """
        if df is None or not isinstance(df, pd.DataFrame):
            raise DataValidationError("Input must be a pandas DataFrame.")

        if df.empty:
            raise DataValidationError("DataFrame is empty.")

        required = set(self._schema.all_columns)
        # Contextual columns are optional at load; added by load() if missing
        contextual = set(getattr(self._schema, "CONTEXTUAL_NUMERIC", ())) | {"glucose_trend"}
        required = required - contextual
        missing = required - set(df.columns)
        if missing:
            raise DataValidationError(
                f"Missing required columns: {sorted(missing)}. "
                f"Present: {sorted(df.columns)}"
            )

        # Check for duplicate column names
        if len(df.columns) != len(set(df.columns)):
            raise DataValidationError("Duplicate column names are not allowed.")

        logger.debug("Validation passed for DataFrame with columns %s", list(df.columns))

    def load_and_validate(self, file_path: Optional[Path] = None) -> pd.DataFrame:
        """
        Load CSV and validate schema. Convenience method.

        Returns:
            Validated raw DataFrame.
        """
        df = self.load(file_path)
        self.validate(df)
        return df


def load_and_validate(
    file_path: Path,
    schema: Optional[DataSchema] = None,
) -> pd.DataFrame:
    """
    Pure function entry point: load and validate in one call.

    Useful for tests and scripts that do not need a loader instance.
    """
    loader = DataLoader(schema=schema, file_path=file_path)
    return loader.load_and_validate(file_path)


def derive_insulin_dose(df: pd.DataFrame, schema: Optional[DataSchema] = None) -> pd.DataFrame:
    """
    Derive continuous Insulin_Dose (units) when not present in the dataset.

    Uses a clinical-style formula: base from weight, adjusted by glucose, HbA1c,
    and insulin_sensitivity (lower sensitivity → higher dose), with categorical
    Insulin providing realistic variation.
    """
    sch = schema or DataSchema()
    out = df.copy()
    if sch.TARGET_REGRESSION in out.columns:
        return out
    w = out["weight"].clip(lower=DERIVE_WEIGHT_CLIP_LOWER_KG, upper=DERIVE_WEIGHT_CLIP_UPPER_KG)
    g = out["glucose_level"].clip(lower=DERIVE_GLUCOSE_CLIP_LOWER_MGDL, upper=DERIVE_GLUCOSE_CLIP_UPPER_MGDL)
    h = out["HbA1c"].clip(lower=DERIVE_HBA1C_CLIP_LOWER_PCT, upper=DERIVE_HBA1C_CLIP_UPPER_PCT)
    sens = out["insulin_sensitivity"].clip(lower=DERIVE_SENSITIVITY_CLIP_LOWER, upper=DERIVE_SENSITIVITY_CLIP_UPPER)
    base = w * DERIVE_BASE_WEIGHT_FACTOR * (g / DERIVE_GLUCOSE_NORMALIZER) * (h / DERIVE_HBA1C_NORMALIZER) / (sens + DERIVE_SENSITIVITY_OFFSET)
    if sch.TARGET in out.columns:
        cat_scale = out[sch.TARGET].map({"no": DERIVE_CAT_SCALE_NO, "down": DERIVE_CAT_SCALE_DOWN, "steady": DERIVE_CAT_SCALE_STEADY, "up": DERIVE_CAT_SCALE_UP})
        cat_scale = cat_scale.fillna(DERIVE_CAT_SCALE_FILLNA)
        base = base * cat_scale
    out[sch.TARGET_REGRESSION] = base.clip(lower=DERIVE_INSULIN_DOSE_CLIP_LOWER, upper=DERIVE_INSULIN_DOSE_CLIP_UPPER)
    return out
