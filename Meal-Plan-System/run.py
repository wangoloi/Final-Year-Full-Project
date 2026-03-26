"""
Shim: starts the FastAPI app from `backend/`.
Prefer explicitly:  python backend/run.py
"""
import subprocess
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent / "backend"
if not (_backend / "run.py").is_file():
    sys.stderr.write("Missing backend/run.py — is the backend folder present?\n")
    raise SystemExit(1)

raise SystemExit(
    subprocess.call([sys.executable, str(_backend / "run.py"), *sys.argv[1:]], cwd=str(_backend))
)
