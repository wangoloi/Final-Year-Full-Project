import { useState, useRef, useEffect } from 'react'
import { NavLink, Navigate, Outlet, useNavigate } from 'react-router-dom'
import { FiBell, FiAlertTriangle, FiUser, FiChevronDown, FiActivity, FiGrid, FiTrendingUp, FiFileText, FiSliders, FiSun, FiMenu, FiCoffee, FiClipboard } from 'react-icons/fi'
import { useClinical } from '../context/ClinicalContext'
import { apiFetch } from '../api'
import { WORKSPACE_PATH } from '../constants'

const API = '/api'

function TopBar({ sidebarOpen, onToggleSidebar, onLogoTripleClick }) {
  const navigate = useNavigate()
  const { notifications, clearNotificationBadge, setTheme, setSignedIn, userProfile, setUserProfile } = useClinical()
  const [profileEdit, setProfileEdit] = useState({ displayName: '', role: '', email: '' })
  const [profileSaved, setProfileSaved] = useState(false)
  const [accountToast, setAccountToast] = useState('')
  const [showNotifications, setShowNotifications] = useState(false)
  const [showProfile, setShowProfile] = useState(false)
  const [showProfileModal, setShowProfileModal] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [settings, setSettings] = useState({ units: 'mg/dL', theme: 'light', notifications_enabled: true })
  const notifRef = useRef(null)
  const profileRef = useRef(null)

  const unreadCount = notifications.filter((n) => n.unread).length

  useEffect(() => {
    apiFetch(`${API}/settings`).then((r) => r.ok && r.json()).then((d) => {
      if (d) { setSettings(d); setTheme(d.theme || 'light') }
    }).catch(() => {})
  }, [setTheme])

  useEffect(() => {
    if (showSettings) apiFetch(`${API}/settings`).then((r) => r.ok && r.json()).then((d) => d && setSettings(d)).catch(() => {})
  }, [showSettings])

  useEffect(() => {
    setTheme(settings.theme || 'light')
  }, [settings.theme, setTheme])

  useEffect(() => {
    function handleClickOutside(e) {
      if (
        notifRef.current && !notifRef.current.contains(e.target) &&
        profileRef.current && !profileRef.current.contains(e.target)
      ) {
        setShowNotifications(false)
        setShowProfile(false)
      }
    }
    document.addEventListener('click', handleClickOutside)
    return () => document.removeEventListener('click', handleClickOutside)
  }, [])

  const saveSettings = (key, value) => {
    const next = { ...settings, [key]: value }
    setSettings(next)
    if (key === 'theme') setTheme(value || 'light')
    apiFetch(`${API}/settings`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(next) }).catch(() => {})
  }

  const goToDashboard = () => { setShowNotifications(false); navigate(WORKSPACE_PATH) }
  const goToAlerts = () => { setShowNotifications(false); navigate(`${WORKSPACE_PATH}/alerts`) }
  const goToReports = () => { setShowNotifications(false); navigate(`${WORKSPACE_PATH}/reports`) }
  const hasReportsDownloadNotif = notifications.some((n) => n.notification_type === 'reports_download')
  const handleProfile = () => {
    setShowProfile(false)
    setShowProfileModal(true)
    setProfileEdit({ displayName: userProfile.displayName ?? '', role: userProfile.role ?? '', email: userProfile.email ?? '' })
    setProfileSaved(false)
  }
  const handleSaveProfile = () => {
    setUserProfile({ displayName: profileEdit.displayName.trim(), role: profileEdit.role.trim(), email: profileEdit.email.trim() })
    setProfileSaved(true)
    setTimeout(() => setProfileSaved(false), 2000)
  }
  const handlePreferences = () => { setShowProfile(false); setShowSettings(true) }
  const handleSignOut = () => { setShowProfile(false); setSignedIn(false); navigate('/') }

  return (
    <header className="topbar">
      <div className="topbar-brand">
        <button
          type="button"
          className="topbar-nav-toggle"
          onClick={onToggleSidebar}
          aria-label={sidebarOpen ? 'Close navigation' : 'Open navigation'}
          title={sidebarOpen ? 'Close menu' : 'Open menu'}
        >
          <FiMenu size={22} />
        </button>
        <div
          className="topbar-logo topbar-logo-clickable"
          aria-hidden="true"
          onClick={onLogoTripleClick}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && onLogoTripleClick()}
          title="GlucoSense"
        >
          <FiActivity size={24} />
        </div>
        <div>
          <span className="topbar-title">GlucoSense</span>
          <span className="topbar-subtitle">Clinical CDS + Meal Plan</span>
        </div>
      </div>

      <div className="topbar-actions">
        <div className="topbar-dropdown" ref={notifRef}>
          <button
            type="button"
            className="topbar-icon-btn"
            title="Notifications"
            onClick={() => { setShowNotifications((v) => !v); setShowProfile(false); if (unreadCount) clearNotificationBadge(); }}
            aria-label="Notifications"
            aria-expanded={showNotifications}
          >
            <FiBell size={20} />
            {unreadCount > 0 && <span className="topbar-badge">{unreadCount}</span>}
          </button>
          {showNotifications && (
            <div className="topbar-dropdown-panel topbar-notifications">
              <div className="topbar-dropdown-header">Notifications</div>
              {notifications.length === 0 ? (
                <div className="topbar-dropdown-item topbar-dropdown-empty">No new notifications</div>
              ) : (
                notifications.map((n) => (
                  <div key={n.id} className={`topbar-dropdown-item ${n.unread ? 'unread' : ''}`}>
                    <p>{n.text}</p>
                    <span className="topbar-dropdown-meta">{n.time}</span>
                  </div>
                ))
              )}
              <div className="topbar-dropdown-footer">
                <span className="topbar-dropdown-footer-label">Quick links</span>
                <div className="topbar-dropdown-actions">
                  <button type="button" className="topbar-dropdown-link topbar-dropdown-link--reports" onClick={goToDashboard}>
                    <FiGrid size={16} /> Dashboard
                  </button>
                  {hasReportsDownloadNotif && (
                    <button type="button" className="topbar-dropdown-link topbar-dropdown-link--reports" onClick={goToReports}>
                      <FiFileText size={16} /> Reports
                    </button>
                  )}
                  <button type="button" className="topbar-dropdown-link topbar-dropdown-link--alerts" onClick={goToAlerts}>
                    <FiAlertTriangle size={16} /> Alerts
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="topbar-dropdown" ref={profileRef}>
          <button type="button" className="topbar-avatar-btn" title="Account" onClick={() => { setShowProfile((v) => !v); setShowNotifications(false); }} aria-label="Account menu" aria-expanded={showProfile}>
            <div className="topbar-avatar" aria-hidden="true"><FiUser size={18} /></div>
            <FiChevronDown size={14} className="topbar-avatar-chevron" />
          </button>
          {showProfile && (
            <div className="topbar-dropdown-panel topbar-profile-menu">
              <div className="topbar-dropdown-header">Account</div>
              <button type="button" className="topbar-dropdown-item" onClick={handleProfile}>Profile</button>
              <button type="button" className="topbar-dropdown-item" onClick={handlePreferences}>Preferences</button>
              <button type="button" className="topbar-dropdown-item" onClick={handleSignOut}>Sign out</button>
            </div>
          )}
        </div>
      </div>

      {showSettings && (
        <div className="settings-overlay settings-overlay-center" onClick={() => setShowSettings(false)} aria-hidden="true">
          <div className="settings-panel settings-panel-modal" onClick={(e) => e.stopPropagation()}>
            <div className="settings-panel-header">
              <h2 className="settings-panel-title">Settings</h2>
              <button type="button" className="settings-close" onClick={() => setShowSettings(false)} aria-label="Close">×</button>
            </div>
            <div className="settings-panel-body">
              <label className="settings-row settings-row-interactive">
                <span className="settings-row-label"><FiSliders size={18} className="settings-row-icon" /> Units</span>
                <span className="settings-row-status">Working</span>
                <select className="settings-select" value={settings.units || 'mg/dL'} onChange={(e) => saveSettings('units', e.target.value)}>
                  <option value="mg/dL">Glucose: mg/dL</option>
                  <option value="mmol/L">Glucose: mmol/L</option>
                </select>
              </label>
              <div className="settings-row settings-row-interactive">
                <span className="settings-row-label"><FiBell size={18} className="settings-row-icon" /> Notifications</span>
                <div className="settings-row-control">
                  <span className="settings-row-status">{settings.notifications_enabled !== false ? 'On' : 'Off'}</span>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={settings.notifications_enabled !== false}
                    aria-label="Notifications on or off"
                    className={`toggle-switch ${settings.notifications_enabled !== false ? 'toggle-switch-on' : ''}`}
                    onClick={() => saveSettings('notifications_enabled', settings.notifications_enabled === false)}
                  >
                    <span className="toggle-switch-knob" />
                  </button>
                </div>
              </div>
              <div className="settings-row settings-row-interactive">
                <span className="settings-row-label"><FiSun size={18} className="settings-row-icon" /> Theme</span>
                <div className="settings-row-control">
                  <span className="settings-row-status">{settings.theme === 'dark' ? 'Dark' : 'Light'}</span>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={settings.theme === 'dark'}
                    aria-label="Theme dark or light"
                    className={`toggle-switch ${settings.theme === 'dark' ? 'toggle-switch-on' : ''}`}
                    onClick={() => saveSettings('theme', settings.theme === 'dark' ? 'light' : 'dark')}
                  >
                    <span className="toggle-switch-knob" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {showProfileModal && (
        <div className="settings-overlay settings-overlay-center" onClick={() => setShowProfileModal(false)} aria-hidden="true">
          <div className="settings-panel settings-panel-modal profile-modal" onClick={(e) => e.stopPropagation()}>
            <div className="settings-panel-header">
              <h2 className="settings-panel-title">Profile</h2>
              <button type="button" className="settings-close" onClick={() => setShowProfileModal(false)} aria-label="Close">×</button>
            </div>
            <div className="settings-panel-body profile-modal-body">
              <div className="profile-avatar-large"><FiUser size={32} /></div>
              <div className="profile-form">
                <label className="profile-field">
                  <span className="profile-field-label">Display name</span>
                  <input
                    type="text"
                    className="profile-input"
                    value={profileEdit.displayName}
                    onChange={(e) => setProfileEdit((p) => ({ ...p, displayName: e.target.value }))}
                    placeholder="Enter name..."
                  />
                </label>
                <label className="profile-field">
                  <span className="profile-field-label">Role</span>
                  <input
                    type="text"
                    className="profile-input"
                    value={profileEdit.role}
                    onChange={(e) => setProfileEdit((p) => ({ ...p, role: e.target.value }))}
                    placeholder="Enter Role..."
                  />
                </label>
                <label className="profile-field">
                  <span className="profile-field-label">Email</span>
                  <input
                    type="email"
                    className="profile-input"
                    value={profileEdit.email}
                    onChange={(e) => setProfileEdit((p) => ({ ...p, email: e.target.value }))}
                    placeholder="Enter Email..."
                  />
                </label>
              </div>
              <div className="profile-actions">
                <button type="button" className="profile-save-btn" onClick={handleSaveProfile}>
                  {profileSaved ? 'Saved' : 'Save'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {accountToast && <div className="account-toast">{accountToast}</div>}
    </header>
  )
}

function Sidebar({ isOpen, onClose }) {
  const { patient } = useClinical()
  const patientName =
    patient?.name != null && patient.name !== '' ? String(patient.name) : 'Patient'

  const handleNavClick = (e) => {
    const link = e.target.closest('a')
    if (link) onClose()
  }

  return (
    <aside className={`sidebar sidebar-flip ${isOpen ? 'sidebar-flip--open' : ''}`} aria-hidden={!isOpen}>
      <div className="sidebar-header-row">
        <span className="sidebar-label">Navigation</span>
        <button type="button" className="sidebar-close-btn" onClick={onClose} aria-label="Close navigation">×</button>
      </div>
      <div className="sidebar-patient-card">
        <div className="sidebar-patient-photo">
          {patient.photoPlaceholder ? <span>{patientName.slice(0, 2).toUpperCase()}</span> : null}
        </div>
        <div className="sidebar-patient-name">{patientName}</div>
        <div className="sidebar-patient-condition">{patient.condition}</div>
      </div>

      <nav className="sidebar-nav" aria-label="Main" onClick={handleNavClick}>
        <NavLink to={WORKSPACE_PATH} end className="sidebar-nav-link"><FiGrid size={18} className="sidebar-nav-icon" /> Dashboard</NavLink>
        <NavLink to={`${WORKSPACE_PATH}/assessment`} className="sidebar-nav-link"><FiClipboard size={18} className="sidebar-nav-icon" /> Assessment</NavLink>
        <NavLink to={`${WORKSPACE_PATH}/patients`} className="sidebar-nav-link"><FiUser size={18} className="sidebar-nav-icon" /> Patients</NavLink>
        <NavLink to={`${WORKSPACE_PATH}/glucose-trends`} className="sidebar-nav-link"><FiTrendingUp size={18} className="sidebar-nav-icon" /> Glucose Trends</NavLink>
        <NavLink to={`${WORKSPACE_PATH}/insulin-management`} className="sidebar-nav-link"><FiActivity size={18} className="sidebar-nav-icon" /> Glucose & Dosage</NavLink>
        <NavLink to={`${WORKSPACE_PATH}/reports`} className="sidebar-nav-link"><FiFileText size={18} className="sidebar-nav-icon" /> Reports</NavLink>
        <NavLink to={`${WORKSPACE_PATH}/alerts`} className="sidebar-nav-link"><FiAlertTriangle size={18} className="sidebar-nav-icon" /> Alerts</NavLink>
        <NavLink to={`${WORKSPACE_PATH}/meal-plan`} className="sidebar-nav-link sidebar-nav-link--meal"><FiCoffee size={18} className="sidebar-nav-icon" /> Meal plan</NavLink>
      </nav>
    </aside>
  )
}

const TRIPLE_CLICK_THRESHOLD_MS = 500

export default function Layout() {
  const { theme, isSignedIn } = useClinical()
  const navigate = useNavigate()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const logoClickCount = useRef(0)
  const logoClickTimer = useRef(null)

  const handleLogoTripleClick = () => {
    logoClickCount.current += 1
    if (logoClickTimer.current) clearTimeout(logoClickTimer.current)
    logoClickTimer.current = setTimeout(() => {
      if (logoClickCount.current >= 3) {
        navigate(`${WORKSPACE_PATH}/model-info`)
      }
      logoClickCount.current = 0
      logoClickTimer.current = null
    }, TRIPLE_CLICK_THRESHOLD_MS)
  }

  if (!isSignedIn) {
    return <Navigate to="/login" replace state={{ from: 'workspace' }} />
  }

  return (
    <div className="app-shell">
      <TopBar
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen((v) => !v)}
        onLogoTripleClick={handleLogoTripleClick}
      />
      <div className={`app-body ${sidebarOpen ? 'app-body--sidebar-open' : ''}`} data-theme={theme || 'light'}>
        <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        {sidebarOpen && (
          <div className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} aria-hidden="true" />
        )}
        <main className="app-main" id="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
