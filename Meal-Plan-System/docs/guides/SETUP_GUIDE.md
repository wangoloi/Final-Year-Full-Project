# Glocusense Meal Plan — setup guide

**Stack:** React (Vite) + FastAPI (Python). No Flask, no Node API for the main product.

## Prerequisites

- Python **3.10+** (3.11+ recommended)
- Node.js **18+** and npm

## 1. Backend (FastAPI)

From the **repository root** (folder that contains `backend/` and `frontend/`):

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
python backend/run.py
```

- API: http://127.0.0.1:8000  
- Docs: http://127.0.0.1:8000/docs  
- Shortcut: `python run.py` at repo root delegates to `backend/run.py`.

## 2. Frontend (Vite)

```bash
cd frontend
npm install
npm run dev
```

- App: http://localhost:5173 (proxies `/api` → http://127.0.0.1:8000)

## 3. Optional: seed foods manually

```bash
python backend/scripts/seed_foods.py
```

## Environment variables

| Variable       | Default / behavior                          |
|----------------|---------------------------------------------|
| `PORT`         | `8000`                                      |
| `DATABASE_URL` | Auto: SQLite (see `backend/api/core/config.py`) |
| `JWT_SECRET`   | Dev default — **change in production**      |

## Repository layout (short)

```
Meal-Plan-System/
├── backend/
│   ├── api/              # FastAPI application package
│   ├── run.py
│   ├── requirements.txt
│   ├── tests/
│   ├── database/         # SQL reference
│   └── datasets/         # Food CSV for seeding
├── frontend/             # React (Vite) web app
├── scripts/
└── docs/
```

More detail: [../STRUCTURE.md](../STRUCTURE.md), [HOW_TO_RUN.md](./HOW_TO_RUN.md).
