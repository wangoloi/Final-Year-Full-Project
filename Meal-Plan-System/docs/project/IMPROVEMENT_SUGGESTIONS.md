# Glocusense – Improvement Suggestions

> **Context (2026):** The running API is **FastAPI** under `backend/` (`/api/auth`, `/api/search`, `/api/glucose`, …). Items below may mention **`/api/v1`** or scripts that no longer exist—translate to the current module layout when implementing.

Based on a full system walkthrough (frontend + backend), here are prioritized improvement areas and their impact.

---

## 1. **Data Seeding (Critical – Immediate Value)**

**Current state:** If the food table is empty, search/recommendations look bare until data loads.

**Action:** Ensure **`python backend/run.py`** has run (CSV seed runs in a background thread), or run **`python backend/scripts/seed_foods.py`** from the repo root.

**Impact:** Enables core flows (search, meal logging, recommendations). Without this, the app feels non-functional.

---

## 2. **Profile Save API (High – User Trust)**

**Current state:** Profile page has a Save button but only logs to console. No API call.

**Action:**
- Add `PATCH /api/v1/users/me` (or `PUT`) to update `first_name`, `height`, `weight`, `age`, `activity_level`.
- Add `GET /api/v1/users/me` to return full profile for form prefill.
- Wire `ProfilePage` to these endpoints.

**Impact:** Users can persist health data. Needed for future personalization (recommendations, calorie targets).

---

## 3. **Goals Persistence (High – Core Feature)**

**Current state:** `list_goals` returns `[]`, `create_goal` returns fake data and does not persist. No `Goal` model.

**Action:**
- Add `Goal` model (user_id, goal_type, target_value, current_value, unit, deadline, status).
- Implement real CRUD in `api_v1.py` (list, create, update, delete).
- Add migration for `goals` table.

**Impact:** Goals become usable and visible on the dashboard. Supports accountability and tracking.

---

## 4. **Meals Persistence (High – Core Feature)**

**Current state:** `list_meals` returns `[]`, `create_meal` returns a fake object and ignores `items` (food_id, quantity).

**Action:**
- Add `Meal` and `MealItem` models (meal → meal_items → food_id, quantity).
- Persist meals and items in `create_meal`.
- Compute `total_calories` from items.
- Return real meals in `list_meals`.

**Impact:** Meal logging works end-to-end. Dashboard “Recent Meals” becomes meaningful.

---

## 5. **Glucose Logging UI (High – Diabetes Focus)**

**Current state:** Dashboard “Log Reading” navigates to `/meals` (meal logger). No dedicated glucose entry flow.

**Action:**
- Add a “Log Glucose” dialog or page (value, type: fasting/post_meal/pre_meal, notes).
- Call `glucoseApi.create()`.
- Fix “Log Reading” button to open this flow instead of navigating to meals.

**Impact:** Users can log blood glucose without confusion. Time in Range and charts become useful.

---

## 6. **Search Category Alignment (Medium – UX)**

**Current state:** Search filters use `breakfast`, `lunch`, `dinner`, `snack`. `FoodItem.category` uses `grains`, `vegetables`, `proteins`, etc.

**Action:** Either:
- Change Search filters to match `FoodItem.category`, or
- Add a `meal_type` (or similar) field to foods and filter by that.

**Impact:** Filters return relevant results instead of empty lists.

---

## 7. **Recommendations Personalization (Medium – Differentiation)**

**Current state:** Recommendations page shows first 12 foods from `/foods` (filtered by “not interested”). No personalization by profile, goals, or glucose.

**Action:**
- Extend existing **`GET /api/recommendations`** with stronger personalization (engine + user profile).
- Filter by low GI, diabetes-friendly, and optionally user preferences.
- Consider integrating with `diabetic_diet_meal_plans_with_macros_GI.csv` for richer meal plans.

**Impact:** Recommendations feel tailored and more useful for diabetes management.

---

## 8. **Chatbot Enhancement (Medium – Engagement)**

**Current state:** Simple keyword-based replies.

**Action:**
- Add more intent handlers (e.g., “suggest low GI breakfast” → return specific foods).
- Optionally integrate RAG over diet datasets for factual answers.
- Add quick actions that link to Search/Recommendations with pre-filled queries.

**Impact:** Chatbot becomes more helpful and drives users to relevant features.

---

## 9. **“Add to Meal” Integration (Medium – UX)**

**Current state:** “Add to meal” in Recommendations and Meal Logger “Add to Meal” both exist, but Recommendations’ “Add to meal” is a placeholder.

**Action:** Wire Recommendations “Add to meal” to `mealsApi.create()` with the selected food and default meal type.

**Impact:** Seamless flow from discovery to logging.

---

## 10. **Empty States & Onboarding (Low – Polish)**

**Current state:** Empty lists show “No goals yet”, “No meals logged”, etc. No guided first steps.

**Action:**
- Add short onboarding tips (e.g., “Log your first glucose reading”, “Add a goal”).
- Optional: first-time checklist or progress indicator.

**Impact:** New users understand what to do first.

---

## 11. **Profile Prefill (Low – UX)**

**Current state:** Profile form may not load existing `height`, `weight`, `age`, `activity_level` from backend.

**Action:** Fetch user profile on load and set form defaults. Ensure **`GET /api/auth/me`** returns the fields you need (extend `User.to_dict()` if required).

**Impact:** Users see their saved data and can edit it correctly.

---

## 12. **Error Handling & Feedback (Low – Robustness)**

**Current state:** API errors may show generic messages. Mutations may not show success/error toasts.

**Action:**
- Add toast/snackbar for success and error on mutations.
- Improve 401 handling (e.g., redirect to login, clear token).
- Validate inputs and return clear error messages.

**Impact:** Users get clear feedback and understand when something fails.

---

## Summary Priority Matrix

| Priority | Area                    | Effort | Value   |
|----------|-------------------------|--------|---------|
| P0       | Data seeding            | Low    | Critical|
| P1       | Profile API             | Medium | High    |
| P1       | Goals persistence       | Medium | High    |
| P1       | Meals persistence       | Medium | High    |
| P1       | Glucose logging UI      | Medium | High    |
| P2       | Search category fix     | Low    | Medium  |
| P2       | Recommendations API     | Medium | Medium  |
| P2       | Chatbot enhancement     | Medium | Medium  |
| P2       | Add to meal integration | Low    | Medium  |
| P3       | Empty states            | Low    | Low     |
| P3       | Profile prefill         | Low    | Low     |
| P3       | Error handling          | Low    | Low     |

---

## Quick Wins (Do First)

1. Run `python add_foods.py` – immediate usability.
2. Fix “Log Reading” button target – correct navigation.
3. Align Search categories with `FoodItem.category` – filters work.

---

## Recommended Implementation Order

1. **Data seeding** – unblock all food-related features.
2. **Profile API + frontend** – enable profile completion and future personalization.
3. **Goals model + API** – make goals functional.
4. **Meals + MealItem models + API** – make meal logging functional.
5. **Glucose logging UI** – complete the diabetes tracking loop.
6. **Search category alignment** – improve discovery.
7. **Recommendations personalization** – differentiate the product.
8. **Chatbot + Add to meal** – improve engagement and flow.
