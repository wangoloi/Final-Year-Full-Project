/**
 * Patients API service.
 * CRUD for patients, patient records, and backups.
 */
import { apiFetch } from '../api'

const API = '/api'

/** FastAPI may return detail as a string, object, or validation array */
function formatApiDetail(payload) {
  const d = payload?.detail
  if (d == null) return null
  if (typeof d === 'string') return d
  if (Array.isArray(d)) {
    return d
      .map((x) => (x && typeof x === 'object' && 'msg' in x ? x.msg : String(x)))
      .filter(Boolean)
      .join('; ')
  }
  if (typeof d === 'object' && d.msg) return String(d.msg)
  return String(d)
}

export async function fetchPatients() {
  const res = await apiFetch(`${API}/patients`)
  if (!res.ok) return { patients: [], count: 0 }
  const data = await res.json()
  return { patients: data.patients || [], count: data.count || 0 }
}

export async function fetchRemovedPatients() {
  // removed_only=1 (integer) — same route as active list; avoids path collisions with /patients/{id}.
  const res = await apiFetch(`${API}/patients?removed_only=1`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    return {
      patients: [],
      count: 0,
      error: formatApiDetail(err) || `Could not load removed patients (${res.status})`,
    }
  }
  const data = await res.json()
  return { patients: data.patients || [], count: data.count || 0, error: null }
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

export async function seedDemoPatients(force = false) {
  const res = await apiFetch(`${API}/patients/seed-demo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ force }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    return { ok: false, error: err.detail || 'Failed to load demo data' }
  }
  const data = await res.json()
  return {
    ok: true,
    monitoring_seeded_for: data.monitoring_seeded_for,
    patient_ids: data.patient_ids,
    patients: data.patients || [],
  }
}

export async function ensurePatientDemoMonitoring(patientId) {
  const res = await apiFetch(`${API}/patients/${patientId}/ensure-demo-monitoring`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    return { ok: false, error: err.detail || 'Failed to ensure demo data', seeded: false }
  }
  const data = await res.json()
  return { ok: true, seeded: Boolean(data.seeded), reason: data.reason }
}

export async function restorePatient(id) {
  const pid = Number(id)
  if (!Number.isFinite(pid) || pid <= 0) {
    return { ok: false, error: 'Invalid patient id' }
  }
  const res = await apiFetch(`${API}/patients/${pid}/restore`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    return { ok: false, error: formatApiDetail(err) || 'Could not restore patient' }
  }
  const data = await res.json().catch(() => ({}))
  return { ok: true, warning: data.warning || null }
}

export async function deletePatient(id) {
  const res = await apiFetch(`${API}/patients/${id}`, { method: 'DELETE' })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    return { ok: false, error: err.detail || 'Failed to delete patient' }
  }
  return { ok: true }
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
