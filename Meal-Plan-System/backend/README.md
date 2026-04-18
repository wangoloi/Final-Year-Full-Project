# Backend (FastAPI)

Python API for Glocusense Meal Plan.

```bash
# From repository root (parent of backend/):
python backend/run.py

# Or:
cd backend
pip install -r requirements.txt
python run.py
```

- **Port:** 8000 (override with `PORT` env var)
- **OpenAPI:** http://127.0.0.1:8000/docs  
- **Health:** http://127.0.0.1:8000/api/health  

| Path | Purpose |
|------|---------|
| `api/` | FastAPI app, models, routers |
| `database/` | Reference SQL schema, migrations, seeds |
| `datasets/` | Uganda food CSV (startup seed) |
| `tests/` | `pytest` from repo root (see root **`pyproject.toml`**) |
| `scripts/` | `seed_foods.py`, `seed_test_user.py` — run: `python backend/scripts/seed_foods.py` |
| `.env.example` | Copy to **`backend/.env`** or repo-root **`.env`** |
| `docker-compose.yml` | Optional DB stack: `docker compose -f backend/docker-compose.yml up -d` |
| `docker-compose.typesense.yml` | Typesense for food search: `docker compose -f backend/docker-compose.typesense.yml up -d` — then set `TYPESENSE_HOST=localhost` in `.env` (see **`TYPESENSE.md`**) |
| `CHATBOT.md` | RAG (Chroma) + LLM (OpenAI or Ollama) for **`/api/chatbot/message`** |
