/**
 * Fetch wrapper: ngrok header + Meal Plan JWT for Clinical API (when GLUCOSENSE_REQUIRE_AUTH is on).
 */
import { getStoredMealToken } from './auth/mealPlanAuth'

const NGROK_HEADER = { 'ngrok-skip-browser-warning': '1' }

const CLINICAL_BASE = (import.meta.env.VITE_CLINICAL_API_URL || '').replace(/\/$/, '')

export function apiFetch(url, options = {}) {
  const headers = { ...NGROK_HEADER, ...options.headers }
  const token = getStoredMealToken()
  if (token) headers.Authorization = `Bearer ${token}`
  const full = url.startsWith('http') ? url : `${CLINICAL_BASE}${url}`
  return fetch(full, { ...options, headers })
}
