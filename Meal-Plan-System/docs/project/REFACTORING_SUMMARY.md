# Glocusense Refactoring Summary

> **Historical / coursework context:** Much of this file refers to a **Flask** monolith, `app/`, `/api/v1`, and paths that differ from the current repo. The **current** stack is **`backend/`** (FastAPI) + **`frontend/`** (Vite). Use [../STRUCTURE.md](../STRUCTURE.md) and [../ARCHITECTURE.md](../ARCHITECTURE.md) for the live layout.

## Completed Transformations

### 1. Database & Models
- **New models**: `Goal`, `Meal`, `MealItem`, `GlucoseReading`, `ChatMessage`
- **Migration**: `002_add_goal_meal_glucose_chat` creates all new tables
- **Food categories**: Aligned to `grains`, `vegetables`, `proteins`, `fruits`, `snacks`, `beverages`
- **Data seeding**: `add_foods.py` seeds 15 Ugandan foods including snacks and beverages

### 2. OOP & SOLID Architecture
- **Core module** (`app/core/`): Custom exceptions (`AppError`, `ValidationError`, `NotFoundError`, etc.), structured logging
- **Domain interfaces** (`app/domain/interfaces.py`): Protocol-based repository and service interfaces
- **Repositories** (`app/repositories/`): `UserRepository`, `FoodRepository`, `GoalRepository`, `MealRepository`, `GlucoseRepository`
- **Services** (`app/services/`): `UserService`, `GoalService`, `MealService`, `GlucoseService`, `RecommendationService`, `ChatbotServiceV2`
- **Dependency injection**: Services receive repositories via constructor

### 3. API Improvements (All Implemented)
| Improvement | Status |
|-------------|--------|
| Profile API (GET/PATCH /users/me) | ✅ |
| Goals CRUD (list, create, update, delete) | ✅ |
| Meals with MealItems (persisted, calories computed) | ✅ |
| Glucose logging (GlucoseReading model) | ✅ |
| Search category alignment | ✅ |
| Recommendations API (personalized, low GI) | ✅ |
| Chatbot enhancement (food suggestions, chat history) | ✅ |
| Add to meal from recommendations | ✅ |
| Structured error handling | ✅ |

### 4. Frontend Updates
- **Profile**: Fetches and saves via `usersApi`, prefill from backend
- **Dashboard**: Log Glucose dialog (value, type, notes) instead of navigating to meals
- **Search**: Categories updated to grains, vegetables, proteins, fruits, snacks, beverages
- **Recommendations**: Uses `recommendationsApi`, Add to meal creates meal and navigates
- **API clients**: `usersApi`, `recommendationsApi` added

### 5. Client: React web app only
- **UI**: Vite + React in `frontend/` → FastAPI `/api/*` (dev proxy in `vite.config.js`).
- **Onboarding**: `POST /api/auth/onboarding/complete`, optional `PATCH /api/auth/profile`.
- **No** Expo / React Native / `apps/mobile` in this repo.

### 6. Microservices Structure
- **Modular monolith**: All domains in one Flask app, organized as service modules
- **Services README**: `services/README.md` documents extraction path
- **API Gateway**: Main Flask app routes `/api/v1/*`

### 7. Testing
- **Pytest (current repo):** `backend/tests/conftest.py`, `backend/tests/test_api.py`
- **Run (from repo root):** `pytest` or `python -m pytest backend/tests -v`

### 8. Documentation
- **docs/ARCHITECTURE.md**: System diagram, OOP/SOLID, API endpoints, error format
- **docs/DEPLOYMENT.md**: Backend, frontend, production checklist

## File Structure (New/Modified)

```
app/
  core/           # Exceptions, logging
  domain/         # Interfaces
  repositories/   # Data access
  api/            # Controllers, middleware
  services/       # user_service, goal_service, meal_service, glucose_service,
                 # recommendation_service, chatbot_service_v2
  models.py       # + Goal, Meal, MealItem, GlucoseReading, ChatMessage

frontend/src/
  services/api/   # + users.ts, recommendations.ts
  pages/          # Profile, Dashboard, Search, Recommendations updated

services/        # Microservices README (legacy notes)
tests/           # Pytest suite
docs/            # ARCHITECTURE.md, DEPLOYMENT.md
```

## Quick Start

```bash
# Backend
python backend/run.py

# Web
cd frontend && npm run dev

# Tests (repo root)
pytest -q
```
