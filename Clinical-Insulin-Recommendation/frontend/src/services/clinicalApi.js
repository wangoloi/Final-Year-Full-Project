/**
 * Clinical API service.
 * Single responsibility: API calls for patient, notifications, alerts, records, settings.
 */
import { requestJson } from './http'

const API = '/api'

export async function fetchPatientContext() {
  return requestJson(`${API}/patient-context`)
}

export async function fetchNotifications(limit = 20) {
  const data = await requestJson(`${API}/notifications?limit=${limit}`)
  return data.notifications || []
}

export async function fetchRecords(limit = 100) {
  return requestJson(`${API}/records?limit=${limit}`)
}

export async function createNotification(text, type) {
  await requestJson(`${API}/notifications`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, type }),
  })
  return true
}

export async function deleteNotificationsByType(type) {
  await requestJson(`${API}/notifications/by-type/${type}`, { method: 'DELETE' })
  return true
}

export async function markNotificationsRead() {
  await requestJson(`${API}/notifications/read`, { method: 'PATCH' })
  return true
}

export async function fetchAlerts(limit = 50, unresolvedOnly = true) {
  const data = await requestJson(`${API}/alerts?limit=${limit}&unresolved_only=${unresolvedOnly}`)
  return data.alerts || []
}

export async function resolveAlert(id) {
  await requestJson(`${API}/alerts/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id }),
  })
  return true
}

export async function resolveAllAlerts() {
  const data = await requestJson(`${API}/alerts/resolve-all`, { method: 'POST' })
  return data.resolved ?? 0
}

export async function getSettings() {
  return requestJson(`${API}/settings`)
}

export async function putSettings(payload) {
  return requestJson(`${API}/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function deleteRecord(id) {
  return requestJson(`${API}/records/${id}`, { method: 'DELETE' })
}