"""
Glocusense - Run FastAPI backend.

  From repo root:  python backend/run.py
  From this folder:  cd backend && python run.py

React UI:  cd frontend && npm run dev
"""
import os
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import uvicorn  # noqa: E402

if __name__ == "__main__":
    os.chdir(_BACKEND_DIR)
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=True)
