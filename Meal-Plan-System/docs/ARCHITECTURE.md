# Glocusense Meal Plan — Architecture

**Stack:** React (Vite) SPA + FastAPI + SQLAlchemy + SQLite (default).

**GlucoSense integration (separate API ports, iframe, SSO):** [../../../SYSTEM_PIPELINE.md](../../../SYSTEM_PIPELINE.md).

## High-level diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  FRONTEND — React SPA (Vite dev server :5175)                      │
│  `frontend/src` — calls `/api/*` (proxied to backend)             │
└────────────────────────────┬──────────────────────────────────────┘
                             │ HTTP  /api → 127.0.0.1:8001 (default)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  BACKEND — FastAPI in `backend/` (`api.main:app`, uvicorn :8001)  │
│  Routers: auth, search, chatbot, recommendations, glucose           │
│  Pattern: router → service → repository (per domain)               │
└────────────────────────────┬──────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  DATA — SQLite (Windows: %LocalAppData%\Glocusense\glocusense.db)│
│  ORM: `backend/api/models.py` — tables via `init_db()`            │
│  Seed: `backend/datasets/*.csv` + `backend/api/utils/seed.py`     │
└─────────────────────────────────────────────────────────────────┘
```

## Request flow (example: register)

1. Browser `POST /api/auth/register` → Vite proxy → `backend/api/modules/auth/router.py`
2. Service validates, hashes password (`bcrypt`), persists user, returns JWT + user JSON
3. Frontend stores token in `localStorage`, `AuthContext` holds user state

## Optional components

| Area | Path | Role |
|------|------|------|
| ML experiments | `ml-services/`, `models/` | Offline pipelines |
| SQL reference | `backend/database/` | Schema / migrations as documentation |
| Docker | `backend/docker-compose.yml` | Optional Postgres, Redis, Elasticsearch |

## Configuration

- `backend/api/core/config.py` — `DATABASE_URL`, `JWT_SECRET`, `PORT`, dotenv  
- `frontend/vite.config.js` — dev proxy `/api` → backend  

See also: [STRUCTURE.md](./STRUCTURE.md), [guides/HOW_TO_RUN.md](./guides/HOW_TO_RUN.md).
