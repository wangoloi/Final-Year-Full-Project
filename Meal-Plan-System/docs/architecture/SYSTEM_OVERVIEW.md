# Smart Diabetes Nutrition and Monitoring Platform
## System Overview

> **Note:** This file describes an **older / aspirational** architecture (Express, `/api/v1`, Elasticsearch). The **shipping** Meal Plan app is **FastAPI** in `backend/` with **`/api/auth`**, **`/api/search`**, etc. See [../ARCHITECTURE.md](../ARCHITECTURE.md).


### Architecture

```
+------------------+     +------------------+     +------------------+
|   Web / Mobile   |     |   Express.js     |     |   Python ML      |
|   Frontend       |---->|   REST API       |<--->|   Services       |
+------------------+     +------------------+     +------------------+
                                |                         |
                                v                         v
                        +------------------+     +------------------+
                        |   PostgreSQL     |     |   FAISS / Redis   |
                        |   Redis          |     |   Elasticsearch   |
                        |   Elasticsearch  |     +------------------+
                        +------------------+
```

### Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| REST API | Express.js | Auth, CRUD, orchestration |
| Relational DB | PostgreSQL 15 | Users, meals, glucose, goals |
| Cache | Redis | Sessions, rate limits, hot data |
| Search | Elasticsearch 8.x | Hybrid keyword + semantic search |
| Vector DB | FAISS | Food embeddings, RAG retrieval |
| ML Services | Python | Embeddings, recommendations, analytics |

### API Structure (`/api/v1`)

| Resource | Endpoints |
|----------|-----------|
| /auth | POST /register, POST /login |
| /foods | GET /, GET /:id |
| /meals | GET /, GET /:id, POST / |
| /glucose | GET /, POST / |
| /goals | GET /, POST / |
| /messages | GET /conversation/:userId, POST / |

### Datasets Used

- `diabetic_diet_meal_plans_with_macros_GI.csv` - Food/meal seed data
- `diet_recommendations_dataset.csv` - Patient profiles and diet recommendations

### Next Steps

1. Run `docker compose -f backend/docker-compose.yml up -d` and apply schema
2. Seed foods: `python database/seeds/seed_foods_from_csv.py`
3. Start API: `cd backend && npm install && npm run dev`
4. Build FAISS index from foods (run embedding pipeline)
5. Configure Elasticsearch index for foods
6. Integrate chatbot with LLM (OpenAI or local)
