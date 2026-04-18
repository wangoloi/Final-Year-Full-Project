# Glocusense — Meal Plan & nutrition assistant

Diabetes-focused meal planning: **React (Vite) web app** + **FastAPI** backend + **SQLite** (no separate mobile app).

## Quick start

```bash
pip install -r requirements.txt   # installs backend/requirements.txt
python backend/run.py             # API on :8000 (or: python run.py)
# other terminal (API on 8000 — Vite default proxy is 8001 for GlucoSense integration):
cd frontend && npm install && set MEAL_PLAN_API_PROXY=http://127.0.0.1:8000 && npm run dev
```

On **Windows PowerShell** use `$env:MEAL_PLAN_API_PROXY='http://127.0.0.1:8000'` before `npm run dev` when the meal API runs on port **8000**.

- **Web app:** http://localhost:5174 (strict port in `vite.config.js`)  
- **API docs:** http://127.0.0.1:8000/docs  
- **Windows + path with `;`:** [docs/guides/HOW_TO_RUN.md](./docs/guides/HOW_TO_RUN.md)

**One-click (Windows):** `.\scripts\start_full_system.ps1`

## Where things live

| Folder | Role |
|--------|------|
| **`backend/`** | **FastAPI** — `api/`, `run.py`, `requirements.txt`, `tests/`, `scripts/` (Python seeds), `docker-compose.yml`, `.env.example`, `database/`, `datasets/` |
| **`frontend/`** | **React (Vite)** — `src/`, `docs/UI_DESIGN_GUIDE.md` |
| **`scripts/`** | Windows / workflow helpers (PowerShell); **not** Python API code |
| **`pyproject.toml`** | `pytest` config for `backend/tests` |
| **`ml-services/`**, **`models/`** | Optional ML / offline code (not part of the live API package) |

## Documentation

**Full stack (with GlucoSense):** [../../SYSTEM_PIPELINE.md](../../SYSTEM_PIPELINE.md) · [../../ARCHITECTURE.md](../../ARCHITECTURE.md) (workspace root).

| Doc | Description |
|-----|-------------|
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | System design |
| [docs/STRUCTURE.md](./docs/STRUCTURE.md) | Full folder map |
| [docs/guides/HOW_TO_RUN.md](./docs/guides/HOW_TO_RUN.md) | Run & troubleshoot |
| [docs/README.md](./docs/README.md) | All docs index |

---

*Course / legacy narratives: `docs/reference/`, `docs/project/`, `docs/history/`.*
