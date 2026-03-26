#!/usr/bin/env python3
"""
Rebuild evaluation_summary.csv from existing metrics.json files.
Use when you have model evaluation artifacts but the summary is incomplete or stale.

Usage: python scripts/rebuild_evaluation_summary.py [--out-dir outputs/evaluation]
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd


def main():
    parser = argparse.ArgumentParser(description="Rebuild evaluation summary from metrics.json")
    parser.add_argument("--out-dir", type=Path, default=Path("outputs/evaluation"))
    args = parser.parse_args()

    out_dir = args.out_dir.resolve()
    if not out_dir.exists():
        print(f"Error: {out_dir} does not exist")
        return 1

    rows = []
    for subdir in sorted(out_dir.iterdir()):
        if not subdir.is_dir():
            continue
        metrics_path = subdir / "metrics.json"
        if not metrics_path.exists():
            continue
        try:
            with open(metrics_path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: Could not read {metrics_path}: {e}")
            continue

        test = data.get("test")
        if not test:
            continue

        model_name = test.get("model_name", subdir.name)
        rows.append({
            "model": model_name,
            "accuracy": test.get("accuracy", 0),
            "f1_weighted": test.get("f1_weighted", 0),
            "f1_macro": test.get("f1_macro", 0),
            "roc_auc_weighted": test.get("roc_auc_ovr_weighted", 0),
            "artifacts_dir": str(out_dir / subdir.name),
        })

    if not rows:
        print("No metrics.json files found")
        return 1

    df = pd.DataFrame(rows).sort_values("f1_weighted", ascending=False)
    summary_path = out_dir / "evaluation_summary.csv"
    df.to_csv(summary_path, index=False)
    print(f"Wrote {len(rows)} models to {summary_path}")
    print(df.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    sys.exit(main())
