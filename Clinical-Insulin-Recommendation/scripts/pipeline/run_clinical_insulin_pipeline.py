"""
Train the clinical insulin regression pipeline (0-10 IU).

Usage (from Clinical-Insulin-Recommendation root):
  python scripts/pipeline/run_clinical_insulin_pipeline.py
  python scripts/pipeline/run_clinical_insulin_pipeline.py --skip-learning-curve --skip-shap

Or use the repo root shim: python run_clinical_insulin_pipeline.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
_SRC = _ROOT / "backend" / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from clinical_insulin_pipeline.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
