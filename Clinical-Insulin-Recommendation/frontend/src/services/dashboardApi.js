/**
 * Dashboard API service.
 * Single responsibility: API calls for recommendation, dose, feedback.
 */
import { requestJson } from './http'

const API = '/api'

export async function fetchRecommendation(body) {
  try {
    const data = await requestJson(`${API}/recommend`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    return { ok: true, data, status: 200 }
  } catch (err) {
    return { ok: false, data: { detail: err?.message || 'Request failed' }, status: err?.status ?? 0 }
  }
}

export async function recordDose(payload) {
  try {
    await requestJson(`${API}/dose`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return true
  } catch {
    return false
  }
}

export async function submitFeedback(payload) {
  try {
    const data = await requestJson(`${API}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return { ok: true, data }
  } catch (e) {
    return { ok: false, data: { detail: e?.message || 'Failed to submit feedback' } }
  }
}
