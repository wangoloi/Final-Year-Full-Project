/**
 * Dashboard API service.
 * Single responsibility: API calls for recommendation, dose, feedback.
 */
import { apiFetch } from '../api'

const API = '/api'

export async function fetchRecommendation(body) {
  const res = await apiFetch(`${API}/recommend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await res.json().catch(() => ({}))
  return { ok: res.ok, data, status: res.status }
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
