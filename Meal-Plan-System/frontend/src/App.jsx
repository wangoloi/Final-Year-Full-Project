import React from 'react';
import { Routes, Route, Navigate, useLocation, Link } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Layout from './components/layout/Layout';
import Landing from './pages/auth/Landing';
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';
import Onboarding from './pages/app/Onboarding';
import Dashboard from './pages/app/Dashboard';
import Chatbot from './pages/app/Chatbot';
import Glucose from './pages/app/Glucose';
import MealPlan from './pages/app/MealPlan';

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
    const qs = location.search || '';
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: '0.75rem', background: 'var(--gray-100)', padding: '1rem' }}>
        <div className="text-muted" style={{ fontSize: '1.05rem', textAlign: 'center' }}>
          <i className="fas fa-link" style={{ marginRight: '0.5rem' }} />
          Signing you in from GlucoSense…
        </div>
        <Link to={`/login${qs}`} style={{ fontSize: '0.92rem' }} replace>
          Sign in with Meal Plan account instead
        </Link>
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
          <Route path="search" element={<Navigate to="/app/meal-plan" replace />} />
          <Route path="chatbot" element={<Chatbot />} />
          <Route path="recommendations" element={<Navigate to="/app/meal-plan" replace />} />
          <Route path="meal-plan" element={<MealPlan />} />
          <Route path="glucose" element={<Glucose />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
