## Frontend–Backend Integrity & Hardcoding Audit (GlucoSense + Meal Plan)

### Scope
- **Clinical portal**: `Clinical-Insulin-Recommendation/frontend` (Vite/React)
- **Meal Plan app**: `Meal-Plan-System/frontend` (Vite/React + Tailwind)
- **Clinical API**: `Clinical-Insulin-Recommendation/backend` (FastAPI, default `:8000`)
- **Meal Plan API**: `Meal-Plan-System/backend` (FastAPI, default `:8001`)

### 1) Communication verification (endpoint mapping)

#### Clinical portal → Clinical API (via Vite proxy `/api` → `:8000`)
- **Health (liveness)**: `GET /api/health/live`
- **Assessments**: `POST /api/recommend`
- **Dose events**: `POST /api/dose`
- **Clinician feedback**: `POST /api/feedback`
- **Records**: `GET /api/records?limit=...`, `DELETE /api/records/{id}`
- **Patients**: `GET /api/patients`, `GET /api/patients/{id}`, `POST /api/patients`, `PUT /api/patients/{id}`, `DELETE /api/patients/{id}`, `POST /api/patients/{id}/restore`, `DELETE /api/patients/{id}/permanent`
- **Patient-linked lists**: `GET /api/patients/{id}/records`, `GET /api/patients/{id}/glucose-readings`, `GET /api/patients/{id}/dose-events`
- **Notifications**: `GET /api/notifications`, `POST /api/notifications`, `DELETE /api/notifications/by-type/{type}`, `PATCH /api/notifications/read`
- **Alerts**: `GET /api/alerts`, `POST /api/alerts/resolve`, `POST /api/alerts/resolve-all`
- **Settings**: `GET /api/settings`, `PUT /api/settings`
- **Patient context**: `GET /api/patient-context`

Backend source of truth: `Clinical-Insulin-Recommendation/backend/src/insulin_system/api/routes.py`.

#### Clinical portal → Meal Plan API (SSO only, via Vite proxy `/api/auth` → `:8001`)
- **SSO token provision**: `POST /api/auth/integration/glucosense` with header `X-Glucosense-Embed-Key`

Backend source of truth: `Meal-Plan-System/backend/api/modules/auth/router.py`.

#### Meal Plan frontend → Meal Plan API (via Vite proxy `/api` → `:8001`)
- Auth: `POST /api/auth/login`, `POST /api/auth/register`, `GET /api/auth/me`, `PATCH /api/auth/profile`, `POST /api/auth/onboarding/complete`
- Search: `GET /api/search?q=...&limit=...`
- Chatbot: `GET/POST/DELETE /api/chatbot/sessions*`, `POST /api/chatbot/message`
- Recommendations: `GET /api/recommendations?limit=...`, `GET /api/recommendations/engine`, `POST /api/recommendations/feedback`
- Glucose: `GET /api/glucose`, `POST /api/glucose`

Backend source of truth: `Meal-Plan-System/backend/api/main.py` and module routers under `Meal-Plan-System/backend/api/modules/*`.

### 2) Environment & configuration audit

#### Issues found
- **Hardcoded fallback Meal Plan origin** in Clinical portal (`http://localhost:5175`) caused inconsistent behavior on LAN/remote dev and violated “no hardcoding”.
- **Hardcoded fallback SSO secret** in Clinical portal (`dev-embed-local-only`) meant “misconfigured but still kind of works” and made misconfigurations hard to diagnose.
- **Outdated `.env.example`** in Meal Plan frontend referenced an old `VITE_API_BASE_URL`/`VITE_WS_URL` setup not used by the current code (the app relies on the Vite `/api` proxy).

#### Fixes applied
- **Clinical portal now requires env**:
  - `VITE_MEAL_PLAN_URL`
  - `VITE_MEAL_PLAN_EMBED_SECRET`
  - File: `Clinical-Insulin-Recommendation/frontend/src/constants.js`
  - Updated: `Clinical-Insulin-Recommendation/frontend/.env.example`
- **Meal Plan `.env.example`** updated to match reality (proxy-based) and to document:
  - `VITE_ALLOWED_GLUCOSENSE_ORIGINS` (optional for embed postMessage allowlist)
  - File: `Meal-Plan-System/frontend/.env.example`

### 3) Hardcoding detection in frontend UI

#### Issues found
- **Silent failures**: multiple API paths swallowed errors (`catch {}` / `.catch(() => {})`) and returned `null`/`[]` on failure, producing “stale UI with no feedback”.
- **Inline styles** used for error/empty states in a few places (less critical, but inconsistent).
- **Operational port assumptions** in user-facing copy (e.g. “start backend on 8000/8001”) are acceptable for this dev/demo environment but were not consistently shown on failure.

#### Fixes applied
- Added a **global, dismissible API error banner** in the Clinical portal clinician shell:
  - `Clinical-Insulin-Recommendation/frontend/src/components/ApiErrorBanner.jsx`
  - Wired into `Clinical-Insulin-Recommendation/frontend/src/components/Layout.jsx`
  - Styled in `Clinical-Insulin-Recommendation/frontend/src/index.css`
- Updated `ClinicalContext` to expose `apiError`, `reportApiError()`, and `clearApiError()` and to report failures instead of swallowing them:
  - `Clinical-Insulin-Recommendation/frontend/src/context/ClinicalContext.jsx`
- Centralized request error handling for Clinical portal services:
  - `Clinical-Insulin-Recommendation/frontend/src/services/http.js` (`requestJson`)
  - Migrated `clinicalApi.js`, `patientsApi.js`, and `dashboardApi.js` to use it.
- Refactored key pages/components to use centralized APIs and surface errors:
  - Settings calls in `Layout.jsx` now use `clinicalApi.getSettings/putSettings`
  - `Reports.jsx` uses `clinicalApi` and reports failures via banner
  - `PatientRecords.jsx` shows a visible warning state if loads fail
  - `AssessmentPage.jsx` reports recommendation and dose-record failures via banner
  - `Patients.jsx` reports failures via banner (instead of `window.alert`)

### 4) API integration consistency (centralization)

#### Clinical portal
- **Before**: mix of `apiFetch` + per-service “return [] on error” patterns.
- **After**: shared JSON client (`requestJson`) + consistent error propagation; pages decide whether to show inline warnings and/or the global banner.

#### Meal Plan frontend
- Already centralized in `Meal-Plan-System/frontend/src/lib/api.js`:
  - consistent JSON parsing
  - explicit proxy failure explanation
  - token header handling
  - timeouts + helpful errors

### 5) Error handling & resilience

#### Fixes applied
- **Non-OK responses** now become actionable messages (banner + inline state where appropriate) instead of silent no-ops.
- **Network failures**: Clinical `apiFetch` already returns a synthetic `503` JSON Response; `requestJson` now turns that into a thrown Error, which surfaces via banner.

#### Current limitation
- Clinical production build sometimes fails on this machine due to **Vite/esbuild OOM** (Go runtime crash). This is environmental and independent of code correctness.

### 6) Data flow validation (backend → state → UI)
- Assessment flow aligns with backend:
  - UI posts to `POST /api/recommend` and expects either:
    - `422 { detail, errors: [...] }` (handled)
    - `200 { request_id, predicted_class, confidence, dosage_action, ... }` (rendered)
- Dose record:
  - UI posts to `POST /api/dose` and now reports failures via banner.
- Meal Plan SSO:
  - UI posts to `POST /api/auth/integration/glucosense` and postMessages the JWT to the iframe.
  - Misconfiguration (missing env) now throws early with a clear message.

### 7) Validation checks performed
- Confirmed services are reachable in an integrated dev run:
  - `GET http://127.0.0.1:8000/api/health/live` → `{ status:"ok", live:true }`
  - `GET http://127.0.0.1:8001/api/health` → `{ status:"ok", app:"glocusense-meal-plan" }`
  - Vite HTML served on `:5173` (portal) and `:5175` (meal app)

### 8) Summary of resolved issues
- **Removed hardcoded fallbacks** for Meal Plan origin and SSO secret in Clinical portal.
- **Centralized API error handling** in Clinical portal with shared `requestJson`.
- **Eliminated silent failures** by surfacing errors in a global banner and page-level UI states.
- **Updated env documentation** to reflect current proxy-based architecture.

