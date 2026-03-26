/**
 * Clinical API service.
 * Single responsibility: API calls for patient, notifications, alerts, records, settings.
 */
import { apiFetch } from '../api'

const API = '/api'

export async function fetchPatientContext() {
  const res = await apiFetch(`${API}/patient-context`)
  if (!res.ok) return null
  return res.json()
}

export async function fetchNotifications(limit = 20) {
  const res = await apiFetch(`${API}/notifications?limit=${limit}`)
  if (!res.ok) return []
  const data = await res.json()
  return data.notifications || []
}

export async function fetchRecords(limit = 100) {
  const res = await apiFetch(`${API}/records?limit=${limit}`)
  if (!res.ok) return { records: [], count: 0 }
  const data = await res.json()
  return data
}

export async function createNotification(text, type) {
  const res = await apiFetch(`${API}/notifications`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, type }),
  })
  return res.ok
}

export async function deleteNotificationsByType(type) {
  const res = await apiFetch(`${API}/notifications/by-type/${type}`, { method: 'DELETE' })
  return res.ok
}

export async function markNotificationsRead() {
  const res = await apiFetch(`${API}/notifications/read`, { method: 'PATCH' })
  return res.ok
}

export async function fetchAlerts(limit = 50, unresolvedOnly = true) {
  const res = await apiFetch(`${API}/alerts?limit=${limit}&unresolved_only=${unresolvedOnly}`)
  if (!res.ok) return []
  const data = await res.json()
  return data.alerts || []
}

export async function resolveAlert(id) {
  const res = await apiFetch(`${API}/alerts/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id }),
  })
  return res.ok
}

export async function resolveAllAlerts() {
  const res = await apiFetch(`${API}/alerts/resolve-all`, { method: 'POST' })
  if (!res.ok) return 0
  const data = await res.json()
  return data.resolved ?? 0
}