# Development Environment Setup

## Prerequisites

- Docker & Docker Compose
- Node.js 18+
- Python 3.10+
- (Optional) PostgreSQL 15, Redis 7, Elasticsearch 8.x for local install

## Quick Start with Docker

```bash
# Start infrastructure
docker compose -f backend/docker-compose.yml up -d

# Wait for services (check health)
docker compose -f backend/docker-compose.yml ps

# Run migrations
psql $DATABASE_URL -f database/schema/001_initial_schema.sql

# Seed foods
python database/seeds/seed_foods_from_csv.py
```

## Service Configuration

### PostgreSQL 15

- Port: 5432
- Connection pooling: Use `pg-pool` in Node.js (default pool size: 10)
- Performance: `shared_buffers`, `work_mem` tuned for dev

### Redis

- Port: 6379
- Auth: `requirepass` in redis.conf
- Persistence: RDB + AOF enabled
- For HA: Sentinel can be added in production

### Elasticsearch 8.x

- Port: 9200 (REST), 9300 (transport)
- Single-node for dev; cluster for prod
- Heap: 512MB for dev

## Environment Variables

See `backend/.env.example`. Required for API:

- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET`
- `ELASTICSEARCH_URL`

## Python Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements-ml.txt
```

## Node.js

```bash
cd backend && npm install
```

## Logging

- Winston for Express
- Structured JSON logs in production
- Log level via `LOG_LEVEL`
