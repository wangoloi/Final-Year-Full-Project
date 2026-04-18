import React from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Layout from './components/Layout';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Register from './pages/Register';
import Onboarding from './pages/Onboarding';
import Dashboard from './pages/Dashboard';
import Search from './pages/Search';
import Chatbot from './pages/Chatbot';
import Recommendations from './pages/Recommendations';
import Glucose from './pages/Glucose';
import MealPlan from './pages/MealPlan';
import SmartSensor from './pages/SmartSensor';

function LoadingScreen() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--gray-100)' }}>
      <div className="text-muted" style={{ fontSize: '1.125rem' }}>
        <i className="fas fa-spinner fa-spin" style={{ marginRight: '0.5rem' }} /> Loading...
      </div>
    </div>
  );
}

/** Must be logged in. */
function RequireAuth({ children }) {
  const { user, loading, embedHandoffPending } = useAuth();
  const location = useLocation();
  if (loading) return <LoadingScreen />;
  if (!user && embedHandoffPending) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: '0.75rem', background: 'var(--gray-100)' }}>
        <div className="text-muted" style={{ fontSize: '1.05rem' }}>
          <i className="fas fa-link" style={{ marginRight: '0.5rem' }} />
          Signing you in from GlucoSense…
        </div>
      </div>
    );
  }
  if (!user) {
    const qs = location.search || '';
    return <Navigate to={`/login${qs}`} replace />;
  }
  return children;
}

/**
 * Main app shell: requires login and finished onboarding (FastAPI flag).
 * New accounts get onboarding_completed === false until POST /api/auth/onboarding/complete.
 */
function RequireOnboarded({ children }) {
  const { user } = useAuth();
  if (user?.onboarding_completed === false) {
    return <Navigate to="/app/onboarding" replace />;
  }
  return children;
}

/** Onboarding page: logged in only; if already onboarded, go to app. */
function OnboardingGate({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <LoadingScreen />;
  if (!user) {
    const qs = location.search || '';
    return <Navigate to={`/login${qs}`} replace state={{ from: location }} />;
  }
  if (user.onboarding_completed !== false) {
    return <Navigate to="/app" replace />;
  }
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          path="/app/onboarding"
          element={
            <OnboardingGate>
              <Onboarding />
            </OnboardingGate>
          }
        />
        <Route
          path="/app"
          element={(
            <RequireAuth>
              <RequireOnboarded>
                <Layout />
              </RequireOnboarded>
            </RequireAuth>
          )}
        >
          <Route index element={<Dashboard />} />
          <Route path="search" element={<Search />} />
          <Route path="chatbot" element={<Chatbot />} />
          <Route path="recommendations" element={<Recommendations />} />
          <Route path="meal-plan" element={<MealPlan />} />
          <Route path="glucose" element={<Glucose />} />
          <Route path="smart-sensor" element={<SmartSensor />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
