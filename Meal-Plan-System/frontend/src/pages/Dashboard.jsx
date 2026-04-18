import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../api';

export default function Dashboard() {
  const { user } = useAuth();
  const [recommendations, setRecommendations] = useState([]);
  const [readings, setReadings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.recommendations(6), api.glucose.list()])
      .then(([recRes, gluRes]) => {
        setRecommendations(recRes.recommendations || []);
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
              <p className="m-0 text-base text-white/95">Welcome back, {displayName}!</p>
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
            to="/app/search"
            className="group flex flex-col rounded-xl border border-gray-200/80 bg-white p-6 shadow-card transition-all duration-200 hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-card-lg"
          >
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50 text-blue-600 transition-colors group-hover:bg-blue-100">
              <i className="fas fa-apple-whole text-2xl" aria-hidden />
            </div>
            <h3 className="mb-2 text-lg font-semibold text-gray-900">Search Foods</h3>
            <p className="mb-0 text-sm leading-relaxed text-gray-600">
              Find diabetes-friendly local and healthy foods
            </p>
          </Link>
          <Link
            to="/app/glucose"
            className="group flex flex-col rounded-xl border border-gray-200/80 bg-white p-6 shadow-card transition-all duration-200 hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-card-lg"
          >
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50 text-blue-600 transition-colors group-hover:bg-blue-100">
              <i className="fas fa-heart-pulse text-2xl" aria-hidden />
            </div>
            <h3 className="mb-2 text-lg font-semibold text-gray-900">Record Glucose</h3>
            <p className="mb-0 text-sm leading-relaxed text-gray-600">Track blood sugar readings</p>
          </Link>
          <Link
            to="/app/meal-plan"
            className="group flex flex-col rounded-xl border border-gray-200/80 bg-white p-6 shadow-card transition-all duration-200 hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-card-lg"
          >
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50 text-blue-600 transition-colors group-hover:bg-blue-100">
              <i className="fas fa-calendar-week text-2xl" aria-hidden />
            </div>
            <h3 className="mb-2 text-lg font-semibold text-gray-900">Meal plan</h3>
            <p className="mb-0 text-sm leading-relaxed text-gray-600">
              See your week laid out with breakfast, lunch, dinner &amp; snacks
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
            <Link to="/app/glucose" className="btn btn-secondary shrink-0 self-start sm:self-auto">
              Record
            </Link>
          </div>
          {loading ? (
            <p className="mb-0 rounded-lg bg-gray-50 py-8 text-center text-gray-600">Loading…</p>
          ) : readings.length === 0 ? (
            <p className="mb-0 rounded-lg border border-dashed border-gray-200 bg-gray-50 py-8 text-center text-gray-600">
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
                    <span className="ml-1 font-normal text-gray-600">— {r.reading_type}</span>
                  </div>
                  <time className="mt-1 block text-sm text-gray-500">
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
              <i className="fas fa-seedling" aria-hidden />
            </span>
            Recommendations
          </h2>
          <Link to="/app/recommendations" className="btn btn-secondary shrink-0 self-start sm:self-auto">
            View all
          </Link>
        </div>
        {loading ? (
          <p className="mb-0 rounded-lg bg-gray-50 py-8 text-center text-gray-600">Loading…</p>
        ) : recommendations.length === 0 ? (
          <div className="rounded-lg border border-dashed border-gray-200 bg-gray-50 py-8 text-center">
            <p className="mb-0 text-gray-600">Complete your profile for personalized suggestions.</p>
          </div>
        ) : (
          <ul className="m-0 grid list-none grid-cols-1 gap-4 p-0 sm:grid-cols-2 lg:grid-cols-4">
            {recommendations.slice(0, 4).map((rec) => (
              <li
                key={rec.id}
                className="flex min-h-[7.5rem] flex-col rounded-lg border border-gray-100 bg-gray-50 p-4 shadow-sm transition-shadow hover:shadow-md"
              >
                <h4 className="mb-2 line-clamp-2 text-base font-semibold leading-snug text-gray-900">{rec.name}</h4>
                <p className="mt-auto mb-0 text-sm leading-relaxed text-gray-600">
                  {rec.calories} cal · GI {rec.glycemic_index ?? 'N/A'}
                  <span className="mt-1 block truncate text-gray-500" title={rec.category}>
                    {rec.category}
                  </span>
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
