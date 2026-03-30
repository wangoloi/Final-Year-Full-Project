# Typesense food search

Food search (`GET /api/search`) uses **Typesense** when `TYPESENSE_HOST` is set. Otherwise it keeps the previous **SQLite `ILIKE` + RapidFuzz** behavior.

## Local setup

1. Start Typesense:

   ```bash
   docker compose -f backend/docker-compose.typesense.yml up -d
   ```

2. In `backend/.env` (create from `.env.example`):

   ```env
   TYPESENSE_HOST=localhost
   TYPESENSE_PORT=8108
   TYPESENSE_PROTOCOL=http
   TYPESENSE_API_KEY=xyz
   ```

3. Restart the Meal Plan API. After CSV/fallback seed finishes, the app **syncs all `food_items` rows** into the `foods` collection.

## Behavior

- **Query fields:** `name`, `local_name`, `description`, `category`
- **Typo tolerance:** `num_typos=2`
- **Diabetes users:** `filter_by: diabetes_friendly:=true` (same as before)
- **Failure:** Any Typesense error falls back to SQL search automatically

## Collection name

Override with `TYPESENSE_FOODS_COLLECTION` (default: `foods`).
