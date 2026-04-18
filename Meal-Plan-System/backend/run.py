"""
Glocusense - Run FastAPI backend.

  From repo root:  python backend/run.py
  From this folder:  cd backend && python run.py

React UI:  cd frontend && npm run dev
"""
import os
import sys
from pathlib import Path

# Must run before uvicorn imports the app (Chroma / Hugging Face stack).
os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")
os.environ.setdefault("CHROMA_TELEMETRY", "false")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("TRANSFORMERS_NO_FLAX", "1")

_BACKEND_DIR = Path(__file__).resolve().parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import uvicorn  # noqa: E402

if __name__ == "__main__":
    os.chdir(_BACKEND_DIR)
    # Integrated dev uses :8001 (GlucoSense uses :8000). Override with PORT when needed.
    port = int(os.getenv("PORT", 8001))
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=True)
