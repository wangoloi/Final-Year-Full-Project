import { getMealPlanApiBaseUrl, getMealPlanOrigin, getMealPlanEmbedSecret } from '../constants'

const SYNTH_EMAIL_PREFIX = 'glucosense_meal_sso_email'

/**
 * Stable RFC5322-style email for Meal Plan SSO when the portal profile has no email
 * (e.g. legacy session). Uses example.com (documentation namespace) so Pydantic EmailStr accepts it.
 */
export function getStableSyntheticSsoEmail(role, displayName) {
  try {
    const r = role === 'patient' ? 'patient' : 'clinician'
    const key = `${SYNTH_EMAIL_PREFIX}_${r}`
    const existing = localStorage.getItem(key)
    if (existing && existing.includes('@')) return existing
    const part = (displayName || r || 'user')
      .toString()
      .replace(/[^a-zA-Z0-9]/g, '')
      .slice(0, 14) || 'user'
    const id =
      (typeof crypto !== 'undefined' && crypto.randomUUID && crypto.randomUUID().slice(0, 10)) ||
      String(Date.now())
    const addr = `glucosense.${r}.${part}.${id}@example.com`.toLowerCase()
    localStorage.setItem(key, addr)
    return addr
  } catch {
    return 'glucosense.user@example.com'
  }
}

/**
 * Ask Meal Plan API for a JWT for this GlucoSense user (no second password).
 * Uses the FastAPI origin (not the Vite iframe origin) so the request hits the meal backend, not GlucoSense.
 */
export async function provisionMealPlanSession({ email, displayName, role }) {
  const apiBase = getMealPlanApiBaseUrl()
  const secret = getMealPlanEmbedSecret()
  const res = await fetch(`${apiBase}/api/auth/integration/glucosense`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Glucosense-Embed-Key': secret,
    },
    body: JSON.stringify({
      email: email.trim().toLowerCase(),
      display_name: displayName || undefined,
      role: role === 'clinician' ? 'clinician' : 'patient',
    }),
  })
  const text = await res.text()
  let data = {}
  try {
    data = text ? JSON.parse(text) : {}
  } catch {
    /* ignore */
  }
  if (!res.ok) {
    const msg = data?.detail || text?.slice(0, 200) || res.statusText
    throw new Error(typeof msg === 'string' ? msg : 'Meal Plan SSO failed')
  }
  if (!data?.token) {
    throw new Error('Meal Plan SSO: no token in response')
  }
  return data.token
}

export function postMealPlanTokenToIframe(iframeWindow, token, targetOrigin) {
  if (!iframeWindow || token == null) return
  const target = targetOrigin || getMealPlanOrigin()
  iframeWindow.postMessage({ type: 'GLUCOSENSE_MEAL_PLAN_TOKEN', token }, target)
}

/** Iframe can mount its message listener slightly after load; repeat delivery briefly. */
export function postMealPlanTokenToIframeWithRetries(iframeWindow, token, targetOrigin) {
  if (!iframeWindow || token == null) return
  postMealPlanTokenToIframe(iframeWindow, token, targetOrigin)
  window.setTimeout(() => postMealPlanTokenToIframe(iframeWindow, token, targetOrigin), 450)
  window.setTimeout(() => postMealPlanTokenToIframe(iframeWindow, token, targetOrigin), 1200)
  window.setTimeout(() => postMealPlanTokenToIframe(iframeWindow, token, targetOrigin), 2800)
}

export function postMealPlanLogoutToIframe(iframeWindow, targetOrigin) {
  if (!iframeWindow) return
  const target = targetOrigin || getMealPlanOrigin()
  iframeWindow.postMessage({ type: 'GLUCOSENSE_MEAL_PLAN_LOGOUT' }, target)
}
