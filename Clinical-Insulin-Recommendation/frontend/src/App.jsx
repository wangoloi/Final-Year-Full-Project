import { Routes, Route, Navigate } from 'react-router-dom'
import { useClinical } from './context/ClinicalContext'
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
import { WORKSPACE_PATH } from './constants'

function HomeEntry() {
  const { isSignedIn, userRole } = useClinical()
  if (!isSignedIn) return <LandingPage />
  if (userRole === 'patient') return <Navigate to="/meal-plan" replace />
  if (userRole === 'clinician') return <Navigate to={WORKSPACE_PATH} replace />
  return <Navigate to="/login" replace />
}

function RequireSignedIn({ children }) {
  const { isSignedIn } = useClinical()
  if (!isSignedIn) return <Navigate to="/login" replace state={{ from: 'protected' }} />
  return children
}

function RequireClinician({ children }) {
  const { userRole } = useClinical()
  if (userRole !== 'clinician') return <Navigate to="/meal-plan" replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomeEntry />} />
      <Route path="/login" element={<LoginPage />} />

      <Route
        path="/meal-plan"
        element={(
          <RequireSignedIn>
            <MealPlanShell />
          </RequireSignedIn>
        )}
      />

      <Route
        path={WORKSPACE_PATH}
        element={(
          <RequireSignedIn>
            <RequireClinician>
              <ApiGate>
                <Layout />
              </ApiGate>
            </RequireClinician>
          </RequireSignedIn>
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

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
