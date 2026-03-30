"""
Glocusense - Run FastAPI backend.

  From repo root:  python backend/run.py
  From this folder:  cd backend && python run.py

React UI:  cd frontend && npm run dev  (Vite proxies /api → http://127.0.0.1:8001 by default)
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
    # Default 8001 matches frontend/vite.config.js proxy and GlucoSense integration (clinical API uses 8000).
    port = int(os.getenv("PORT", 8001))
    # MEAL_UVICORN_RELOAD=0|false → single process, faster cold start (no file watcher).
    _reload = os.getenv("MEAL_UVICORN_RELOAD", "1") not in ("0", "false")
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=_reload)
