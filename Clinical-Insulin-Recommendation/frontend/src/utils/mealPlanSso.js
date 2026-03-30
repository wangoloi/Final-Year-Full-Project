import { getMealPlanApiBaseUrl, getMealPlanEmbedSecret } from '../constants'

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
 * Dev: same-origin `/api/auth/...` is proxied by Vite to the Meal API; prod: use `VITE_MEAL_PLAN_API_URL` if needed.
 */
export async function provisionMealPlanSession({ email, displayName, role }) {
  const apiBase = getMealPlanApiBaseUrl()
  const secret = getMealPlanEmbedSecret()
  const path = '/api/auth/integration/glucosense'
  const url = apiBase ? `${apiBase.replace(/\/$/, '')}${path}` : path
  let res
  try {
    res = await fetch(url, {
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
  } catch (e) {
    const hint =
      import.meta.env.DEV && e instanceof TypeError
        ? ' Start the Meal Plan API on port 8001 (e.g. scripts/start-integrated.ps1) or set MEAL_PLAN_API_PROXY if it runs elsewhere.'
        : ''
    throw new Error(`Meal Plan SSO: ${e?.message || 'network error'}.${hint}`)
  }
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
  const target = targetOrigin || '*'
  iframeWindow.postMessage({ type: 'GLUCOSENSE_MEAL_PLAN_TOKEN', token }, target)
}

/** Iframe can mount its message listener slightly after load; repeat delivery briefly. */
export function postMealPlanTokenToIframeWithRetries(iframeWindow, token, targetOrigin) {
  if (!iframeWindow || token == null) return
  const target = targetOrigin || '*'
  postMealPlanTokenToIframe(iframeWindow, token, target)
  window.setTimeout(() => postMealPlanTokenToIframe(iframeWindow, token, target), 450)
  window.setTimeout(() => postMealPlanTokenToIframe(iframeWindow, token, target), 1200)
  window.setTimeout(() => postMealPlanTokenToIframe(iframeWindow, token, target), 2800)
}

export function postMealPlanLogoutToIframe(iframeWindow, targetOrigin) {
  if (!iframeWindow) return
  const target = targetOrigin || '*'
  iframeWindow.postMessage({ type: 'GLUCOSENSE_MEAL_PLAN_LOGOUT' }, target)
}
