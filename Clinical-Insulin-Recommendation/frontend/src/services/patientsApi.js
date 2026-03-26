/**
 * Patients API service.
 * CRUD for patients, patient records, and backups.
 */
import { apiFetch } from '../api'

const API = '/api'

export async function fetchPatients() {
  const res = await apiFetch(`${API}/patients`)
  if (!res.ok) return { patients: [], count: 0 }
  const data = await res.json()
  return { patients: data.patients || [], count: data.count || 0 }
}

export async function fetchPatient(id) {
  const res = await apiFetch(`${API}/patients/${id}`)
  if (!res.ok) return null
  return res.json()
}

export async function createPatient(payload) {
  const res = await apiFetch(`${API}/patients`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    return { ok: false, error: err.detail || 'Failed to create patient' }
  }
  const data = await res.json()
  return { ok: true, id: data.id }
}

export async function updatePatient(id, payload) {
  const res = await apiFetch(`${API}/patients/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    return { ok: false, error: err.detail || 'Failed to update patient' }
  }
  return { ok: true }
}

export async function fetchPatientRecords(patientId, limit = 100) {
  const res = await apiFetch(`${API}/patients/${patientId}/records?limit=${limit}`)
  if (!res.ok) return { records: [], count: 0 }
  const data = await res.json()
  return { records: data.records || [], count: data.count || 0 }
}

export async function fetchPatientGlucoseReadings(patientId, hours = 72) {
  const res = await apiFetch(`${API}/patients/${patientId}/glucose-readings?hours=${hours}`)
  if (!res.ok) return { readings: [], count: 0 }
  const data = await res.json()
  return { readings: data.readings || [], count: data.count || 0 }
}

export async function fetchPatientDoseEvents(patientId, limit = 50) {
  const res = await apiFetch(`${API}/patients/${patientId}/dose-events?limit=${limit}`)
  if (!res.ok) return { events: [], count: 0 }
  const data = await res.json()
  return { events: data.events || [], count: data.count || 0 }
}

export async function createBackup() {
  const res = await apiFetch(`${API}/backup`, { method: 'POST' })
  if (!res.ok) return { ok: false, error: 'Backup failed' }
  const data = await res.json().catch(() => ({}))
  return { ok: true, path: data.path }
}

export async function fetchBackups() {
  const res = await apiFetch(`${API}/backups`)
  if (!res.ok) return { backups: [], count: 0 }
  const data = await res.json()
  return { backups: data.backups || [], count: data.count || 0 }
}

export async function restoreBackup(filename) {
  const res = await apiFetch(`${API}/backups/restore`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    return { ok: false, error: err.detail || 'Restore failed' }
  }
  return { ok: true }
}
