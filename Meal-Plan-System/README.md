# Glocusense — Meal Plan & nutrition assistant

Diabetes-focused meal planning: **React (Vite) web app** + **FastAPI** backend + **SQLite** (no separate mobile app).

## Quick start

```bash
pip install -r requirements.txt   # installs backend/requirements.txt
python backend/run.py             # API on :8001 by default (matches Vite proxy)
# other terminal:
cd frontend && npm install && npm run dev
```

If you run the API on **8000** instead, point Vite at it:  
`set MEAL_PLAN_API_PROXY=http://127.0.0.1:8000` (PowerShell: `$env:MEAL_PLAN_API_PROXY='http://127.0.0.1:8000'`).

- **Web app:** http://localhost:5175 (strict port in `vite.config.js`; integrated GlucoSense uses this for the iframe)  
- **API docs:** http://127.0.0.1:8001/docs  
- **Windows + path with `;`:** [docs/guides/HOW_TO_RUN.md](./docs/guides/HOW_TO_RUN.md)

**One-click (Windows):** `.\scripts\start_full_system.ps1`

## Where things live

| Folder | Role |
|--------|------|
| **`backend/`** | **FastAPI** — `api/`, `run.py`, `requirements.txt`, `tests/`, `scripts/` (Python seeds), `docker-compose.yml`, `.env.example`, `database/`, `datasets/` |
| **`frontend/`** | **React (Vite)** — `src/`, `docs/UI_DESIGN_GUIDE.md` |
| **`scripts/`** | **`start_full_system.ps1`**, **`ci.ps1`** / **`ci.sh`** (local CI); **not** Python API code |
| **`pyproject.toml`** | `pytest` config for `backend/tests` |
| **`ml-services/`** | Optional Python services (not part of the live API package) |
| **`models/`** | Offline ML — **`scripts/`** (pipelines), **`notebooks/`**, **`output/`** |
| **`docker/`** | **`Dockerfile.api`**, **`Dockerfile.web`**, **`nginx-meal.conf`** — build from repo root: `docker build -f docker/Dockerfile.api .` |

## Documentation

**Full stack (with GlucoSense):** [../../SYSTEM_PIPELINE.md](../../SYSTEM_PIPELINE.md) · [../../ARCHITECTURE.md](../../ARCHITECTURE.md) (workspace root).

| Doc | Description |
|-----|-------------|
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | System design |
| [docs/STRUCTURE.md](./docs/STRUCTURE.md) | Full folder map |
| [docs/guides/HOW_TO_RUN.md](./docs/guides/HOW_TO_RUN.md) | Run & troubleshoot |
| [docs/PIPELINE.md](./docs/PIPELINE.md) | Dev workflow, local CI, GitHub Actions, Docker |
| [docs/README.md](./docs/README.md) | All docs index |

---

*Additional reference material: `docs/reference/`, `docs/project/`.*
