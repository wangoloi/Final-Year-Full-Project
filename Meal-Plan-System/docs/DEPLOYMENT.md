# Glocusense Meal Plan — deployment notes

Stack: **FastAPI** (`backend/`) + **React/Vite** (`frontend/`).

## Backend (production-style)

```bash
cd /path/to/Meal-Plan-System
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix:    source .venv/bin/activate

pip install -r backend/requirements.txt

export JWT_SECRET="use-a-long-random-secret"   # required in production
export PORT=8000
# Optional: PostgreSQL
# export DATABASE_URL="postgresql+psycopg2://user:pass@host:5432/dbname"

python backend/run.py
# Or: uvicorn api.main:app --host 0.0.0.0 --port 8000
#     (run from inside `backend/` with PYTHONPATH=. )
```

- Health: `GET http://<host>:8000/api/health` → `"app":"glocusense-meal-plan"`
- OpenAPI: `http://<host>:8000/docs`

**CORS:** set allowed origins in `backend/api/main.py` for your production web origin.

## Frontend

```bash
cd frontend
npm ci
npm run build
```

Serve `frontend/dist/` with any static host. Configure the production API URL (e.g. reverse proxy `/api` → FastAPI, or set `VITE_*` build-time vars if you add them to the client).

## Docker (example)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
WORKDIR /app/backend
ENV JWT_SECRET=change-me
EXPOSE 8000
CMD ["python", "run.py"]
```

Adjust `WORKDIR` / `CMD` if you prefer `uvicorn` directly.

## Checklist

- [ ] Strong `JWT_SECRET` (and rotate from dev default)
- [ ] `DATABASE_URL` for PostgreSQL if not using SQLite
- [ ] HTTPS termination (reverse proxy)
- [ ] CORS origins locked to real domains
- [ ] Do not commit `.env` with secrets
