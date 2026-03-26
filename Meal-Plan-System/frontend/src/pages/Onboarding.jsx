import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../api';

/**
 * First-run web onboarding — completes via FastAPI POST /api/auth/onboarding/complete.
 */
export default function Onboarding() {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const displayName = user?.first_name || user?.username || 'there';

  async function handleContinue(e) {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await api.auth.completeOnboarding();
      await refreshUser();
      navigate('/app', { replace: true });
    } catch (err) {
      setError(err.message || 'Could not continue. Is the API running?');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page-noise relative flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-600 via-blue-700 to-blue-900 px-5 py-8 font-sans">
      <div className="relative flex w-full max-w-[520px] flex-col items-stretch">
        <Link
          to="/"
          className="mb-6 inline-flex items-center gap-2 text-[0.9375rem] text-white/90 no-underline transition-opacity hover:text-white hover:opacity-100"
        >
          <i className="fas fa-arrow-left" /> Home
        </Link>
        <div className="relative w-full rounded-[20px] bg-white p-10 shadow-[0_25px_50px_rgba(0,0,0,0.15)] max-sm:p-7">
          <div className="mb-8 text-center">
            <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-100 to-blue-300 text-[1.75rem] text-blue-700">
              <i className="fas fa-leaf" />
            </div>
            <h1 className="m-0 mb-1 font-outfit text-[1.75rem] font-bold text-slate-900">Welcome, {displayName}</h1>
            <p className="m-0 text-base text-slate-500">
              Glocusense helps you plan meals and track glucose with your care goals in mind.
            </p>
          </div>

          <ul className="m-0 mb-6 list-none p-0 text-left">
            <li className="flex items-start gap-3 border-b border-slate-200 py-3 text-[0.9375rem] text-slate-500 first:pt-0 last:border-b-0">
              <i className="fas fa-apple-whole mt-0.5 flex-shrink-0 text-blue-600" />
              <span>
                <strong>Search foods</strong> — diabetes-friendly options from our database.
              </span>
            </li>
            <li className="flex items-start gap-3 border-b border-slate-200 py-3 text-[0.9375rem] text-slate-500 last:border-b-0">
              <i className="fas fa-comments mt-0.5 flex-shrink-0 text-blue-600" />
              <span>
                <strong>Nutrition assistant</strong> — ask questions in plain language.
              </span>
            </li>
            <li className="flex items-start gap-3 py-3 text-[0.9375rem] text-slate-500 last:border-b-0">
              <i className="fas fa-heart-pulse mt-0.5 flex-shrink-0 text-blue-600" />
              <span>
                <strong>Glucose log</strong> — record readings and see them on your dashboard.
              </span>
            </li>
          </ul>

          {error && <div className="alert alert-error mb-5 rounded-[10px]">{error}</div>}

          <form onSubmit={handleContinue}>
            <button type="submit" className="btn btn-primary w-full rounded-[10px] px-6 py-3.5 text-base" disabled={submitting}>
              {submitting ? (
                <>
                  <i className="fas fa-spinner fa-spin" /> Saving…
                </>
              ) : (
                <>
                  Go to dashboard <i className="fas fa-arrow-right ml-1.5" />
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
