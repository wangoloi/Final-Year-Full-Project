# GlucoSense — Full System Analysis

**Document purpose:** Technical analysis of the integrated GlucoSense workspace for documentation and presentation support.  
**Scope:** `Clinical-Insulin-Recommendation` (GlucoSense CDS portal) + `Meal-Plan-System` (Glocusense nutrition app) + integration layer.

---

## 1. Executive summary

GlucoSense is a **dual-stack clinical decision-support (CDS) ecosystem** aimed at Type 1 diabetes–oriented workflows in a **demo/education** setting. It combines:

1. **Insulin dose recommendation** using a trained ML bundle (regression), structured API responses, optional explainability (e.g. SHAP where configured), safety checks, alerts, and clinician-facing dashboards.
2. **Personalized nutritional management** via a separate Meal Plan application: food search, constraint-based meal recommendations, optional RAG + LLM chatbot, glucose logging, and a **synthetic CSV “Smart Sensor” demo** (not live device integration).

Outputs are **decision support only**; the system states that a qualified clinician must validate recommendations.

---

## 2. Stakeholders and roles

| Role | Primary surface | Responsibilities |
|------|-----------------|------------------|
| **Clinician** | GlucoSense React workspace (`/workspace/*`) | Register patients, run assessments, receive insulin guidance, confirm doses, review trends, reports, alerts; embedded Meal Plan via iframe + SSO. |
| **Patient** | GlucoSense `/meal-plan` or standalone Meal Plan UI | Nutrition-focused flows (auth, onboarding, meal plan, chatbot, glucose). |
| **Developer / researcher** | APIs `:8000` / `:8001`, offline pipelines | Train bundles, configure env, deploy Docker. |

---

## 3. High-level topology

| Process | Typical port | Responsibility |
|--------|--------------|----------------|
| **GlucoSense API** | 8000 | CDS REST API, SQLite, model inference |
| **GlucoSense UI** | 5173 | React (Vite) SPA; proxies `/api` → 8000 |
| **Meal Plan API** | 8001 | Auth (JWT), foods, RAG/chat, recommendations, glucose, sensor-demo |
| **Meal Plan UI** | 5175 | React SPA; proxies `/api` → 8001 |

**Integration:** Dashboard embeds Meal UI in an **iframe**; **JWT SSO** (`postMessage` + shared embed secret) avoids duplicate login. Meal API must remain on **8001** to avoid route collision with GlucoSense **8000**.

---

## 4. GlucoSense (Clinical-Insulin-Recommendation)

### 4.1 Frontend

- **Stack:** React 18, React Router 6, Vite 5, Recharts, jsPDF.
- **Routes:** Landing/login; `/workspace` (clinician) with Dashboard, Patients, Glucose trends, Insulin management, Reports, Alerts, Model info; `/meal-plan` (patient meal shell).
- **State:** `ClinicalContext` — session, theme, patients, notifications, alerts.
- **API:** Relative `/api` via Vite proxy to FastAPI.

### 4.2 Backend

- **Framework:** FastAPI (`backend/app.py`), routes under `/api`.
- **Core package:** `insulin_system` — routes, validation, **engine** (predict / explain / recommend), persistence, safety, monitoring.
- **Key endpoints (illustrative):** `POST /api/recommend`, `POST /api/predict`, `POST /api/explain`, patients CRUD, glucose trends, dose events, alerts, feedback, `GET /api/model-info`, health/monitoring.

### 4.3 ML and data

- **Runtime:** Loads **`InferenceBundle`** (joblib) from `outputs/best_model/` or override env; inference via `clinical_insulin_pipeline.inference.predict_insulin_dose` (IU regression) when wired.
- **Offline pipeline:** `clinical_insulin_pipeline/` trains on `SmartSensor_DiabetesMonitoring.csv`; outputs under `outputs/clinical_insulin_pipeline/latest/`.
- **Persistence:** SQLite — patients, records, glucose readings, dose events, alerts, notifications, feedback, backups.

### 4.4 Safety and governance

- Validation layers (Pydantic, domain rules), audit logging, critical alerts after recommendation, disclaimers (CDS not a substitute for clinical judgment).

---

## 5. Meal Plan (Glocusense)

### 5.1 Backend

- **Framework:** FastAPI (`api/main.py`), modular routers: `auth`, `search`, `chatbot`, `recommendations`, `glucose`, `sensor_demo`.
- **Auth:** JWT; **embed token** for GlucoSense iframe (`GLUCOSENSE_EMBED_KEY`).
- **Recommendations engine:** Pools, scoring, optimization, constraints, explainability (`api/modules/recommendations/engine/`).
- **Chatbot:** Chroma RAG + sentence-transformer embeddings; OpenAI or Ollama when configured; else legacy rule-based builder.
- **Search:** SQLite + fuzzy; optional Typesense.
- **Sensor demo:** Reads **CSV** (`SmartSensor_DiabetesMonitoring.csv`) for charts — **not** physical IoT/CGM integration.

### 5.2 Frontend

- Routes: auth (landing, login, register), onboarding, `/app/*` shell — Dashboard, Chatbot, Glucose, MealPlan, Smart Sensor.
- **Design tokens:** `UI_DESIGN_GUIDE.md` — spacing, cards, `page-header`, grid-2, alerts.

---

## 6. End-to-end flows

### 6.1 Clinician: assessment → recommendation → dose

1. Select/register patient.
2. Dashboard assessment → `POST /api/recommend` with `patient_id` and validated body.
3. Engine runs bundle; record persisted; glucose/trends updated; alerts may fire.
4. UI shows recommendation; clinician may log dose and submit feedback.

### 6.2 Meal journey

- Clinician: embedded meal app + link to full meal experience.
- Patient: meal-plan shell backed by Meal API only (separate DB from clinical CDS).

---

## 7. Deployment

- **Local:** Scripts or three terminals (see root `README.md`).
- **Docker:** Compose maps GlucoSense, meal API, meal web (e.g. 8080/8081/8082); env for CORS, JWT, embed secret.
- **Training:** Not auto-run in containers; bundles supplied offline or via volume.

---

## 8. Strengths and limitations

**Strengths**

- Clear separation of **clinical insulin CDS** vs **nutrition** services.
- Hybrid **ML + rules/safety** alignment with literature on diabetes CDS.
- Explainability hooks (model info, feature importance, narrative helpers where configured).
- Documented pipelines (`ARCHITECTURE.md`, `SYSTEM_PIPELINE.md`, subsystem `DESIGN_STRUCTURE.md`).

**Limitations (explicit)**

- **No integration with real IoT, CGM, or wearable sensors** in scope; sensor routes use **demo/synthetic CSV** data.
- CDS outputs require **human validation**; not certified medical device software.
- Resource settings (e.g. low-resource clinics) depend on deployment and data availability outside this repo.

---

## 9. Document map (repository)

| Document | Content |
|----------|---------|
| `ARCHITECTURE.md` | Topology, components, integration |
| `SYSTEM_PIPELINE.md` | Runtime + ML + data artifacts |
| `Clinical-Insulin-Recommendation/docs/DESIGN_STRUCTURE.md` | CDS layers, bundle paths |
| `Meal-Plan-System/docs/DESIGN_STRUCTURE.md` | Meal API modules, RAG, routes |
| `Meal-Plan-System/frontend/docs/UI_DESIGN_GUIDE.md` | UI tokens and patterns |

---

*Analysis aligned with the workspace as of the documentation generation date.*
