"""
Shim — full model evaluation and best-model export.

Prefer: python scripts/pipeline/run_evaluation.py
"""
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_SCRIPT = _ROOT / "scripts" / "pipeline" / "run_evaluation.py"


def main() -> int:
    if not _SCRIPT.exists():
        print(f"Missing {_SCRIPT}")
        return 1
    return subprocess.call([sys.executable, str(_SCRIPT), *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
