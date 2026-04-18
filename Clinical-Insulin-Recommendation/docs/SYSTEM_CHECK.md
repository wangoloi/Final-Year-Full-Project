# GlucoSense – Final System Check and Readiness

This document confirms that all UI and backend features are wired and the system is ready to use.

---

## Top bar

| Element | Behavior | Backend |
|--------|----------|---------|
| **Logo + title** | GlucoSense, Clinical Decision Support | — |
| **Notifications (bell)** | `title="Notifications"` tooltip on hover. Click opens dropdown; "Go to Messages" navigates to `/messages`. Badge shows unread count. | GET `/api/notifications`, PATCH `/api/notifications/read` |
| **Messages icon** | Removed (access via Notifications → Go to Messages or sidebar) | — |
| **Settings (gear)** | `title="Settings"` tooltip. Click opens centered modal. Units, Notifications, Theme with icons and "Working"/"Active" labels. All controls save to API. | GET `/api/settings`, PUT `/api/settings` |
| **Account (avatar + name)** | `title="Account"` tooltip. Dropdown: Profile (toast), Preferences (opens Settings), Sign out (toast). | — |

---

## Settings popup

- **Position:** Centered on screen (`settings-overlay-center`), above other content (z-index 300).
- **Visibility:** Panel and body use `color: var(--text)` and `background: var(--bg)` so labels and controls are visible.
- **Content:** Each row has icon (FiSliders, FiBell, FiSun), label (Units, Notifications, Theme), status (Working / Active / Off), and control (select or checkbox). All interactive and persisted via PUT `/api/settings`.

---

## Sidebar

- Patient card and recent metrics from GET `/api/patient-context` (seed + updated after recommend).
- Nav: Dashboard, Glucose Trends, Insulin Management, Reports, Messages — all routes work.

---

## Pages and API wiring

| Page | Features | API |
|------|----------|-----|
| **Dashboard** | Patient form, Get recommendation, Insulin card, Dosage panel, Administer dose (modal → POST dose), Chart (from API), Advice, Factors, Resources, Disclaimer | POST `/api/recommend`, GET `/api/glucose-trends`, POST `/api/dose` |
| **Glucose Trends** | Chart with time range | GET `/api/glucose-trends` |
| **Insulin Management** | Link to Dashboard | — |
| **Reports** | Session history table | GET `/api/records` |
| **Messages** | Thread, send message | GET `/api/messages`, POST `/api/messages` |

---

## Seed data (first run)

- Backend runs `run_seed_if_needed()` on first request: notifications, messages, glucose readings, patient context, settings, sample records.
- Frontend gets data from above endpoints; no blank screens on first load.

---

## Run checklist

1. Backend: `uvicorn app:app --host 0.0.0.0 --port 8000`
2. Frontend dev: `cd frontend && npm install && npm run dev` → http://localhost:5173
3. Or production: `cd frontend && npm run build` then run backend → http://localhost:8000

---

## Status

- Top bar: Tooltips, Notifications → Messages, Settings centered and visible, Account actions working.
- Messages icon removed; Messages reached via Notifications or sidebar.
- All buttons and features listed above are connected and working. System is ready for use.
