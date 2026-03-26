"""
Phase 8: Experiment tracking - log results, compare iterations, track best model.

Uses multi-objective scoring for model selection (not clinical_cost alone)
to avoid selecting overly conservative models that sacrifice F1 for low cost.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .config import is_better_by_rank

logger = logging.getLogger(__name__)


@dataclass
class ExperimentRecord:
    """Single experiment record."""

    experiment_id: str
    timestamp: str
    model: str
    calibration_method: str  # "none", "sigmoid", "isotonic"
    imbalance_strategy: str
    hyperparameters: Dict[str, Any]
    accuracy: float
    f1_weighted: float
    f1_macro: float
    roc_auc: float
    clinical_cost: float
    overfitting_gap: float  # train_score - val_score
    threshold_optimized: bool
    notes: str = ""


class ExperimentTracker:
    """Track experiments and maintain best model selection."""

    def __init__(self, output_dir: Path = Path("outputs/clinical_ml_experiments")):
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._records: List[ExperimentRecord] = []
        self._best_record: Optional[ExperimentRecord] = None
        self._experiment_table_path = self._output_dir / "experiment_table.csv"

    def log(
        self,
        experiment_id: str,
        model: str,
        imbalance_strategy: str,
        hyperparameters: Dict[str, Any],
        accuracy: float,
        f1_weighted: float,
        f1_macro: float,
        roc_auc: float,
        clinical_cost: float,
        overfitting_gap: float,
        threshold_optimized: bool = False,
        calibration_method: str = "none",
        notes: str = "",
    ) -> None:
        """Log one experiment."""
        record = ExperimentRecord(
            experiment_id=experiment_id,
            timestamp=datetime.now().isoformat(),
            model=model,
            calibration_method=calibration_method,
            imbalance_strategy=imbalance_strategy,
            hyperparameters=hyperparameters,
            accuracy=accuracy,
            f1_weighted=f1_weighted,
            f1_macro=f1_macro,
            roc_auc=roc_auc,
            clinical_cost=clinical_cost,
            overfitting_gap=overfitting_gap,
            threshold_optimized=threshold_optimized,
            notes=notes,
        )
        self._records.append(record)
        self._update_best(record)
        self._save_table()

    def _update_best(self, record: ExperimentRecord) -> None:
        """Update best record using rank-based (Borda-style) comparison. No arbitrary weights."""
        if self._best_record is None:
            self._best_record = record
            return
        if is_better_by_rank(
            record.f1_weighted, record.roc_auc, record.f1_macro,
            record.clinical_cost, record.overfitting_gap,
            self._best_record.f1_weighted, self._best_record.roc_auc,
            self._best_record.f1_macro, self._best_record.clinical_cost,
            self._best_record.overfitting_gap,
        ):
            self._best_record = record

    def _save_table(self) -> None:
        """Save experiment table to CSV."""
        if not self._records:
            return
        rows = []
        for r in self._records:
            row = asdict(r)
            row["hyperparameters"] = json.dumps(row["hyperparameters"])
            rows.append(row)
        df = pd.DataFrame(rows)
        df.to_csv(self._experiment_table_path, index=False)
        logger.info("Saved experiment table: %s", self._experiment_table_path)

    def get_best(self) -> Optional[ExperimentRecord]:
        """Return best experiment record."""
        return self._best_record

    def get_table(self) -> pd.DataFrame:
        """Return experiment table as DataFrame."""
        if not self._records:
            return pd.DataFrame()
        rows = [asdict(r) for r in self._records]
        return pd.DataFrame(rows)
