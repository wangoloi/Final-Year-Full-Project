from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

import pandas as pd

from ..config.schema import DataSchema
from ..exceptions import DataValidationError


def _required_columns(schema: DataSchema) -> Sequence[str]:
    # Training uses all feature columns; inference can add defaults later.
    # For loading/validation we enforce the core set plus common contextual inputs.
    core = [schema.PATIENT_ID, *schema.CATEGORICAL, *schema.NUMERIC, schema.TARGET]
    # Contextual inputs are expected for training data, but are optional for inference.
    for c in getattr(schema, "CONTEXTUAL_IMPUTE", ()):
        if c not in core:
            core.append(c)
    return core


@dataclass
class DataLoader:
    schema: DataSchema
    file_path: Optional[Path] = None

    def validate(self, df: pd.DataFrame) -> None:
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            raise DataValidationError("Empty dataset")
        missing = [c for c in _required_columns(self.schema) if c not in df.columns]
        if missing:
            raise DataValidationError(f"Missing required columns: {', '.join(missing)}")

    def load_and_validate(self, file_path: Optional[Path] = None) -> pd.DataFrame:
        path = Path(file_path or self.file_path or "")
        if not path or not path.exists():
            raise DataValidationError(f"File not found: {path}")
        df = pd.read_csv(path)
        self.validate(df)
        return df


def load_and_validate(file_path: Path, schema: Optional[DataSchema] = None) -> pd.DataFrame:
    """Convenience wrapper used by notebooks/tests."""
    loader = DataLoader(schema=schema or DataSchema(), file_path=Path(file_path))
    return loader.load_and_validate()

