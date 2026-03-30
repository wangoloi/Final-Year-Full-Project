# GlucoSense repository layout (Clinical-Insulin-Recommendation)

**Stack:** **FastAPI** (Python) + **React** (Vite) web app.

| Path | Role |
|------|------|
| **`backend/app.py`** | FastAPI application (`uvicorn backend.app:app` or root shim `app:app`) |
| **`backend/src/insulin_system/`** | API routes, storage, SQLite, patients, recommendations |
| **`backend/src/clinical_insulin_pipeline/`** | Insulin dose regression (0–10 IU): train, evaluate, `joblib` bundle |
| **`frontend/`** | React SPA — `npm run dev` → http://localhost:5173 (proxies `/api` to :8000) |
| **`app.py`** (root) | Thin shim so `uvicorn app:app` from repo root still works |
| **`data/`** | Training CSV (`SmartSensor_DiabetesMonitoring.csv`) and `data/README.md` |
| **`outputs/`** | Generated models, plots, bundles — see `outputs/README.md` |
| **`config/`** | Clinical JSON thresholds / guidelines |
| **`scripts/`** | Launchers, ML pipeline, Windows helpers — see `scripts/README.md` |
| **`tests/`** | Pytest |
| **`docs/`** | Documentation |

**Root entrypoints**

| File | Role |
|------|------|
| `run_clinical_insulin_pipeline.py` | Delegates to `scripts/pipeline/run_clinical_insulin_pipeline.py` |
| `launcher.py` | Delegates to `scripts/launcher.py` |

**Removed / consolidated**

- Duplicate FastAPI app that lived in `backend/main.py` — use **`backend/app.py`** only.
- Legacy ML pipelines (`smart_sensor_ml`, `clinical_ml_pipeline`, etc.) were removed in favor of **`clinical_insulin_pipeline`** and optional `outputs/best_model` for the API stub.
