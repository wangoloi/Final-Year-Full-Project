import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { ALERTS_FETCH_LIMIT } from '../constants'
import * as clinicalApi from '../services/clinicalApi'
import { fetchPatients } from '../services/patientsApi'
const PROFILE_STORAGE_KEY = 'glucosense_user_profile'
const SESSION_STORAGE_KEY = 'glucosense_session'

/** @typedef {'clinician' | 'patient'} UserRole */

function loadSession() {
  try {
    const raw = localStorage.getItem(SESSION_STORAGE_KEY)
    if (!raw) return { isSignedIn: false, userRole: null }
    const s = JSON.parse(raw)
    return {
      isSignedIn: Boolean(s.isSignedIn),
      userRole: s.userRole === 'patient' ? 'patient' : s.userRole === 'clinician' ? 'clinician' : null,
    }
  } catch {
    return { isSignedIn: false, userRole: null }
  }
}

function saveSession(isSignedIn, userRole) {
  try {
    if (!isSignedIn || !userRole) {
      localStorage.removeItem(SESSION_STORAGE_KEY)
      return
    }
    localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify({ isSignedIn: true, userRole }))
  } catch (_) {}
}
const REPORTS_DOWNLOADED_KEY = 'glucosense_reports_downloaded_dates'
const REPORTS_DOWNLOAD_TYPE = 'reports_download'

function getRecordDate(record) {
  if (!record?.created_at) return null
  const d = new Date(record.created_at)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function getDatesWithRecords(records) {
  const set = new Set()
  records.forEach((r) => { const d = getRecordDate(r); if (d) set.add(d) })
  return [...set].sort().reverse()
}

function getDownloadedDates() {
  try {
    const raw = localStorage.getItem(REPORTS_DOWNLOADED_KEY)
    if (!raw) return []
    const arr = JSON.parse(raw)
    return Array.isArray(arr) ? arr : []
  } catch { return [] }
}

function formatDateLabel(dateStr) {
  const d = new Date(dateStr + 'T12:00:00')
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)
  if (d.toDateString() === today.toDateString()) return 'Today'
  if (d.toDateString() === yesterday.toDateString()) return 'Yesterday'
  return d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })
}
const ClinicalContext = createContext(null)

function loadProfile() {
  try {
    const raw = localStorage.getItem(PROFILE_STORAGE_KEY)
    if (raw) {
      const p = JSON.parse(raw)
      return { displayName: p.displayName ?? '', role: p.role ?? '', email: p.email ?? '' }
    }
  } catch (_) {}
  return { displayName: '', role: '', email: '' }
}

export function ClinicalProvider({ children }) {
  const session = loadSession()
  const [theme, setTheme] = useState('light')
  const [isSignedIn, setSignedInState] = useState(session.isSignedIn)
  const [userRole, setUserRoleState] = useState(session.userRole)
  const [userProfile, setUserProfileState] = useState(loadProfile)
  const [patient, setPatientState] = useState({
    name: 'Current Patient',
    condition: 'Type 1 Diabetes',
    photoPlaceholder: true,
  })
  const [patients, setPatients] = useState([])
  const [selectedPatientId, setSelectedPatientId] = useState(null)
  const [recentMetrics, setRecentMetrics] = useState({
    glucose: null,
    glucoseUnit: 'mg/dL',
    carbohydrates: null,
    activityMinutes: null,
    timestamp: null,
  })
  const [notifications, setNotifications] = useState([])
  const [alertsPreview, setAlertsPreview] = useState(0)

  const fetchPatientContext = useCallback(async () => {
    try {
      const data = await clinicalApi.fetchPatientContext()
      if (!data) return
      setPatientState((p) => ({
        ...p,
        name:
          data.name != null && data.name !== ''
            ? String(data.name)
            : p.name,
        condition: data.condition != null && data.condition !== '' ? String(data.condition) : p.condition,
      }))
      setRecentMetrics((prev) => ({
        ...prev,
        glucose: data.glucose ?? prev.glucose,
        carbohydrates: data.carbohydrates ?? prev.carbohydrates,
        activityMinutes: data.activity_minutes ?? prev.activityMinutes,
        timestamp: data.updated_at || prev.timestamp,
      }))
    } catch (_) {}
  }, [])

  const fetchNotifications = useCallback(async () => {
    try {
      const items = await clinicalApi.fetchNotifications()
      setNotifications(items)
    } catch (_) {}
  }, [])

  const syncReportsDownloadNotification = useCallback(async () => {
    try {
      const { records } = await clinicalApi.fetchRecords(100)
      const datesWithRecords = getDatesWithRecords(records)
      const downloadedDates = getDownloadedDates()
      const undownloadedDates = datesWithRecords.filter((d) => !downloadedDates.includes(d))
      if (undownloadedDates.length > 0) {
        const label = undownloadedDates.length === 1
          ? formatDateLabel(undownloadedDates[0])
          : `${undownloadedDates.length} days`
        await clinicalApi.createNotification(
          `Reports from ${label} ready to download. Go to Reports to download before the next session.`,
          REPORTS_DOWNLOAD_TYPE
        )
      } else {
        await clinicalApi.deleteNotificationsByType(REPORTS_DOWNLOAD_TYPE)
      }
    } catch (_) {}
  }, [])

  const fetchAlertsPreview = useCallback(async () => {
    try {
      const alerts = await clinicalApi.fetchAlerts(ALERTS_FETCH_LIMIT, true)
      setAlertsPreview(alerts.length)
    } catch (_) {}
  }, [])

  useEffect(() => {
    if (!isSignedIn || userRole !== 'clinician') return
    const load = async () => {
      await syncReportsDownloadNotification()
      await fetchNotifications()
      fetchPatientContext()
      fetchAlertsPreview()
    }
    load()
  }, [isSignedIn, userRole, fetchPatientContext, fetchNotifications, fetchAlertsPreview, syncReportsDownloadNotification])

  const updatePatient = useCallback((name, condition) => {
    setPatientState((p) => ({
      ...p,
      name: name != null && name !== '' ? String(name) : p.name,
      condition: condition != null && condition !== '' ? String(condition) : p.condition,
    }))
  }, [])

  const updateRecentMetrics = useCallback((metrics) => {
    setRecentMetrics((prev) => ({ ...prev, ...metrics, timestamp: metrics.timestamp || new Date().toISOString() }))
  }, [])

  const setUserProfile = useCallback((updates) => {
    setUserProfileState((prev) => {
      const next = { ...prev, ...updates }
      try {
        localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(next))
      } catch (_) {}
      return next
    })
  }, [])

  const setSignedIn = useCallback((value) => {
    setSignedInState(value)
    if (!value) {
      try {
        window.dispatchEvent(new CustomEvent('glucosense:sign-out'))
      } catch (_) {}
      setUserRoleState(null)
      saveSession(false, null)
    }
  }, [])

  const setUserRole = useCallback((role) => {
    setUserRoleState(role)
    if (role && isSignedIn) saveSession(true, role)
  }, [isSignedIn])

  const login = useCallback((role, profilePatch = {}) => {
    setUserRoleState(role)
    setSignedInState(true)
    saveSession(true, role)
    if (profilePatch && Object.keys(profilePatch).length) {
      setUserProfileState((prev) => {
        const next = { ...prev, ...profilePatch }
        try {
          localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(next))
        } catch (_) {}
        return next
      })
    }
  }, [])

  const clearNotificationBadge = useCallback(async () => {
    try {
      await clinicalApi.markNotificationsRead()
    } catch (_) {}
    setNotifications((n) => n.map((x) => ({ ...x, unread: false })))
  }, [])

  const refreshFromApi = useCallback(() => {
    fetchPatientContext()
    fetchNotifications()
    fetchAlertsPreview()
  }, [fetchPatientContext, fetchNotifications, fetchAlertsPreview])

  const refreshPatients = useCallback(async () => {
    try {
      const { patients: list } = await fetchPatients()
      setPatients(list)
    } catch (_) {}
  }, [])

  useEffect(() => {
    if (!isSignedIn || userRole !== 'clinician') return
    refreshPatients()
  }, [isSignedIn, userRole, refreshPatients])

  const value = {
    theme,
    setTheme,
    isSignedIn,
    setSignedIn,
    userRole,
    setUserRole,
    login,
    userProfile,
    setUserProfile,
    patient: { ...patient, photoPlaceholder: true },
    setPatient: updatePatient,
    patients,
    selectedPatientId,
    setSelectedPatientId,
    refreshPatients,
    recentMetrics,
    setRecentMetrics: updateRecentMetrics,
    notifications,
    setNotifications,
    clearNotificationBadge,
    alertsPreview,
    setAlertsPreview: setAlertsPreview,
    refreshFromApi,
  }

  return (
    <ClinicalContext.Provider value={value}>
      {children}
    </ClinicalContext.Provider>
  )
}

export function useClinical() {
  const ctx = useContext(ClinicalContext)
  if (!ctx) throw new Error('useClinical must be used within ClinicalProvider')
  return ctx
}
