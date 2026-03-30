/**
 * Dashboard API service.
 * Single responsibility: API calls for recommendation, dose, feedback.
 */
import { apiFetch } from '../api'

const API = '/api'

export async function fetchRecommendation(body) {
  try {
    const res = await apiFetch(`${API}/recommend`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const data = await res.json().catch(() => ({}))
    return { ok: res.ok, data, status: res.status }
  } catch (err) {
    // ERR_CONNECTION_REFUSED / Failed to fetch when Vite or FastAPI is down
    const isNetwork =
      err instanceof TypeError &&
      (String(err.message || '').includes('fetch') || String(err.message || '').includes('Failed'))
    const detail = isNetwork
      ? 'Cannot reach the GlucoSense API. Start the backend on port 8000 and the Vite frontend (npm run start). If the dev server crashed, restart it.'
      : String(err?.message || err)
    return { ok: false, data: { detail }, status: 0 }
  }
}

export async function recordDose(payload) {
  const res = await apiFetch(`${API}/dose`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return res.ok
}

export async function submitFeedback(payload) {
  const res = await apiFetch(`${API}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const data = await res.json().catch(() => ({}))
  return { ok: res.ok, data }
}
