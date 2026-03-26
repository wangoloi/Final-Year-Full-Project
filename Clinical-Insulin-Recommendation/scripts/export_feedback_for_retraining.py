"""
Export clinician feedback for model retraining.

Reads from clinician_feedback table and outputs a CSV suitable for
augmenting training data or fine-tuning. Use with retrain_with_feedback.py.

Usage:
  python scripts/export_feedback_for_retraining.py
  python scripts/export_feedback_for_retraining.py --out outputs/feedback_export.csv --limit 500
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "src"))

from insulin_system.storage import get_clinician_feedback


def main(
    out_path: Path = Path("outputs/feedback_export.csv"),
    limit: int = 500,
    db_path: Path | None = None,
) -> int:
    records = get_clinician_feedback(limit=limit, db_path=db_path)
    if not records:
        print("No clinician feedback records found.")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "id", "created_at", "record_id", "request_id",
        "predicted_class", "clinician_action", "actual_dose_units",
        "override_reason", "input_summary",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in records:
            row = r.copy()
            if isinstance(row.get("input_summary"), str):
                try:
                    row["input_summary"] = json.loads(row["input_summary"])
                except (json.JSONDecodeError, TypeError):
                    pass
            w.writerow(row)
    print(f"Exported {len(records)} feedback records to {out_path}")
    return 0


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=Path("outputs/feedback_export.csv"))
    p.add_argument("--limit", type=int, default=500)
    args = p.parse_args()
    sys.exit(main(out_path=args.out, limit=args.limit))
