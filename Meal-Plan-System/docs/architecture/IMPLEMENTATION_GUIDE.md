# Implementation Guide

## Phase 1: Database (DONE)

- ER diagram: `docs/architecture/ER_DIAGRAM.md`
- Schema: `database/schema/001_initial_schema.sql`
- Seeds: `database/seeds/seed_foods_from_csv.py`
- Rollback: `database/migrations/rollback_001.sql`

## Phase 2: Development Environment (DONE)

- `backend/docker-compose.yml` - PostgreSQL, Redis, Elasticsearch
- `backend/.env.example` - Copy to `backend/.env` or repo-root `.env`

## Phase 3: Express API (DONE)

- `backend/` - Modular structure
- Run: `cd backend && npm install && npm run dev`

## Phase 4: ML Services (DONE - Core)

- `ml-services/src/embedding/pipeline.py` - FAISS index builder
- `ml-services/src/recommendation/hybrid_engine.py` - Hybrid recommender
- `ml-services/src/chatbot/rag_pipeline.py` - RAG + safety filter
- `ml-services/src/analytics/glucose_analytics.py` - Time series
- `ml-services/src/goals/goal_tracker.py` - Goal progress

## Phase 5: Chatbot RAG

- Integrate LangChain + OpenAI
- Store conversations in PostgreSQL
- Use FAISS for knowledge retrieval

## Phase 6: Elasticsearch

- Index: `search/elasticsearch/food_index.json`
- Hybrid search: keyword + semantic re-ranking

## Phase 7: Glucose Prediction

- Train LSTM on user glucose history
- Alert triggering system

## Phase 8: Goal Tracking

- Integrate `goal_tracker.py` with API
- Progress visualization endpoints
