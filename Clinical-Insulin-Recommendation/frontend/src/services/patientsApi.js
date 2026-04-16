/**
 * Patients API service.
 * CRUD for patients, patient records, and backups.
 */
import { requestJson } from './http'

const API = '/api'

export async function fetchPatients() {
  const data = await requestJson(`${API}/patients`)
  return { patients: data.patients || [], count: data.count || 0 }
}

export async function fetchDeletedPatients() {
  const data = await requestJson(`${API}/patients/deleted`)
  return { patients: data.patients || [], count: data.count || 0 }
}

/** @deprecated use fetchDeletedPatients */
export async function fetchArchivedPatients() {
  return fetchDeletedPatients()
}

export async function fetchPatient(id) {
  return requestJson(`${API}/patients/${id}`)
}

export async function createPatient(payload) {
  try {
    const data = await requestJson(`${API}/patients`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return { ok: true, id: data.id }
  } catch (e) {
    return { ok: false, error: e?.message || 'Failed to create patient' }
  }
}

export async function updatePatient(id, payload) {
  try {
    await requestJson(`${API}/patients/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return { ok: true }
  } catch (e) {
    return { ok: false, error: e?.message || 'Failed to update patient' }
  }
}

/** Soft-delete: patient is removed from the active list; restore from Deleted below. */
export async function deletePatient(id) {
  try {
    await requestJson(`${API}/patients/${id}`, { method: 'DELETE' })
    return { ok: true }
  } catch (e) {
    return { ok: false, error: e?.message || 'Failed to delete patient' }
  }
}

/** @deprecated use deletePatient */
export async function archivePatient(id) {
  return deletePatient(id)
}

export async function restorePatient(id) {
  try {
    await requestJson(`${API}/patients/${id}/restore`, { method: 'POST' })
    return { ok: true }
  } catch (e) {
    return { ok: false, error: e?.message || 'Failed to restore patient' }
  }
}

/** Permanently remove patient and linked assessment data. */
export async function purgePatient(id) {
  try {
    await requestJson(`${API}/patients/${id}/permanent`, { method: 'DELETE' })
    return { ok: true }
  } catch (e) {
    return { ok: false, error: e?.message || 'Failed to permanently delete patient' }
  }
}

export async function fetchPatientRecords(patientId, limit = 100) {
  const data = await requestJson(`${API}/patients/${patientId}/records?limit=${limit}`)
  return { records: data.records || [], count: data.count || 0 }
}

export async function fetchPatientGlucoseReadings(patientId, hours = 72) {
  const data = await requestJson(`${API}/patients/${patientId}/glucose-readings?hours=${hours}`)
  return { readings: data.readings || [], count: data.count || 0 }
}

export async function fetchPatientDoseEvents(patientId, limit = 50) {
  const data = await requestJson(`${API}/patients/${patientId}/dose-events?limit=${limit}`)
  return { events: data.events || [], count: data.count || 0 }
}

export async function createBackup() {
  try {
    const data = await requestJson(`${API}/backup`, { method: 'POST' })
    return { ok: true, path: data?.path }
  } catch (e) {
    return { ok: false, error: e?.message || 'Backup failed' }
  }
}

export async function fetchBackups() {
  const data = await requestJson(`${API}/backups`)
  return { backups: data.backups || [], count: data.count || 0 }
}

export async function restoreBackup(filename) {
  try {
    await requestJson(`${API}/backups/restore`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename }),
    })
    return { ok: true }
  } catch (e) {
    return { ok: false, error: e?.message || 'Restore failed' }
  }
}
