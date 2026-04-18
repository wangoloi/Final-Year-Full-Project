import { useEffect } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { getPublicSiteHostname, WORKSPACE_PATH } from './constants'
import ApiGate from './components/ApiGate'
import Layout from './components/Layout'
import LandingPage from './pages/LandingPage'
import LoginPage from './pages/LoginPage'
import MealPlanShell from './pages/MealPlanShell'
import Dashboard from './pages/Dashboard'
import GlucoseTrends from './pages/GlucoseTrends'
import InsulinManagement from './pages/InsulinManagement'
import Reports from './pages/Reports'
import Alerts from './pages/Alerts'
import ModelInfo from './pages/ModelInfo'
import Patients from './pages/Patients'
import MealPlanEmbedPage from './pages/MealPlanEmbedPage'
import AssessmentPage from './pages/AssessmentPage'

/** Root opens the Clinical-Insulin workspace directly (no Meal Plan login on this app). */
function HomeEntry() {
  return <Navigate to={WORKSPACE_PATH} replace />
}

export default function App() {
  const location = useLocation()
  useEffect(() => {
    try {
      const host = getPublicSiteHostname()
      const parts = (location.pathname || '/').split('/').filter(Boolean)
      const pageRaw = parts.length ? parts[parts.length - 1] : 'home'
      const page = pageRaw.replace(/-/g, ' ')
      const pageLabel = page.charAt(0).toUpperCase() + page.slice(1)
      document.title = `GlucoSense — ${host} — ${pageLabel}`
    } catch (_) {
      document.title = 'GlucoSense'
    }
  }, [location.pathname])

  return (
    <Routes>
      <Route path="/" element={<HomeEntry />} />
      <Route path="/welcome" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />

      <Route path="/meal-plan" element={<MealPlanShell />} />

      <Route
        path={WORKSPACE_PATH}
        element={(
          <ApiGate>
            <Layout />
          </ApiGate>
        )}
      >
        <Route index element={<Dashboard />} />
        <Route path="assessment" element={<AssessmentPage />} />
        <Route path="patients" element={<Patients />} />
        <Route path="glucose-trends" element={<GlucoseTrends />} />
        <Route path="insulin-management" element={<InsulinManagement />} />
        <Route path="reports" element={<Reports />} />
        <Route path="alerts" element={<Alerts />} />
        <Route path="model-info" element={<ModelInfo />} />
        <Route path="meal-plan" element={<MealPlanEmbedPage />} />
      </Route>

      <Route path="*" element={<Navigate to={WORKSPACE_PATH} replace />} />
    </Routes>
  )
}
