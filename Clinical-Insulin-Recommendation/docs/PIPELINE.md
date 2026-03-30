# GlucoSense Data Pipeline and System Flow

This document describes how data is generated, stored, and fed into the **GlucoSense** API and UI on first run and during normal operation.

For the **full integrated workspace** (GlucoSense + Meal Plan + offline training), see **[../../../SYSTEM_PIPELINE.md](../../../SYSTEM_PIPELINE.md)**.

---

## 1. High-level flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  FIRST RUN (or empty DB)                                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. Backend starts  →  init_db()  →  Creates SQLite tables                   │
│  2. run_seed_if_needed()  →  Seeds tables if empty                           │
│  3. Seed writes: notifications, messages, glucose_readings, patient_context,  │
│     app_settings, sample records                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  RUNTIME                                                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  Frontend                    Backend API                     Database        │
│  ─────────                   ───────────                     ────────        │
│  GET /api/health        →    init_db + seed            →     reads/writes   │
│  GET /api/notifications →   get_notifications()        →     notifications  │
│  GET /api/messages      →   get_messages()             →     messages       │
│  GET /api/patient-context → get_patient_context()      →     patient_context │
│  GET /api/glucose-trends →  get_glucose_readings()     →     glucose_readings│
│  GET /api/records       →   get_records()              →     records         │
│  GET /api/settings      →   get_setting()              →     app_settings   │
│  POST /api/recommend    →   run_recommend + insert_record + upsert_patient   │
│  POST /api/dose         →   insert_dose_event()        →     dose_events    │
│  POST /api/messages     →   insert_message()           →     messages       │
│  PATCH /api/notifications/read → mark_notifications_read()                  │
│  PUT /api/settings      →   set_setting()              →     app_settings   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Seed data (first-time generation)

When the backend starts and the database is empty (or missing), `run_seed_if_needed()` in `src/insulin_system/storage/seed_data.py` runs:

| Data            | Source                    | Purpose                                      |
|-----------------|---------------------------|----------------------------------------------|
| **notifications** | 3 sample rows             | Top bar dropdown shows alerts                |
| **messages**      | 3 sample care-team messages| Messages page shows conversation             |
| **glucose_readings** | ~74 actual + predicted values over 72h | Chart on Dashboard and Glucose Trends |
| **patient_context** | Name, condition, glucose 128, carbs 45, activity 30 | Sidebar “Recent metrics”        |
| **app_settings**   | units=mg/dL, theme=light, notifications_enabled=true | Settings panel              |
| **records**        | 3 sample recommendation records | Reports page has rows                  |

Seed is **idempotent**: it only inserts when the corresponding table is empty (or for patient_context/settings, overwrites with defaults once).

---

## 3. Database schema (relevant tables)

- **records** – Prediction/recommendation audit (from POST /predict, /explain, /recommend).
- **notifications** – id, created_at, text, unread.
- **messages** – id, created_at, sender, text.
- **glucose_readings** – id, reading_at, value, is_predicted.
- **dose_events** – id, created_at, meal_bolus, correction_dose, total_dose, request_id.
- **app_settings** – key, value.
- **patient_context** – Single row (id=1): name, condition, glucose, carbohydrates, activity_minutes, updated_at.

---

## 4. Training pipeline (model data)

Separate from runtime/seed data, **offline training** is implemented by **`clinical_insulin_pipeline`** (`python run_clinical_insulin_pipeline.py`). It writes **`outputs/clinical_insulin_pipeline/latest/`** (regression bundle, metrics, plots).

The **FastAPI** CDS path loads an **`InferenceBundle`** from **`outputs/best_model/`** when present (`load_best_model`). That file may be produced by a **legacy-compatible** training path or copied from a compatible bundle; until present, some routes may return **503** or use stubs — see **`outputs/README.md`** and `insulin_system/persistence/bundle.py`.

- **Input:** CSV with patient features (default: `data/SmartSensor_DiabetesMonitoring.csv`).
- **Runtime:** No seed data is used for model weights; seed data only populates demo DB content.

---

## 5. End-to-end sequence (first run)

1. Start backend: `uvicorn app:app --host 0.0.0.0 --port 8000`
2. First request (e.g. GET `/api/health` or any `/api/*`) triggers `init_db()` and `run_seed_if_needed()`.
3. Database file is created at `outputs/glucosense.db` and seed data is written.
4. Frontend starts (e.g. `npm run dev`), calls `/api/notifications`, `/api/messages`, `/api/patient-context`, `/api/glucose-trends`, `/api/records`, `/api/settings`.
5. UI displays notifications, messages, sidebar metrics, chart, reports table, and settings from the seeded (and later live) data.
6. User actions (e.g. “Administer dose”, “Send message”, “Get recommendation”) call POST/PATCH/PUT endpoints and update the database; the UI refreshes from the same API.

---

## 6. File reference

| Component        | Path |
|-----------------|------|
| DB init + tables | `backend/src/insulin_system/storage/db.py` |
| Seed logic       | `backend/src/insulin_system/storage/seed_data.py` |
| API routes       | `backend/src/insulin_system/api/routes.py` |
| Clinical training | `backend/src/clinical_insulin_pipeline/` |
| DB file (default)| `outputs/glucosense.db` |
