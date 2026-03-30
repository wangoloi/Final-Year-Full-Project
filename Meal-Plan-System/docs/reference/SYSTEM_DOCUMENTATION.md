# Glocusense — Full System Documentation

**Diabetes-Focused Meal Planning Application**

This document describes the logic, tools, technology, architecture, design, and full functionality of the Glocusense system.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Technology Stack](#2-technology-stack)
3. [System Architecture](#3-system-architecture)
4. [Logic & Algorithms](#4-logic--algorithms)
5. [Database Design](#5-database-design)
6. [API Design](#6-api-design)
7. [Frontend Design](#7-frontend-design)
8. [Data Flow & Functionality](#8-data-flow--functionality)
9. [Configuration & Deployment](#9-configuration--deployment)
10. [Design Rationale & Justifications](#10-design-rationale--justifications)

---

## 1. System Overview

### 1.1 Purpose

Glocusense is a web application that helps people with diabetes:
- Find diabetes-friendly and low-glycemic index foods
- Get nutrition advice through an AI chatbot
- Track blood glucose readings
- Receive personalized food recommendations

### 1.2 Target Users

- **Primary:** People with Type 1, Type 2, Gestational, or Prediabetes
- **Geographic focus:** Uganda (local foods: matooke, posho, cassava) with broader applicability

### 1.3 Core Features

| Feature | Description |
|---------|-------------|
| **Authentication** | Register, login, JWT-protected sessions |
| **Food Search** | Keyword + fuzzy search with diabetes filtering |
| **Nutrition Assistant** | RAG-based chatbot for nutrition questions |
| **Glucose Tracking** | Record fasting, pre/post-meal, random readings |
| **Recommendations** | Personalized low-GI food suggestions |

---

## 2. Technology Stack

### 2.1 Backend

| Component | Technology | Version |
|-----------|------------|---------|
| Framework | FastAPI | ≥0.104.0 |
| Server | Uvicorn | ≥0.24.0 |
| ORM | SQLAlchemy | ≥2.0.0 |
| Auth | bcrypt, PyJWT | ≥4.0.0, ≥2.8.0 |
| Validation | Pydantic | ≥2.0.0 |
| ML/Embeddings | sentence-transformers | ≥2.2.0 |
| Vector DB | ChromaDB | ≥0.4.0 |
| Fuzzy Search | rapidfuzz | ≥3.0.0 |
| Fallback ML | scikit-learn | ≥1.3.0 |

### 2.2 Frontend

| Component | Technology | Version |
|-----------|------------|---------|
| Framework | React | 18.2.0 |
| Build Tool | Vite | 5.0.0 |
| Routing | React Router DOM | 6.20.0 |
| Icons | Font Awesome | 6.4.0 |
| Fonts | DM Sans, Outfit (Google Fonts) | — |

### 2.3 Database

| Component | Technology |
|-----------|------------|
| Primary | SQLite (default) |
| Alternative | PostgreSQL (via `DATABASE_URL`) |
| Vector Store | ChromaDB (persistent) or in-memory fallback |

### 2.4 Tools & Libraries

- **Embeddings:** `all-MiniLM-L6-v2` (384 dimensions) or TF-IDF fallback
- **Vector similarity:** ChromaDB cosine distance or NumPy dot product
- **Password hashing:** bcrypt
- **JWT:** HS256, 7-day expiry

---

## 3. System Architecture

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     FRONTEND (React + Vite)                             │
│  Landing | Login | Register | Dashboard | Search | Chatbot | Glucose |   │
│  Recommendations                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP/REST (Bearer JWT)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND (api/main.py)                        │
│  CORS | Auth Routers | Search | Chatbot | Recommendations | Glucose     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   SQLAlchemy     │    │   ChromaDB /      │    │  EmbeddingService │
│   SQLite/Postgres│    │   In-Memory       │    │  (sentence-       │
│   (Users, Foods, │    │   Vector Store    │    │   transformers)  │
│   Glucose, Chat) │    │   (RAG)           │    │                  │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

### 3.2 Backend Module Structure

```
api/
├── main.py                 # FastAPI app, CORS, startup seed
├── models.py               # User, FoodItem, GlucoseReading, ChatMessage
├── database.py             # Re-exports from shared
├── core/
│   ├── config.py           # DATABASE_URL, JWT_SECRET, PORT
│   ├── exceptions.py      # AppError, ValidationError, AuthError
│   └── logging_config.py  # Structured logging
├── shared/
│   ├── database.py         # Engine, SessionLocal, get_db, init_db
│   └── dependencies.py     # get_current_user (JWT)
├── modules/
│   ├── auth/               # Register, login, /me
│   ├── search/             # Food search (keyword + fuzzy)
│   ├── chatbot/            # RAG-based nutrition assistant
│   ├── recommendations/    # Personalized food suggestions
│   └── glucose/            # Glucose CRUD
├── rag/
│   ├── embedding_service.py  # SentenceTransformer / TF-IDF
│   └── vector_store.py       # ChromaDB / in-memory
└── utils/
    └── seed.py             # CSV load, RAG build
```

### 3.3 Request Flow

1. **Client** sends HTTP request with optional `Authorization: Bearer <token>`
2. **FastAPI** routes to appropriate module (auth, search, chatbot, etc.)
3. **Dependencies** inject `db` (Session) and `user` (for protected routes)
4. **Service** executes business logic, calls repository if needed
5. **Response** returned as JSON

---

## 4. Logic & Algorithms

### 4.1 Authentication Logic

**Registration:**
1. Validate username and email uniqueness
2. Hash password with bcrypt
3. Create user record with optional diabetes fields
4. Generate JWT (userId, 7-day expiry)
5. Return `{ user, token }`

**Login:**
1. Find user by username or email
2. Verify password with bcrypt
3. Generate JWT
4. Return `{ user, token }`

**Protected Routes:**
- Extract `Authorization: Bearer <token>` header
- Decode JWT, validate signature and expiry
- Load user by `userId` from payload
- Return 401 if invalid

### 4.2 Search Logic

**Strategy:** Keyword-first, fuzzy fallback

1. **Keyword Search** (`keyword_search`):
   - SQL `ILIKE` on `name`, `local_name`, `description`, `category`
   - If user has diabetes: filter `diabetes_friendly = True`
   - Return up to `limit * 2` results, trimmed to `limit`

2. **Fuzzy Search** (`fuzzy_search`) — if keyword returns nothing:
   - Load all foods (optionally diabetes-only)
   - For each food, compute `max(fuzz.ratio, fuzz.partial_ratio)` / 100
   - Keep items with score ≥ 0.5
   - Sort by score descending, return top `limit`

### 4.3 Chatbot Logic (RAG)

**Intent Detection (order matters):**

| Priority | Intent | Keywords | Handler |
|----------|--------|----------|---------|
| 1 | Greeting | hello, hi, hey | `build_greeting_reply()` |
| 2 | Glycemic index | gi, glycemic | `build_gi_reply()` |
| 3 | Carbohydrates | carb, carbohydrate | `build_carb_reply()` |
| 4 | Blood sugar stability | stable, control, good for diabetes | `build_stability_reply(foods)` |
| 5 | Food-specific | RAG retrieval returns foods | `build_food_reply(foods[0])` |
| 6 | Fallback | — | `build_fallback_reply()` |

**RAG Retrieval:**
1. Embed user message with `EmbeddingService.embed_query()`
2. Query `VectorStore` for top 5 similar documents
3. Extract `food_id` from metadata, load from DB
4. Pass to intent handlers (stability or food-specific)

**Response Building:**
- Each handler returns a string; disclaimer appended to all
- Disclaimer: *"This is general information only. Consult your healthcare provider for medical advice."*

### 4.4 Recommendations Logic

**Scoring Algorithm (`score_food`):**

| Factor | Condition | Score |
|--------|-----------|-------|
| Glycemic index | ≤ 40 | +30 |
| Glycemic index | ≤ 55 | +20 |
| Glycemic index | > 55 | +5 |
| Fiber | ≥ 5 g | +15 |
| Fiber | ≥ 2.5 g | +8 |
| Diabetes-friendly | True | +10 |

**Flow:**
1. Set `max_gi = 50` (diabetic) or `55` (non-diabetic)
2. Fetch candidates: `glycemic_index <= max_gi`, optional `diabetes_friendly`
3. Order by `glycemic_index ASC`, `fiber DESC`
4. Score each food, sort by score descending
5. **Diversify by category:** Round-robin across categories to avoid clustering

### 4.5 Glucose Tracking Logic

**Reading Types:** `fasting`, `pre_meal`, `post_meal`, `random`

**Add Reading:**
1. Validate `reading_value` (numeric)
2. Normalize `reading_type` (default `random`)
3. Insert `GlucoseReading` with `user_id`, `reading_time = now()`
4. Return list of readings (newest first)

---

## 5. Database Design

### 5.1 Entity-Relationship Overview

```
User (1) ──────< GlucoseReading (N)
User (1) ──────< ChatMessage (N)
FoodItem (standalone, seeded from CSV)
```

### 5.2 User

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| username | String(80) | Unique, NotNull |
| email | String(120) | Unique, NotNull |
| password_hash | String(128) | Nullable |
| created_at | DateTime | Default now |
| first_name, last_name | String(50) | Nullable |
| age, gender, height, weight | Various | Nullable |
| activity_level | String(20) | Nullable |
| has_diabetes | Boolean | Default False |
| diabetes_type | String(20) | Nullable |
| diagnosis_date | Date | Nullable |
| current_medications | Text | Nullable |
| target_blood_glucose_min/max | Float | Nullable |
| profile_completed | Boolean | Default False |
| onboarding_completed | Boolean | Default False |

### 5.3 FoodItem

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| name | String(100) | NotNull |
| local_name | String(100) | Nullable |
| category | String(50) | NotNull |
| description | Text | Nullable |
| calories, protein, carbohydrates, fiber, fat, sugar | Float | NotNull |
| glycemic_index | Integer | Nullable |
| sodium, vitamin_c, iron, calcium | Float | Nullable |
| diabetes_friendly | Boolean | Default False |
| serving_size | String(80) | Nullable |
| created_at | DateTime | Default now |

### 5.4 GlucoseReading

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| user_id | Integer | FK → users.id |
| reading_value | Float | NotNull |
| reading_type | String(20) | NotNull |
| reading_time | DateTime | NotNull |
| notes | Text | Nullable |
| created_at | DateTime | Default now |

### 5.5 ChatMessage

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| user_id | Integer | FK → users.id |
| role | String(10) | user | assistant |
| content | Text | NotNull |
| created_at | DateTime | Default now |

---

## 6. API Design

### 6.1 Base URL

- Development: `http://localhost:8000`
- Frontend proxy: `/api` → `http://localhost:8000`

### 6.2 Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Health check |
| POST | /api/auth/register | No | Register user |
| POST | /api/auth/login | No | Login |
| GET | /api/auth/me | Yes | Current user |
| GET | /api/search?q=&limit= | Yes | Search foods |
| POST | /api/chatbot/message | Yes | Send message |
| GET | /api/recommendations?limit= | Yes | Get recommendations |
| GET | /api/glucose | Yes | List glucose readings |
| POST | /api/glucose | Yes | Add glucose reading |

### 6.3 Request/Response Examples

**Register:**
```json
POST /api/auth/register
{ "username": "jane", "email": "jane@example.com", "password": "secret", "has_diabetes": true, "diabetes_type": "Type 2" }
→ { "user": {...}, "token": "eyJ..." }
```

**Search:**
```
GET /api/search?q=matooke&limit=20
→ { "results": [...], "not_found": false }
```

**Chatbot:**
```json
POST /api/chatbot/message
{ "message": "Is matooke good for diabetes?" }
→ { "response": "Matooke (Steamed Green Banana): 122 cal, glycemic index 45, ..." }
```

---

## 7. Frontend Design

### 7.1 Page Structure

| Route | Component | Protected |
|-------|-----------|-----------|
| / | Landing | No |
| /login | Login | No |
| /register | Register | No |
| /app | Layout + Outlet | Yes |
| /app | Dashboard | Yes |
| /app/search | Search | Yes |
| /app/chatbot | Chatbot | Yes |
| /app/recommendations | Recommendations | Yes |
| /app/glucose | Glucose | Yes |

### 7.2 Component Hierarchy

```
App
├── AuthProvider
│   ├── Routes
│   │   ├── Landing
│   │   ├── Login
│   │   ├── Register
│   │   └── PrivateRoute
│   │       └── Layout
│   │           ├── Navbar (logo, nav links, logout)
│   │           └── Outlet (Dashboard, Search, Chatbot, etc.)
```

### 7.3 API Client

- **Base:** `/api`
- **Auth:** `localStorage.getItem('token')` → `Authorization: Bearer <token>`
- **Methods:** `auth.login`, `auth.register`, `auth.me`, `search()`, `chatbot()`, `recommendations()`, `glucose.list`, `glucose.add`
- **Error handling:** Parses `detail`, `error`, `message` from JSON; throws on non-OK status

### 7.4 Design System

- **Colors:** Primary blue (#2563eb), dark blue (#1d4ed8)
- **Typography:** DM Sans (body), Outfit (headings)
- **Layout:** Card-based, responsive grid
- **Icons:** Font Awesome (apple-whole, comments, heart-pulse, seedling, leaf)

---

## 8. Data Flow & Functionality

### 8.1 Startup Flow

1. `python backend/run.py` (or `python run.py` from repo root) → Uvicorn loads `api.main:app` with cwd `backend/`
2. Lifespan: `init_db()` creates tables
3. Background thread: `load_foods_from_csv(db)` loads CSV from `backend/datasets/`
4. If no foods: `seed_fallback(db)` adds minimal data
5. `build_rag_store(db)` is a no-op (RAG disabled; DB search used)
6. API ready at `http://localhost:8000`

### 8.2 User Registration Flow

1. User fills form (username, email, password, optional diabetes info)
2. Frontend POSTs to `/api/auth/register`
3. Backend validates uniqueness, hashes password, creates user
4. Returns JWT; frontend stores in `localStorage`
5. Redirect to `/app`

### 8.3 Search Flow

1. User enters query in Search page
2. Frontend GETs `/api/search?q=...&limit=20` with Bearer token
3. Backend: keyword search → fuzzy if empty
4. Returns `{ results: [...], not_found }`
5. Frontend renders food cards (name, calories, glycemic index, category)

### 8.4 Chatbot Flow

1. User types message
2. Frontend POSTs `/api/chatbot/message` with `{ message }`
3. Backend: save user message → embed query → RAG retrieval → intent detection → build reply → save assistant message
4. Returns `{ response }`
5. Frontend appends to chat UI

### 8.5 Recommendations Flow

1. User opens Recommendations page
2. Frontend GETs `/api/recommendations?limit=12` with Bearer token
3. Backend: fetch candidates → score → diversify → return list
4. Frontend renders grid of food cards

### 8.6 Glucose Flow

1. User fills form (value, type, notes) and submits
2. Frontend POSTs `/api/glucose` with body
3. Backend validates, inserts, returns updated list
4. Frontend refreshes readings display

---

## 9. Configuration & Deployment

### 9.1 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | (auto) | SQLite path or PostgreSQL URL |
| JWT_SECRET | dev-secret-... | JWT signing key (min 32 bytes) |
| PORT | 8000 | API port |
| LOG_LEVEL | INFO | Logging level |

### 9.2 Database Paths

- **Windows:** `%LOCALAPPDATA%/Glocusense/glocusense.db`
- **Linux/macOS:** `instance/glocusense.db`
- **Override:** Set `DATABASE_URL`

### 9.3 Vector Store

- **Path:** `instance/chroma_nutrition`
- **Fallback:** In-memory (NumPy cosine similarity) if ChromaDB unavailable

### 9.4 Running the System

```bash
# Backend (from repo root)
pip install -r requirements.txt
python backend/run.py

# Frontend
cd frontend && npm install && npm run dev
```

- API: http://localhost:8000
- Frontend: http://localhost:5173 (proxies /api to backend)

---

## 10. Design Rationale & Justifications

This section explains *why* certain technologies, patterns, and design decisions were made, and what results they achieve.

### 10.1 Technology Choices

#### FastAPI (Backend Framework)

**Why:** FastAPI was chosen over Flask for the API layer because it provides automatic OpenAPI documentation, built-in request validation via Pydantic, async support, and strong typing. For a REST API that serves a React frontend, FastAPI reduces boilerplate and catches validation errors early.

**Result:** Cleaner API code, fewer runtime validation bugs, and self-documenting endpoints.

#### SQLite (Default Database)

**Why:** SQLite requires no separate server, works out of the box, and stores data in a single file. This simplifies local development and deployment for small-to-medium user bases. The system supports PostgreSQL via `DATABASE_URL` for production scaling.

**Result:** Zero-config setup for developers and students; easy migration path when scaling is needed.

#### JWT (Authentication)

**Why:** JWTs are stateless—the server does not need to store sessions. The token carries the user ID and expiry; the frontend sends it with each request. This fits a decoupled frontend/backend architecture and works well with third-party API clients if you add them later.

**Result:** Simpler backend (no session store), easier horizontal scaling, and straightforward integration with any client that can send headers.

#### bcrypt (Password Hashing)

**Why:** bcrypt is designed for password hashing with built-in salting and configurable cost. It is resistant to brute-force and rainbow-table attacks. Industry standard for secure password storage.

**Result:** Passwords are never stored in plain text; even with database access, attackers cannot recover user passwords.

#### React + Vite (Frontend)

**Why:** React provides component-based UI, a large ecosystem, and clear separation of concerns. Vite offers fast dev server startup and HMR (hot module replacement) compared to Create React App.

**Result:** Faster development cycles, maintainable UI code, and a modern build pipeline.

---

### 10.2 Search Architecture

#### Keyword-First, Fuzzy Fallback

**Why:** Keyword search (SQL `ILIKE`) is fast, deterministic, and works well when users type exact or partial food names (e.g. "matooke", "bean"). Fuzzy search (rapidfuzz) is used only when keyword returns nothing—to handle typos like "matoke" or "matoke".

**Why not semantic-only?** Semantic search is powerful for "low sugar fruit" → apple, but it requires embedding every query and can be slower. For a food database where users often search by name, keyword-first gives instant results with minimal overhead.

**Result:** Users get fast, relevant results for both exact matches and common typos, without unnecessary embedding computation.

#### Diabetes Filtering

**Why:** When `user.has_diabetes` is true, search can optionally filter to `diabetes_friendly` foods only. This personalizes results for users who need stricter dietary guidance.

**Result:** Diabetic users see more relevant options without manual filtering.

---

### 10.3 Chatbot Architecture

#### RAG (Retrieval-Augmented Generation)

**Why:** Instead of calling an external LLM (OpenAI, etc.) for every question, the system embeds the user's message and retrieves relevant food documents from a vector store. Responses are built from retrieved data using rule-based templates. This avoids API costs, latency, and the risk of LLM "hallucination" for nutrition facts.

**Result:** Fast, deterministic, and factually grounded answers based on the curated food database. No external API dependency.

#### Rule-Based Intent Detection

**Why:** Intent is detected by keyword matching (greeting, GI, carbs, stability) before RAG. This ensures that general questions (e.g. "What is glycemic index?") get a consistent, educational response without needing to retrieve foods. Food-specific questions (e.g. "Is matooke good for diabetes?") trigger RAG retrieval.

**Result:** Predictable behavior, easier to tune and debug, and clear separation between general knowledge and food-specific answers.

#### ChromaDB (Vector Store)

**Why:** ChromaDB is a lightweight, embeddable vector database that persists to disk. It handles similarity search efficiently and requires no separate server. The system also has an in-memory fallback (NumPy cosine similarity) if ChromaDB is unavailable.

**Result:** RAG retrieval works in production with persistence; the app still runs in constrained environments.

#### Sentence Transformers (all-MiniLM-L6-v2)

**Why:** This model produces 384-dimensional embeddings, is fast, and works well for semantic similarity of short text (food names, descriptions). It runs locally—no API calls—and is widely used for retrieval tasks.

**Result:** Semantic search over the food database without external dependencies; good balance of quality and speed.

#### TF-IDF Fallback

**Why:** If `sentence-transformers` is not installed (e.g. in a minimal environment), the system falls back to `scikit-learn`'s TF-IDF. This allows the app to run without heavy ML dependencies.

**Result:** The chatbot works even when the full embedding model cannot be loaded; quality may be lower but the system remains functional.

#### Disclaimer on Every Response

**Why:** Nutrition advice can have health implications. The disclaimer ("This is general information only. Consult your healthcare provider for medical advice.") protects users and the system from liability and clarifies that the chatbot is informational, not a substitute for professional care.

**Result:** Users understand the limitations; the system aligns with responsible health-software practices.

---

### 10.4 Recommendations Logic

#### Scoring Algorithm

**Why:** The scoring weights (GI ≤ 40: +30, GI ≤ 55: +20, fiber ≥ 5: +15, etc.) reflect clinical guidance: low glycemic index and high fiber are beneficial for blood sugar control. The `diabetes_friendly` flag adds a bonus when the food is explicitly marked suitable.

**Result:** Recommendations prioritize foods that are evidence-based for diabetes management.

#### Different max_gi for Diabetic vs Non-Diabetic

**Why:** Diabetic users get `max_gi = 50` (stricter); non-diabetic get `55`. This tailors recommendations to the user's health profile without requiring complex configuration.

**Result:** More appropriate suggestions for users who need tighter glycemic control.

#### Category Diversification

**Why:** Without diversification, top-scoring foods might all be from one category (e.g. vegetables). Round-robin across categories ensures variety—grains, proteins, fruits, etc.—so users see a balanced set of options.

**Result:** Recommendations feel more useful and varied, not repetitive.

---

### 10.5 Module Architecture

#### Modular Monolith (auth, search, chatbot, etc.)

**Why:** Each domain (auth, search, chatbot, recommendations, glucose) has its own router, service, and optionally repository. This keeps the codebase organized, testable, and easier to extend. It also follows a microservice-style structure internally without the operational complexity of separate services.

**Result:** Clear boundaries and responsibilities; new features can be added without touching unrelated code.

#### Repository Pattern (Search, Recommendations, Glucose)

**Why:** Data access is isolated in repository modules. Services contain business logic; repositories handle SQL queries. This separation makes it easier to change the database or add caching later without rewriting business logic.

**Result:** Maintainable data layer; easier to test services with mocked repositories.

---

### 10.6 Frontend Design

#### Card-Based Layout

**Why:** Cards group related information (food name, calories, glycemic index) and provide clear visual hierarchy. They work well on both desktop and mobile and are a familiar pattern for health and nutrition apps.

**Result:** Consistent, scannable UI; good mobile UX.

#### Single Page Application (SPA)

**Why:** React Router enables client-side navigation without full page reloads. The app feels responsive; users can switch between Search, Chatbot, Recommendations, etc. without losing context.

**Result:** Faster perceived performance and a smoother user experience.

#### Local Storage for Token

**Why:** The JWT is stored in `localStorage` so the user stays logged in across page refreshes. The token is sent with every API request via the `Authorization` header.

**Result:** Persistent login sessions; users do not need to authenticate on every visit.

---

### 10.7 Data & Seeding

#### Uganda Food Dataset

**Why:** The target audience includes Uganda; local staples (matooke, posho, cassava) must be in the database. The system seeds from `uganda_food_nutrition_dataset(in).csv` to ensure culturally relevant content.

**Result:** Users can search and get recommendations for foods they actually eat.

#### RAG Build on Startup

**Why:** The vector store is built on application startup from the food database. This ensures the chatbot always has up-to-date embeddings when new foods are seeded.

**Result:** Chatbot answers reflect the current food database without manual re-indexing.

---

### 10.8 Summary of Results Achieved

| Decision | Rationale | Result |
|----------|-----------|--------|
| FastAPI | Modern API framework, validation, docs | Clean API, fewer bugs |
| SQLite default | Simplicity, no server | Easy setup, portable |
| JWT | Stateless auth | Scalable, client-friendly |
| RAG + rules | No LLM dependency, grounded answers | Fast, accurate, low cost |
| Keyword + fuzzy search | Fast, handles typos | Good UX for food search |
| Scoring + diversification | Evidence-based, varied | Relevant recommendations |
| Modular backend | Separation of concerns | Maintainable, testable |
| React SPA | Fast navigation | Responsive UX |

---

## Appendix: File Reference

| Purpose | Path |
|---------|------|
| API entry | backend/api/main.py |
| Models | backend/api/models.py |
| Config | backend/api/core/config.py |
| Auth | backend/api/modules/auth/ |
| Search | backend/api/modules/search/ |
| Chatbot | backend/api/modules/chatbot/ |
| Recommendations | backend/api/modules/recommendations/ |
| Glucose | backend/api/modules/glucose/ |
| RAG (disabled in API) | Historical: `ml-services/` embedding & chatbot modules; live chatbot uses DB search |
| Seed | backend/api/utils/seed.py |
| Frontend entry | frontend/src/main.jsx |
| App & routing | frontend/src/App.jsx |
| API client | frontend/src/lib/api.js |
| Layout | frontend/src/components/layout/Layout.jsx |
