"""
Data loading and validation module.

Handles CSV loading, schema validation, and contextual column injection.
"""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from .config import DataConfig

logger = logging.getLogger(__name__)


class DataLoader:
    """
    Loads the insulin dosage dataset from CSV and validates structure.

    Supports dependency injection of schema for testing.
    """

    def __init__(self, config: Optional[DataConfig] = None):
        self._config = config or DataConfig()

    def load(self, file_path: Path) -> pd.DataFrame:
        """
        Load dataset from CSV.

        Args:
            file_path: Path to CSV file.

        Returns:
            Raw DataFrame as read from CSV.

        Raises:
            FileNotFoundError: If file does not exist.
            ValueError: If CSV cannot be read.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found: {path}")

        df = pd.read_csv(path)
        self._inject_contextual_columns(df)
        logger.info("Loaded dataset from %s, shape=%s", path, df.shape)
        return df

    def _inject_contextual_columns(self, df: pd.DataFrame) -> None:
        """Add contextual columns with defaults if missing."""
        defaults = [
            ("iob", 0.0),
            ("anticipated_carbs", 0.0),
            ("glucose_trend", "stable"),
        ]
        for col, default in defaults:
            if col not in df.columns:
                df[col] = default
                logger.debug("Added missing contextual column %s with default %s", col, default)

    def validate(self, df: pd.DataFrame) -> None:
        """
        Validate that DataFrame has required columns and is non-empty.

        Raises:
            ValueError: If validation fails.
        """
        if df is None or not isinstance(df, pd.DataFrame):
            raise ValueError("Input must be a pandas DataFrame.")
        if df.empty:
            raise ValueError("DataFrame is empty.")

        required = {self._config.patient_id_col, self._config.target_col}
        required.update(self._config.categorical_cols)
        required.update(self._config.numeric_cols)
        required -= {"glucose_trend", "glucose_trend_encoded"}  # contextual, optional

        missing = required - set(df.columns)
        if missing:
            raise ValueError(
                f"Missing required columns: {sorted(missing)}. "
                f"Present: {sorted(df.columns)}"
            )
        if len(df.columns) != len(set(df.columns)):
            raise ValueError("Duplicate column names are not allowed.")
        logger.debug("Validation passed for DataFrame with columns %s", list(df.columns))

    def load_and_validate(self, file_path: Path) -> pd.DataFrame:
        """Load CSV and validate schema. Convenience method."""
        df = self.load(file_path)
        self.validate(df)
        return df


def load_dataset(path: Path, config: Optional[DataConfig] = None) -> pd.DataFrame:
    """
    Pure function: load and validate dataset.

    Args:
        path: Path to CSV file.
        config: Optional data configuration.

    Returns:
        Validated DataFrame.
    """
    loader = DataLoader(config=config)
    return loader.load_and_validate(path)
