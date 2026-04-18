/**
 * Meal Plan API JWT — source of truth for GlucoSense portal role (server-enforced RBAC).
 */
import { getMealPlanApiBaseUrl } from '../constants'

const TOKEN_KEY = 'glucosense_meal_jwt'

export function getStoredMealToken() {
  try {
    return sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setStoredMealToken(token) {
  try {
    sessionStorage.setItem(TOKEN_KEY, token)
  } catch {
    localStorage.setItem(TOKEN_KEY, token)
  }
}

export function clearStoredMealToken() {
  try {
    sessionStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* ignore */
  }
}

export async function loginMealPlanApi(username, password) {
  const base = getMealPlanApiBaseUrl()
  const res = await fetch(`${base}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = data.detail ?? data.message ?? `Login failed (${res.status})`
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return data
}

export async function fetchMealPlanMe(token) {
  const base = getMealPlanApiBaseUrl()
  const res = await fetch(`${base}/api/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) return null
  return res.json()
}

/** Map Meal Plan user.role to UI clinician | patient */
export function mapServerRoleToUiRole(role) {
  const r = String(role || 'patient').toLowerCase()
  if (r === 'clinician' || r === 'admin') return 'clinician'
  return 'patient'
}
