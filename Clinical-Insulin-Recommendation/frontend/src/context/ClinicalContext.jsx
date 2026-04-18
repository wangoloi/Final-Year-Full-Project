import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { ALERTS_FETCH_LIMIT } from '../constants'
import * as clinicalApi from '../services/clinicalApi'
import { fetchPatients } from '../services/patientsApi'
import {
  clearStoredMealToken,
  fetchMealPlanMe,
  getStoredMealToken,
  loginMealPlanApi,
  mapServerRoleToUiRole,
  setStoredMealToken,
} from '../auth/mealPlanAuth'

const PROFILE_STORAGE_KEY = 'glucosense_user_profile'
const REPORTS_DOWNLOADED_KEY = 'glucosense_reports_downloaded_dates'
const REPORTS_DOWNLOAD_TYPE = 'reports_download'

/** GlucoSense clinical UI is always clinician; Meal Plan account role is stored on profile (SSO). */
const GLUCOSENSE_UI_ROLE = 'clinician'

function getRecordDate(record) {
  if (!record?.created_at) return null
  const d = new Date(record.created_at)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function getDatesWithRecords(records) {
  const set = new Set()
  records.forEach((r) => {
    const dt = getRecordDate(r)
    if (dt) set.add(dt)
  })
  return [...set].sort().reverse()
}

function getDownloadedDates() {
  try {
    const raw = localStorage.getItem(REPORTS_DOWNLOADED_KEY)
    if (!raw) return []
    const arr = JSON.parse(raw)
    return Array.isArray(arr) ? arr : []
  } catch {
    return []
  }
}

function formatDateLabel(dateStr) {
  const d = new Date(`${dateStr}T12:00:00`)
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
      return {
        displayName: p.displayName ?? '',
        role: p.role ?? '',
        email: p.email ?? '',
        mealPlanRole: p.mealPlanRole ?? 'clinician',
      }
    }
  } catch (_) {}
  return { displayName: '', role: '', email: '', mealPlanRole: 'clinician' }
}

export function ClinicalProvider({ children }) {
  const [theme, setTheme] = useState('light')
  const [authReady, setAuthReady] = useState(true)
  const [isSignedIn, setSignedInState] = useState(true)
  const [userRole, setUserRoleState] = useState(GLUCOSENSE_UI_ROLE)
  const [userProfile, setUserProfileState] = useState(() => {
    const p = loadProfile()
    if (!p.displayName) {
      return { ...p, displayName: 'Guest', role: GLUCOSENSE_UI_ROLE }
    }
    return { ...p, role: GLUCOSENSE_UI_ROLE }
  })
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

  /**
   * Optional: enrich profile from Meal Plan JWT if present (login is only required on Meal Plan itself).
   * GlucoSense opens the clinical workspace without Meal Plan credentials.
   */
  useEffect(() => {
    let cancelled = false
    const token = getStoredMealToken()
    if (!token) {
      return () => {
        cancelled = true
      }
    }
    fetchMealPlanMe(token)
      .then((data) => {
        if (cancelled || !data?.user) {
          clearStoredMealToken()
          return
        }
        const mp = mapServerRoleToUiRole(data.user.role)
        setUserProfileState((prev) => ({
          ...prev,
          email: data.user.email || prev.email,
          displayName: data.user.first_name || data.user.username || prev.displayName,
          mealPlanRole: mp,
          role: GLUCOSENSE_UI_ROLE,
        }))
      })
      .catch(() => {
        clearStoredMealToken()
      })
    return () => {
      cancelled = true
    }
  }, [])

  const fetchPatientContext = useCallback(async () => {
    try {
      const data = await clinicalApi.fetchPatientContext()
      if (!data) return
      setPatientState((p) => ({
        ...p,
        name: data.name != null && data.name !== '' ? String(data.name) : p.name,
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
        const label =
          undownloadedDates.length === 1
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

  const updatePatient = useCallback((nameOrPatch, condition) => {
    setPatientState((p) => {
      let nextName = p.name
      let nextCondition = p.condition
      if (nameOrPatch != null && typeof nameOrPatch === 'object' && !Array.isArray(nameOrPatch)) {
        const { name: n, condition: c } = nameOrPatch
        if (n != null && n !== '') nextName = String(n)
        if (c != null && c !== '') nextCondition = String(c)
      } else {
        if (nameOrPatch != null && nameOrPatch !== '') nextName = String(nameOrPatch)
        if (condition != null && condition !== '') nextCondition = String(condition)
      }
      return { ...p, name: nextName, condition: nextCondition }
    })
  }, [])

  const updateRecentMetrics = useCallback((metrics) => {
    setRecentMetrics((prev) => ({ ...prev, ...metrics, timestamp: metrics.timestamp || new Date().toISOString() }))
  }, [])

  const setUserProfile = useCallback((updates) => {
    setUserProfileState((prev) => {
      const next = { ...prev, ...updates, role: GLUCOSENSE_UI_ROLE }
      try {
        localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(next))
      } catch (_) {}
      return next
    })
  }, [])

  /**
   * false = disconnect optional Meal Plan link only; GlucoSense stays open (no portal login required).
   */
  const setSignedIn = useCallback((value) => {
    if (!value) {
      try {
        window.dispatchEvent(new CustomEvent('glucosense:sign-out'))
      } catch (_) {}
      clearStoredMealToken()
      setUserRoleState(GLUCOSENSE_UI_ROLE)
      setUserProfileState((prev) => ({
        ...prev,
        email: '',
        mealPlanRole: 'clinician',
        displayName: prev.displayName?.replace?.(/\s*\(Meal Plan\)\s*$/, '') || 'Guest',
        role: GLUCOSENSE_UI_ROLE,
      }))
      setSignedInState(true)
      return
    }
    setSignedInState(true)
  }, [])

  /** Optional: link a Meal Plan account for SSO into the nutrition iframe (Meal Plan still enforces its own login when opened standalone). */
  const loginWithMealPlan = useCallback(async (username, password) => {
    const data = await loginMealPlanApi(username, password)
    setStoredMealToken(data.token)
    const mpRole = mapServerRoleToUiRole(data.user.role)
    setUserRoleState(GLUCOSENSE_UI_ROLE)
    setSignedInState(true)
    const profile = {
      displayName: data.user.first_name || data.user.username || '',
      email: data.user.email || '',
      mealPlanRole: mpRole,
      role: GLUCOSENSE_UI_ROLE,
    }
    setUserProfileState(profile)
    try {
      localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile))
    } catch (_) {}
    return { user: data.user, role: mpRole }
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
    authReady,
    isSignedIn,
    setSignedIn,
    userRole,
    loginWithMealPlan,
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

  return <ClinicalContext.Provider value={value}>{children}</ClinicalContext.Provider>
}

export function useClinical() {
  const ctx = useContext(ClinicalContext)
  if (!ctx) throw new Error('useClinical must be used within ClinicalProvider')
  return ctx
}
