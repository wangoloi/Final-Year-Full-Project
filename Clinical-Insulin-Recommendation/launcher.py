"""Shim — start backend & frontend. Implementation: scripts/launcher.py"""
import subprocess
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parent / "scripts" / "launcher.py"


if __name__ == "__main__":
    if not _SCRIPT.exists():
        print(f"Missing {_SCRIPT}")
        raise SystemExit(1)
    raise SystemExit(subprocess.call([sys.executable, str(_SCRIPT), *sys.argv[1:]]))
