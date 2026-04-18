# Smart Diabetes Nutrition & Monitoring Platform

> **Superseded:** Describes Express/Postgres layout and `database/` at repo root. The **current** Meal Plan app uses **`backend/`** (FastAPI) and **`backend/database/`** for SQL reference. See [../ARCHITECTURE.md](../ARCHITECTURE.md).

Production-ready architecture implementing the master system design prompt.

## Quick Start

```bash
# 1. Start infrastructure
docker compose -f backend/docker-compose.yml up -d

# 2. Apply database schema (after Postgres is ready)
$env:DATABASE_URL="postgresql://glocusense:glocusense_dev@localhost:5432/glocusense"
psql $env:DATABASE_URL -f database/schema/001_initial_schema.sql

# 3. Seed foods from datasets
python database/seeds/seed_foods_from_csv.py

# 4. Start Express API
cd backend && npm install && npm run dev

# 5. (Optional) ML services
cd ml-services && pip install -r requirements.txt
```

## Project Structure

```
Meal-Plan-System/
├── backend/                 # Express.js REST API
│   ├── src/
│   │   ├── config/          # Logger, database, Redis
│   │   ├── middleware/      # Auth, error handling, rate limit
│   │   ├── modules/         # Foods, meals, glucose, goals, messages
│   │   │   └── {module}/    # controller, service, repository
│   │   └── routes/
├── database/
│   ├── schema/              # PostgreSQL DDL
│   ├── seeds/               # Seed scripts + Python loader
│   └── migrations/          # Rollback scripts
├── ml-services/             # Python ML
│   ├── src/
│   │   ├── embedding/       # FAISS pipeline (all-MiniLM-L6-v2)
│   │   ├── recommendation/  # Hybrid engine
│   │   ├── chatbot/         # RAG pipeline, safety filter
│   │   ├── analytics/       # Glucose analytics
│   │   └── goals/           # Goal tracker
│   └── requirements.txt
├── search/                  # Elasticsearch index config
├── docs/architecture/      # ER diagram, vector schema, setup
├── datasets/                # diabetic_diet_meal_plans, diet_recommendations
└── backend/docker-compose.yml  # PostgreSQL, Redis, Elasticsearch
```

## API Endpoints (`/api/v1`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /auth/register | No | Register |
| POST | /auth/login | No | Login |
| GET | /foods | No | List foods (paginated, filter by category, max_gi) |
| GET | /foods/:id | No | Get food by ID |
| GET | /meals | Yes | List user meals |
| GET | /meals/:id | Yes | Get meal |
| POST | /meals | Yes | Create meal |
| GET | /glucose | Yes | List glucose readings |
| POST | /glucose | Yes | Create reading |
| GET | /goals | Yes | List goals |
| POST | /goals | Yes | Create goal |
| GET | /messages/conversation/:userId | Yes | Get conversation |
| POST | /messages | Yes | Send message |

## Design Principles

- **SOLID**: Single responsibility, dependency injection where appropriate
- **Clean architecture**: Controller → Service → Repository
- **Modular**: Each resource is self-contained
- **Production-ready**: JWT auth, rate limiting, centralized logging, error handling

## Datasets

- `diabetic_diet_meal_plans_with_macros_GI.csv` - Meal plans with macros and GI
- `diet_recommendations_dataset.csv` - Patient profiles and diet recommendations

Used for seeding foods and training recommendation models.
