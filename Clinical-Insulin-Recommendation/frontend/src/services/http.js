import { apiFetch } from '../api'

async function safeJson(res) {
  try {
    return await res.json()
  } catch {
    return null
  }
}

export async function requestJson(url, options = {}) {
  const res = await apiFetch(url, options)
  const data = await safeJson(res)
  if (!res.ok) {
    const detail = data?.detail || data?.message || `Request failed (${res.status})`
    const err = new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
    err.status = res.status
    err.data = data
    throw err
  }
  return data
}

