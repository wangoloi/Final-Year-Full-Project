"""Persist evaluation tables as CSV under the run output directory."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pandas as pd


def write_evaluation_csvs(
    out_dir: Path,
    leaderboard: pd.DataFrame,
    *,
    best_name: str,
    best_test_metrics: Dict[str, float],
    n_train: int,
    n_test: int,
    n_rows_dropped_iqr: int,
) -> Path:
    """
    Write model comparison and run summary CSVs to ``out_dir/evaluation/``.

    Returns the evaluation directory path.
    """
    eval_dir = Path(out_dir) / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)

    ranked = leaderboard.copy()
    ranked.insert(0, "rank", range(1, len(ranked) + 1))
    ranked.to_csv(eval_dir / "model_metrics.csv", index=False, encoding="utf-8")

    summary_row: Dict[str, Any] = {
        "best_model": best_name,
        "selection_metric": "rmse",
        "n_train": n_train,
        "n_test": n_test,
        "n_rows_dropped_iqr": n_rows_dropped_iqr,
    }
    for k, v in best_test_metrics.items():
        summary_row[f"best_test_{k}"] = v
    pd.DataFrame([summary_row]).to_csv(
        eval_dir / "evaluation_summary.csv", index=False, encoding="utf-8"
    )

    return eval_dir
