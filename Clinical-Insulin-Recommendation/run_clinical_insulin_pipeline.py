"""
Compatibility entrypoint (repo root). Implementation: scripts/pipeline/run_clinical_insulin_pipeline.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parent / "scripts" / "pipeline" / "run_clinical_insulin_pipeline.py"


if __name__ == "__main__":
    if not _SCRIPT.is_file():
        print(f"Missing {_SCRIPT}", file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(subprocess.call([sys.executable, str(_SCRIPT), *sys.argv[1:]]))
