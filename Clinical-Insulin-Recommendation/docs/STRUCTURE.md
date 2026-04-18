# GlucoSense repository layout

**Stack:** **FastAPI** (Python) + **React** (Vite) web app.

| Path | Role |
|------|------|
| **`backend/app.py`** | FastAPI application (`uvicorn backend.app:app` or root shim `app:app`) |
| **`backend/src/`** | `insulin_system` (API, models, storage) and `clinical_ml_pipeline` |
| **`frontend/`** | React SPA — `npm run dev` → http://localhost:5173 (proxies `/api` to :8000) |
| **`app.py`** (root) | Thin shim so `uvicorn app:app` from repo root still works |
| **`data/`** | Training CSV and fixtures |
| **`outputs/`** | Saved models, DB (`glucosense.db`), evaluation artifacts |
| **`config/`** | Clinical JSON thresholds / guidelines |
| **`scripts/`** | Pipelines, seeds, launcher, Windows helpers |
| **`tests/`** | Pytest |
| **`docs/`** | Documentation + **`docs/notebooks/`** (Jupyter) |

**Removed / consolidated**

- Duplicate FastAPI app that lived in `backend/main.py` (old dashboard-only API) — use **`backend/app.py`** only.
- Root `requirements/` — optional Streamlit deps → **`scripts/pipeline/requirements-dashboard.txt`**.
