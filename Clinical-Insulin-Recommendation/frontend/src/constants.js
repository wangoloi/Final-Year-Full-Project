/**
 * Domain and UI constants for GlucoSense.
 * Single source of truth for bounds, thresholds, and display values.
 */

// Medical value ranges (must match backend validation)
export const AGE_MIN = 0
export const AGE_MAX = 100
export const GENDER_OPTIONS = ['Male', 'Female']
export const GLUCOSE_MIN = 20
export const GLUCOSE_MAX = 600
export const BMI_MIN = 12
export const BMI_MAX = 70
export const HBA1C_MIN = 4
export const HBA1C_MAX = 20
export const WEIGHT_MIN = 20
export const WEIGHT_MAX = 300

// Legacy inputs removed from UI (kept in backend with safe defaults)

/** Smart Sensor pipeline — required with measurement (API + model) */
export const MEAL_CONTEXT_OPTIONS = ['before_meal', 'after_meal', 'fasting']
export const ACTIVITY_CONTEXT_OPTIONS = ['resting', 'active', 'post_exercise']

// Chart display
export const CHART_REFERENCE_LINE_LOW_MGDL = 70
export const CHART_REFERENCE_LINE_HIGH_MGDL = 180
export const CHART_Y_DOMAIN_MIN = 60
export const CHART_Y_DOMAIN_MAX = 220
export const CHART_HEIGHT_DASHBOARD = 280
export const CHART_HEIGHT_TRENDS = 360

// Recommendation UI
export const CONFIDENCE_CAUTION_THRESHOLD_PCT = 70
export const CONFIDENCE_HIGH_PCT = 60   // Above this = "High" certainty
export const CONFIDENCE_MEDIUM_PCT = 40 // Above this = "Medium"; below = "Low"
export const EXPLANATION_DRIVERS_DISPLAY_LIMIT = 8

// Certainty tooltip (shown on Insulin recommendation card)
export const CERTAINTY_TOOLTIP = 'The model\'s probability for this recommendation. With 4 options (down, up, steady, no), 25% is random chance. Low values mean multiple options are plausible—use clinical judgment.'

// Form / validation
export const MEDICATION_NAME_MAX_LENGTH = 200

// Timing (ms)
export const FETCH_TREND_DEBOUNCE_MS = 300
export const DOSE_CONFIRM_DELAY_MS = 800

// API
export const ALERTS_FETCH_LIMIT = 50

/** Clinician app routes live under this path (landing stays at `/`). */
export const WORKSPACE_PATH = '/workspace'

/** Optional Meal Plan SSO link page (GlucoSense clinical workspace does not require login). */
export const LOGIN_PATH_CLINICAL = `/login?next=${encodeURIComponent(WORKSPACE_PATH)}`

/** @deprecated use `/meal-plan` directly — no GlucoSense login gate */
export const LOGIN_PATH_MEAL = `/login?next=${encodeURIComponent('/meal-plan')}`

/** Path to the GlucoSense mark in `public/` (Vite `BASE_URL` ends with `/`). */
export const BRAND_LOGO_SRC = `${import.meta.env.BASE_URL ?? '/'}glucosense-logo.svg`

/**
 * Public site URL shown in the UI and browser tab (marketing / production hostname).
 * The address bar still shows the real origin (e.g. localhost) until you deploy and point DNS here.
 * Override with VITE_PUBLIC_SITE_URL (e.g. https://www.glucosense.ug.com).
 */
export function getPublicSiteDisplayUrl() {
  const u = import.meta.env.VITE_PUBLIC_SITE_URL
  if (u && String(u).trim()) return String(u).trim().replace(/\/$/, '')
  return 'https://www.glucosense.ug.com'
}

/** Hostname only, for compact labels (e.g. www.glucosense.ug.com). */
export function getPublicSiteHostname() {
  try {
    const raw = getPublicSiteDisplayUrl()
    const withProto = raw.includes('://') ? raw : `https://${raw}`
    return new URL(withProto).hostname
  } catch {
    return 'www.glucosense.ug.com'
  }
}

/** Glocusense Meal Plan (Vite) origin — integrated dev often uses :5175 (see scripts/start-integrated.ps1). */
export function getMealPlanOrigin() {
  const u = import.meta.env.VITE_MEAL_PLAN_URL || import.meta.env.MEAL_PLAN_URL
  if (u && String(u).trim()) return String(u).trim().replace(/\/$/, '')
  return 'http://localhost:5175'
}

/**
 * Meal Plan FastAPI base URL (no `/api` suffix). SSO must call this directly — not the Vite dev server —
 * because Vite’s `/api` proxy may point at GlucoSense (:8000) instead of the meal API (:8001).
 */
export function getMealPlanApiBaseUrl() {
  const u = import.meta.env.VITE_MEAL_PLAN_API_URL || import.meta.env.MEAL_PLAN_API_URL
  if (u && String(u).trim()) return String(u).trim().replace(/\/$/, '')
  return 'http://127.0.0.1:8001'
}

/**
 * @param {{ embed?: boolean }} [opts] - `embed: true` enables single sign-on from GlucoSense (iframe handoff).
 */
export function getMealPlanAppUrl(opts = {}) {
  const base = `${getMealPlanOrigin()}/app`
  if (opts.embed) {
    return `${base}?${new URLSearchParams({ embed: 'glucosense' }).toString()}`
  }
  return base
}

/** Must match Meal Plan API `GLUCOSENSE_EMBED_KEY` (dev default). Exposed in client — dev/demo only. */
export function getMealPlanEmbedSecret() {
  return (
    import.meta.env.VITE_MEAL_PLAN_EMBED_SECRET ||
    import.meta.env.MEAL_PLAN_EMBED_SECRET ||
    'dev-embed-local-only'
  )
}
