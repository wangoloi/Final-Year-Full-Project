import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../lib/api';

export default function Dashboard() {
  const { user } = useAuth();
  const [guidance, setGuidance] = useState(null);
  const [readings, setReadings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.recommendations(6), api.glucose.list()])
      .then(([recRes, gluRes]) => {
        setGuidance(recRes.guidance || null);
        setReadings((gluRes.readings || []).slice(0, 5));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const displayName = user?.first_name || user?.username || 'User';

  return (
    <div className="page-content mx-auto flex w-full max-w-6xl flex-col gap-8">
      {/* Hero */}
      <header className="page-header overflow-hidden">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-4">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-white/15 text-2xl text-white shadow-inner">
              <i className="fas fa-tachometer-alt" aria-hidden />
            </div>
            <div>
              <h1 className="!mb-1 text-2xl font-bold tracking-tight text-white sm:text-3xl">Dashboard</h1>
              <p className="m-0 text-base font-normal text-white">Welcome back, {displayName}!</p>
            </div>
          </div>
        </div>
      </header>

      {/* Quick actions */}
      <section aria-labelledby="dash-quick-actions">
        <h2 id="dash-quick-actions" className="sr-only">
          Quick actions
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Link
            to="/app/meal-plan"
            className="group flex flex-col rounded-xl border border-gray-200/80 bg-white p-6 shadow-card transition-all duration-200 hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-card-lg"
          >
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50 text-blue-600 transition-colors group-hover:bg-blue-100">
              <i className="fas fa-apple-whole text-2xl" aria-hidden />
            </div>
            <h3 className="mb-2 text-lg font-semibold text-gray-900">Search &amp; plan</h3>
            <p className="mb-0 text-sm font-normal leading-relaxed text-gray-700">
              Search foods and build your glucose-aware meal plan
            </p>
          </Link>
          <Link
            to="/app/meal-plan#meal-plan-glucose-log"
            className="group flex flex-col rounded-xl border border-gray-200/80 bg-white p-6 shadow-card transition-all duration-200 hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-card-lg"
          >
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50 text-blue-600 transition-colors group-hover:bg-blue-100">
              <i className="fas fa-heart-pulse text-2xl" aria-hidden />
            </div>
            <h3 className="mb-2 text-lg font-semibold text-gray-900">Log glucose</h3>
            <p className="mb-0 text-sm font-normal leading-relaxed text-gray-700">
              Enter a reading on Meal plan to personalize recommendations
            </p>
          </Link>
          <Link
            to="/app/meal-plan"
            className="group flex flex-col rounded-xl border border-gray-200/80 bg-white p-6 shadow-card transition-all duration-200 hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-card-lg"
          >
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50 text-blue-600 transition-colors group-hover:bg-blue-100">
              <i className="fas fa-utensils text-2xl" aria-hidden />
            </div>
            <h3 className="mb-2 text-lg font-semibold text-gray-900">Meals &amp; guidance</h3>
            <p className="mb-0 text-sm font-normal leading-relaxed text-gray-700">
              What to eat now, alternatives, and foods to ease off—based on your glucose
            </p>
          </Link>
        </div>
      </section>

      {user?.has_diabetes && (
        <section className="rounded-xl border border-gray-200/80 bg-white p-6 shadow-card" aria-labelledby="dash-glucose">
          <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <h2 id="dash-glucose" className="mb-0 flex items-center gap-2 text-xl font-semibold text-blue-600">
              <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
                <i className="fas fa-heart-pulse" aria-hidden />
              </span>
              Blood Glucose
            </h2>
            <Link to="/app/meal-plan#meal-plan-glucose-log" className="btn btn-secondary shrink-0 self-start sm:self-auto">
              Log reading
            </Link>
          </div>
          {loading ? (
            <p className="mb-0 rounded-lg bg-gray-50 py-8 text-center font-medium text-gray-800">Loading…</p>
          ) : readings.length === 0 ? (
            <p className="mb-0 rounded-lg border border-dashed border-gray-200 bg-gray-50 py-8 text-center text-gray-800">
              No readings yet. Start tracking!
            </p>
          ) : (
            <ul className="m-0 grid list-none grid-cols-1 gap-3 p-0 sm:grid-cols-2 lg:grid-cols-3">
              {readings.map((r) => (
                <li
                  key={r.id}
                  className="rounded-lg border border-gray-100 border-l-4 border-l-blue-600 bg-gray-50 p-4 shadow-sm"
                >
                  <div className="font-semibold text-gray-900">
                    {r.reading_value} mg/dL
                    <span className="ml-1 font-normal text-gray-700">— {r.reading_type}</span>
                  </div>
                  <time className="mt-1 block text-sm text-gray-700">
                    {new Date(r.reading_time).toLocaleString()}
                  </time>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <section className="rounded-xl border border-gray-200/80 bg-white p-6 shadow-card" aria-labelledby="dash-recs">
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h2 id="dash-recs" className="mb-0 flex items-center gap-2 text-xl font-semibold text-blue-600">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
              <i className="fas fa-utensils" aria-hidden />
            </span>
            What to eat next
          </h2>
          <Link to="/app/meal-plan" className="btn btn-secondary shrink-0 self-start sm:self-auto">
            Open meal plan
          </Link>
        </div>
        {loading ? (
          <p className="mb-0 rounded-lg bg-gray-50 py-8 text-center font-medium text-gray-800">Loading…</p>
        ) : !guidance?.next_action?.meal ? (
          <div className="rounded-lg border border-dashed border-gray-200 bg-gray-50 py-8 text-center">
            <p className="mb-0 text-gray-800">Log glucose on Meal plan to get a clear “eat this now” suggestion.</p>
          </div>
        ) : (
          <div className="rounded-lg border border-emerald-100 bg-emerald-50/40 p-5">
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-emerald-900">
              {guidance.next_action.priority_label || 'Suggested now'}
            </p>
            <h4 className="mb-2 text-lg font-semibold leading-snug text-gray-900">{guidance.next_action.meal}</h4>
            <p className="mb-3 text-sm leading-relaxed text-gray-800">{guidance.next_action.reason}</p>
            {guidance.alternatives?.length > 0 && (
              <div>
                <p className="mb-1 text-xs font-semibold text-gray-700">Also good</p>
                <ul className="m-0 list-disc space-y-1 pl-5 text-sm text-gray-800">
                  {guidance.alternatives.slice(0, 3).map((a) => (
                    <li key={a.meal}>{a.meal}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
