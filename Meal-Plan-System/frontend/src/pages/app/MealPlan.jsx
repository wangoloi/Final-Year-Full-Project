import React, { useMemo, useState, useEffect, useCallback, useRef } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { api } from '../../lib/api';

function trendFromReadings(readings) {
  if (!readings?.length || readings.length < 2) {
    return { label: 'Not enough data', icon: 'fa-minus', iconClass: 'text-slate-500' };
  }
  const newest = readings[0].reading_value;
  const oldest = readings[readings.length - 1].reading_value;
  if (newest > oldest + 8) {
    return { label: 'Rising vs earlier', icon: 'fa-arrow-trend-up', iconClass: 'text-amber-600' };
  }
  if (newest < oldest - 8) {
    return { label: 'Falling vs earlier', icon: 'fa-arrow-trend-down', iconClass: 'text-emerald-600' };
  }
  return { label: 'Relatively flat', icon: 'fa-arrow-right', iconClass: 'text-blue-600' };
}

function glucoseStateLabel(state) {
  if (!state) return '';
  const map = {
    critical_high: 'Very high',
    rising_high: 'High or rising',
    elevated: 'Elevated',
    falling_low: 'On the low side',
    stable_controlled: 'Steady',
    improving: 'Improving',
    unknown_no_data: 'Not enough data yet',
  };
  return map[state] || String(state).replace(/_/g, ' ');
}

function tierBadgeClass(tier) {
  switch (tier) {
    case 'below_range':
      return 'bg-amber-100 text-amber-900 ring-amber-200';
    case 'in_range':
      return 'bg-emerald-100 text-emerald-900 ring-emerald-200';
    case 'above_range':
      return 'bg-orange-100 text-orange-900 ring-orange-200';
    case 'high':
      return 'bg-red-100 text-red-900 ring-red-200';
    default:
      return 'bg-slate-100 text-slate-800 ring-slate-200';
  }
}

function tierLabel(tier) {
  const labels = {
    below_range: 'Below range',
    in_range: 'In range',
    above_range: 'Above range',
    high: 'High',
    unknown: 'No readings',
  };
  return labels[tier] || tier;
}

const MEAL_TIPS = [
  {
    id: 'balance',
    icon: 'fa-scale-balanced',
    title: 'Balance each meal',
    body:
      'Fill most of your plate with vegetables and protein. Add a smaller scoop of rice, posho, or bread. That mix helps your blood sugar rise more slowly after eating.',
    hint: 'Half plate veg, a piece of protein about the size of your palm, and a small starch.',
  },
  {
    id: 'portions',
    icon: 'fa-ruler-combined',
    title: 'Watch portions',
    body:
      'More food on the plate often means a bigger rise in blood sugar. A little less of the heavy carbs (rice, bread, posho) can help. You can still eat the foods you enjoy—just try smaller amounts.',
    hint: 'Try a smaller plate, or measure once so you know what one serving looks like.',
  },
  {
    id: 'feedback',
    icon: 'fa-droplet',
    title: 'Drink water & say what works',
    body:
      'Sip water during the day. When you see meal ideas above, tap “I can eat this” or “Not suitable.” That lets the app suggest meals that fit you better next time.',
    hint: 'Keep a bottle of water nearby. Use the buttons on the meal ideas above so the next ideas fit you better.',
  },
];

export default function MealPlan() {
  const location = useLocation();
  const searchAnchorRef = useRef(null);
  const [guidance, setGuidance] = useState(null);
  const [glucoseContext, setGlucoseContext] = useState(null);
  const [readings, setReadings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [feedbackBusy, setFeedbackBusy] = useState({});

  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState('');
  const [searchNotFound, setSearchNotFound] = useState(false);

  const [glucoseForm, setGlucoseForm] = useState({ reading_value: '', reading_type: 'fasting', notes: '' });
  const [glucoseSaving, setGlucoseSaving] = useState(false);
  const [glucoseFormError, setGlucoseFormError] = useState('');
  const [glucoseFormSuccess, setGlucoseFormSuccess] = useState('');
  const [activeTipIndex, setActiveTipIndex] = useState(0);

  const applyRecPayload = useCallback((data) => {
    setGuidance(data.guidance || null);
    setGlucoseContext(data.glucose_context || null);
  }, []);

  const loadRecommendations = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [data, gluRes] = await Promise.all([api.recommendations(28), api.glucose.list()]);
      applyRecPayload(data);
      setReadings(gluRes.readings || []);
    } catch (err) {
      setError(err.message || 'Failed to load meal ideas');
    } finally {
      setLoading(false);
    }
  }, [applyRecPayload]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setError('');
      setLoading(true);
      try {
        const [recRes, gluRes] = await Promise.all([api.recommendations(28), api.glucose.list()]);
        if (cancelled) return;
        applyRecPayload(recRes);
        setReadings(gluRes.readings || []);
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load meal plan');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [applyRecPayload]);

  useEffect(() => {
    if (!glucoseFormSuccess) return undefined;
    const t = setTimeout(() => setGlucoseFormSuccess(''), 6000);
    return () => clearTimeout(t);
  }, [glucoseFormSuccess]);

  useEffect(() => {
    if (location.hash !== '#meal-plan-glucose-log') return;
    const el = document.getElementById('meal-plan-glucose-log');
    if (el) {
      requestAnimationFrame(() => el.scrollIntoView({ behavior: 'smooth', block: 'start' }));
    }
  }, [location.hash]);

  const trend = useMemo(() => trendFromReadings(readings), [readings]);

  async function handleSearch(e) {
    e?.preventDefault();
    if (!query.trim()) return;
    setSearchLoading(true);
    setSearchError('');
    setSearchNotFound(false);
    setSearchResults([]);
    try {
      const data = await api.search(query.trim(), 20);
      setSearchResults(data.results || []);
      setSearchNotFound(data.not_found || false);
    } catch (err) {
      setSearchError(err.message || 'Search failed');
    } finally {
      setSearchLoading(false);
    }
  }

  function scrollToSearch() {
    searchAnchorRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  async function handleGlucoseSubmit(e) {
    e.preventDefault();
    setGlucoseFormError('');
    setGlucoseFormSuccess('');
    const v = parseFloat(glucoseForm.reading_value);
    if (!glucoseForm.reading_value || Number.isNaN(v)) {
      setGlucoseFormError('Enter a valid glucose value (mg/dL).');
      return;
    }
    setGlucoseSaving(true);
    try {
      await api.glucose.add(v, glucoseForm.reading_type, glucoseForm.notes?.trim() || null);
      setGlucoseForm({ reading_value: '', reading_type: glucoseForm.reading_type, notes: '' });
      setGlucoseFormSuccess('Reading saved. Updating what to eat next for your new data…');
      const [data, gluRes] = await Promise.all([api.recommendations(28), api.glucose.list()]);
      applyRecPayload(data);
      setReadings(gluRes.readings || []);
      setGlucoseFormSuccess('Reading saved. “What you should eat now” below reflects your latest data.');
    } catch (err) {
      setGlucoseFormError(err.message || 'Could not save reading');
    } finally {
      setGlucoseSaving(false);
    }
  }

  async function sendFeedback(foodId, action) {
    const idStr = String(foodId);
    setFeedbackBusy((b) => ({ ...b, [idStr]: true }));
    try {
      await api.recommendationFeedback(Number(foodId), action);
    } catch {
      /* optional toast */
    } finally {
      setFeedbackBusy((b) => ({ ...b, [idStr]: false }));
    }
  }

  const gc = glucoseContext;
  const tier = gc?.tier ?? 'unknown';
  const gs = gc?.glucose_state;
  const na = guidance?.next_action;

  return (
    <div className="page-content mx-auto w-full max-w-6xl gap-10 pb-2 sm:gap-12">
      <header className="page-header overflow-hidden rounded-2xl px-5 py-6 shadow-header-chat sm:px-8 sm:py-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between lg:gap-8">
          <div className="flex min-w-0 flex-1 items-start gap-4 sm:gap-5">
            <div
              className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-white/15 text-white shadow-inner sm:h-16 sm:w-16 sm:text-[1.75rem]"
              aria-hidden
            >
              <i className="fas fa-utensils" />
            </div>
            <div className="min-w-0 pt-0.5">
              <p className="mb-3 inline-flex items-center rounded-full bg-white/20 px-3.5 py-1.5 text-[0.6875rem] font-semibold uppercase tracking-[0.12em] text-white/95">
                Nutrition assistant · Glucose-aware
              </p>
              <h1 className="!mb-2 font-sans text-3xl font-bold tracking-tight text-white sm:text-4xl">
                Meals &amp; guidance
              </h1>
              <p className="m-0 max-w-xl text-sm font-normal leading-relaxed text-white sm:text-base">
                Log your blood glucose below—your “what to eat now” suggestions update automatically when you save a
                reading.
              </p>
            </div>
          </div>
          <div className="flex w-full flex-col gap-2 sm:flex-row sm:flex-wrap lg:w-auto lg:min-w-[11rem] lg:flex-col lg:gap-2.5">
            <button
              type="button"
              onClick={scrollToSearch}
              className="inline-flex cursor-pointer items-center justify-center gap-2 rounded-xl border-none bg-white px-5 py-3 text-sm font-semibold text-blue-700 shadow-sm transition-colors hover:bg-blue-50"
            >
              <i className="fas fa-search" aria-hidden />
              Search foods
            </button>
          </div>
        </div>
      </header>

      {error && (
        <div className="alert alert-error rounded-xl text-sm sm:text-[0.9375rem]">
          {error}
        </div>
      )}

      <section
        className="rounded-2xl border border-blue-200/80 bg-white p-5 shadow-sm sm:p-6"
        aria-labelledby="inline-glucose-heading"
        id="meal-plan-glucose-log"
      >
        <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 id="inline-glucose-heading" className="mb-1 text-lg font-semibold text-slate-900">
              <i className="fas fa-droplet mr-2 text-blue-600" aria-hidden />
              Log a glucose reading
            </h2>
            <p className="m-0 max-w-2xl text-sm text-slate-700">
              We use your saved readings to suggest what to eat next. Enter a value here—guidance updates automatically.
              You do not need to open the Glucose page.
            </p>
          </div>
        </div>
        {glucoseFormError && (
          <div className="alert alert-error mb-4 rounded-xl text-sm" role="alert">
            {glucoseFormError}
          </div>
        )}
        {glucoseFormSuccess && (
          <div className="alert alert-success mb-4 rounded-xl text-sm" role="status">
            {glucoseFormSuccess}
          </div>
        )}
        <form onSubmit={handleGlucoseSubmit} className="grid grid-cols-1 gap-4 sm:grid-cols-12 sm:items-end">
          <div className="sm:col-span-3">
            <label className="mb-1.5 block text-sm font-semibold text-slate-800" htmlFor="mp-glucose-value">
              Value (mg/dL)
            </label>
            <input
              id="mp-glucose-value"
              type="number"
              step="0.1"
              className="form-input w-full rounded-xl border border-slate-300"
              placeholder="e.g. 120"
              value={glucoseForm.reading_value}
              onChange={(e) => setGlucoseForm((f) => ({ ...f, reading_value: e.target.value }))}
              disabled={glucoseSaving}
              required
            />
          </div>
          <div className="sm:col-span-3">
            <label className="mb-1.5 block text-sm font-semibold text-slate-800" htmlFor="mp-glucose-type">
              When
            </label>
            <select
              id="mp-glucose-type"
              className="form-select w-full rounded-xl border border-slate-300"
              value={glucoseForm.reading_type}
              onChange={(e) => setGlucoseForm((f) => ({ ...f, reading_type: e.target.value }))}
              disabled={glucoseSaving}
            >
              <option value="fasting">Fasting</option>
              <option value="pre_meal">Pre-meal</option>
              <option value="post_meal">Post-meal</option>
              <option value="random">Random</option>
            </select>
          </div>
          <div className="sm:col-span-4">
            <label className="mb-1.5 block text-sm font-semibold text-slate-800" htmlFor="mp-glucose-notes">
              Notes (optional)
            </label>
            <input
              id="mp-glucose-notes"
              type="text"
              className="form-input w-full rounded-xl border border-slate-300"
              placeholder="e.g. Before lunch"
              maxLength={200}
              value={glucoseForm.notes}
              onChange={(e) => setGlucoseForm((f) => ({ ...f, notes: e.target.value }))}
              disabled={glucoseSaving}
            />
          </div>
          <div className="sm:col-span-2">
            <button
              type="submit"
              className="btn btn-primary w-full rounded-xl px-4 py-3 text-sm font-semibold"
              disabled={glucoseSaving}
            >
              {glucoseSaving ? (
                <>
                  <i className="fas fa-spinner fa-spin mr-1" aria-hidden />
                  Saving…
                </>
              ) : (
                <>
                  <i className="fas fa-heart-pulse mr-1" aria-hidden />
                  Save &amp; update meals
                </>
              )}
            </button>
          </div>
        </form>
        <p className="mb-0 mt-4 text-center text-xs text-slate-600 sm:text-left">
          <Link to="/app/glucose" className="font-medium text-blue-700 no-underline hover:underline">
            View full history &amp; all readings
          </Link>{' '}
          (optional)
        </p>
      </section>

      {!loading && gc && (
        <section
          className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm sm:p-6"
          aria-labelledby="glucose-insight-heading"
        >
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <h2 id="glucose-insight-heading" className="mb-0 text-lg font-semibold text-slate-900">
                  <i className="fas fa-heart-pulse mr-2 text-blue-600" aria-hidden />
                  Your glucose picture
                </h2>
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ${tierBadgeClass(tier)}`}
                >
                  {tierLabel(tier)}
                </span>
                {gs?.state && (
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-800">
                    {glucoseStateLabel(gs.state)}
                  </span>
                )}
              </div>
              {gs && (
                <div className="mb-4 flex flex-wrap items-center gap-4 text-sm">
                  <div className="flex items-center gap-2 text-slate-800">
                    <span className="font-semibold">Trend</span>
                    <i className={`fas ${trend.icon} ${trend.iconClass}`} aria-hidden />
                    <span>{trend.label}</span>
                  </div>
                </div>
              )}
              <p className="mb-0 text-sm leading-relaxed text-slate-700">{gc.rationale}</p>
              {gc.readings_used > 0 && (
                <p className="mb-0 mt-3 text-xs text-slate-700">
                  Latest {gc.latest_mg_dl != null ? `${gc.latest_mg_dl} mg/dL` : '—'}
                  {gc.avg_recent_mg_dl != null ? ` · Recent avg ${gc.avg_recent_mg_dl} mg/dL` : ''}
                  {gc.readings_used ? ` · ${gc.readings_used} reading(s)` : ''}
                </p>
              )}
            </div>
            <p className="mb-0 shrink-0 self-start text-right text-xs text-slate-600 sm:max-w-[10rem]">
              Readings logged above drive this panel.{' '}
              <Link to="/app/glucose" className="font-semibold text-blue-700 no-underline hover:underline">
                Full history
              </Link>
            </p>
          </div>
          {readings.length > 0 && (
            <ul className="mt-4 grid list-none grid-cols-1 gap-2 border-t border-slate-100 pt-4 sm:grid-cols-3">
              {readings.slice(0, 5).map((r) => (
                <li key={r.id} className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700">
                  <span className="font-semibold text-slate-900">{r.reading_value} mg/dL</span>
                  <span className="text-slate-700"> · {r.reading_type}</span>
                  <time className="mt-0.5 block text-xs text-slate-700">
                    {new Date(r.reading_time).toLocaleString()}
                  </time>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <section
        ref={searchAnchorRef}
        id="meal-plan-search"
        className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm sm:p-7"
        aria-labelledby="meal-plan-search-heading"
      >
        <h2 id="meal-plan-search-heading" className="mb-4 flex items-center gap-2 text-lg font-semibold text-blue-700">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
            <i className="fas fa-apple-whole" aria-hidden />
          </span>
          Search foods
        </h2>
        <p className="mb-4 text-sm text-slate-700">Look up foods in the catalog for ideas beyond today’s suggestions.</p>
        <form onSubmit={handleSearch} className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center">
          <input
            type="search"
            className="form-input min-w-0 flex-1 rounded-xl border border-slate-200 px-4 py-3 text-sm"
            style={{ minWidth: '200px' }}
            placeholder="e.g. matooke, low sugar fruit, beans…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button type="submit" className="btn btn-primary shrink-0 px-6 py-3 text-sm" disabled={searchLoading}>
            {searchLoading ? (
              <>
                <i className="fas fa-spinner fa-spin" /> Searching…
              </>
            ) : (
              <>
                <i className="fas fa-search" /> Search
              </>
            )}
          </button>
        </form>
        {searchError && <div className="alert alert-error mb-4 rounded-xl text-sm">{searchError}</div>}
        {searchNotFound && searchResults.length === 0 && (
          <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 py-8 text-center">
            <p className="mb-0 text-slate-700">No results—try a different term.</p>
          </div>
        )}
        {searchResults.length > 0 && (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {searchResults.map((f) => (
              <div
                key={f.id}
                className="rounded-xl border border-slate-100 bg-slate-50/90 p-4 transition hover:shadow-md"
              >
                <h4 className="mb-1 text-base font-semibold text-slate-900">
                  {f.name}
                  {f.local_name ? ` (${f.local_name})` : ''}
                </h4>
                <p className="mb-0 text-sm text-slate-700">
                  {f.calories} cal · GI {f.glycemic_index ?? '—'} · {f.category}
                  {f.diabetes_friendly && (
                    <span className="ml-2 inline-flex rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-900">
                      Diabetes-friendly
                    </span>
                  )}
                </p>
              </div>
            ))}
          </div>
        )}
      </section>

      <section
        className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm sm:p-7"
        aria-labelledby="meal-plan-recs"
        id="meal-plan-recommendations"
      >
        <h2 id="meal-plan-recs" className="mb-4 flex flex-wrap items-center gap-2 text-lg font-semibold text-blue-700">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
            <i className="fas fa-utensils" aria-hidden />
          </span>
          What you should eat now
        </h2>
        <p className="mb-6 max-w-prose text-sm leading-relaxed text-slate-700">
          Based on your logged readings above: a clear next meal, a few backups, and what to ease off for now. This is
          educational guidance—not a substitute for your care team.
        </p>
        {loading ? (
          <div className="py-10 text-center">
            <div className="spinner-border text-primary mx-auto" role="status" aria-label="Loading" />
            <p className="mt-3 mb-0 text-sm text-slate-700">Preparing your meal guidance…</p>
          </div>
        ) : !guidance || !na?.meal ? (
          <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/80 py-10 text-center">
            <p className="mb-4 text-slate-700">No meal guidance yet. Add a glucose reading above, or try loading again.</p>
            <button
              type="button"
              className="btn btn-primary px-5 py-2.5 text-sm"
              disabled={loading}
              onClick={() => loadRecommendations()}
            >
              {loading ? <i className="fas fa-spinner fa-spin" aria-hidden /> : <i className="fas fa-rotate-right" aria-hidden />}{' '}
              Try again
            </button>
          </div>
        ) : (
          <div className="flex flex-col gap-8">
            <article className="rounded-2xl border border-emerald-200/90 bg-gradient-to-br from-emerald-50/90 to-white p-5 shadow-sm sm:p-6">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-600 px-3 py-1 text-xs font-semibold text-white">
                  <span aria-hidden>🟢</span> {na.priority_label || 'Recommended now'}
                </span>
                {na.meal_type && (
                  <span className="rounded-full bg-white/80 px-2.5 py-0.5 text-xs font-medium text-slate-700 ring-1 ring-emerald-100">
                    {na.meal_type}
                  </span>
                )}
              </div>
              <h3 className="mb-2 text-xl font-semibold leading-snug text-slate-900">{na.meal}</h3>
              <p className="mb-3 text-sm leading-relaxed text-slate-800">{na.reason}</p>
              {na.highlights?.length > 0 && (
                <p className="mb-3 text-sm font-medium text-emerald-900">
                  {na.highlights.slice(0, 4).join(' • ')}
                </p>
              )}
              {na.when_to_eat && (
                <p className="mb-4 text-sm text-slate-600">
                  <span className="font-semibold text-slate-800">When: </span>
                  {na.when_to_eat}
                </p>
              )}
              {guidance.explanation && (
                <p className="mb-4 rounded-xl border border-emerald-100/80 bg-white/70 p-4 text-sm leading-relaxed text-slate-700">
                  {guidance.explanation}
                </p>
              )}
              {na.feedback_food_id != null && (
                <div className="flex flex-wrap gap-2 border-t border-emerald-100/80 pt-4">
                  <button
                    type="button"
                    className="inline-flex flex-1 min-w-[8rem] items-center justify-center gap-2 rounded-xl border border-emerald-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-800 hover:bg-emerald-50"
                    disabled={feedbackBusy[String(na.feedback_food_id)]}
                    onClick={() => sendFeedback(na.feedback_food_id, 'like')}
                  >
                    <i className="fas fa-thumbs-up" /> I can eat this
                  </button>
                  <button
                    type="button"
                    className="inline-flex flex-1 min-w-[8rem] items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-800 hover:bg-amber-50"
                    disabled={feedbackBusy[String(na.feedback_food_id)]}
                    onClick={() => sendFeedback(na.feedback_food_id, 'skip')}
                  >
                    <i className="fas fa-thumbs-down" /> Not suitable for me
                  </button>
                </div>
              )}
            </article>

            {guidance.alternatives?.length > 0 && (
              <div>
                <h3 className="mb-3 text-base font-semibold text-slate-900">Other good choices</h3>
                <ul className="m-0 grid list-none gap-3 p-0 sm:grid-cols-1 lg:grid-cols-3">
                  {guidance.alternatives.map((alt, idx) => (
                    <li
                      key={`${alt.meal}-${idx}`}
                      className="flex flex-col rounded-xl border border-slate-100 bg-slate-50/90 p-4 shadow-sm"
                    >
                      <p className="mb-1 font-semibold text-slate-900">{alt.meal}</p>
                      {alt.highlights?.length > 0 && (
                        <p className="mb-2 text-xs font-medium text-slate-600">{alt.highlights.join(' • ')}</p>
                      )}
                      <p className="mb-3 flex-1 text-sm text-slate-700">{alt.reason}</p>
                      {alt.feedback_food_id != null && (
                        <div className="mt-auto flex gap-2 border-t border-slate-100 pt-3">
                          <button
                            type="button"
                            className="flex flex-1 items-center justify-center gap-1 rounded-lg border border-slate-200 bg-white py-2 text-xs font-medium text-slate-800 hover:bg-emerald-50"
                            disabled={feedbackBusy[String(alt.feedback_food_id)]}
                            onClick={() => sendFeedback(alt.feedback_food_id, 'like')}
                          >
                            <i className="fas fa-thumbs-up" /> Works for me
                          </button>
                          <button
                            type="button"
                            className="flex flex-1 items-center justify-center gap-1 rounded-lg border border-slate-200 bg-white py-2 text-xs font-medium text-slate-800 hover:bg-amber-50"
                            disabled={feedbackBusy[String(alt.feedback_food_id)]}
                            onClick={() => sendFeedback(alt.feedback_food_id, 'skip')}
                          >
                            <i className="fas fa-thumbs-down" /> Skip
                          </button>
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {guidance.avoid?.length > 0 && (
              <div className="rounded-xl border border-amber-200/90 bg-amber-50/50 p-4 sm:p-5">
                <h3 className="mb-2 flex items-center gap-2 text-base font-semibold text-amber-950">
                  <span aria-hidden>⚠️</span> Avoid for now
                </h3>
                <ul className="m-0 list-disc space-y-1 pl-5 text-sm text-amber-950/90">
                  {guidance.avoid.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </section>

      <section className="flex flex-col gap-4" aria-labelledby="meal-plan-tips">
        <h2 id="meal-plan-tips" className="sr-only">
          Meal planning tips
        </h2>
        <p className="mb-0 text-center text-sm text-slate-600 md:text-left">
          Tap a card. The one you pick shows an easy step at the bottom.
        </p>
        <div
          className="grid grid-cols-1 gap-4 md:grid-cols-3 md:gap-5"
          role="group"
          aria-label="Quick meal habits"
        >
          {MEAL_TIPS.map((tip, index) => {
            const isActive = activeTipIndex === index;
            return (
              <button
                key={tip.id}
                type="button"
                onClick={() => setActiveTipIndex(index)}
                aria-pressed={isActive}
                className={[
                  'group flex flex-col rounded-2xl border p-6 text-left shadow-sm outline-none transition-all duration-200 sm:p-7',
                  'hover:-translate-y-0.5 hover:shadow-md active:translate-y-0 active:scale-[0.99]',
                  'focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2',
                  isActive
                    ? 'border-blue-400 bg-gradient-to-br from-blue-50/95 to-white ring-2 ring-blue-500/35 shadow-md'
                    : 'border-slate-200/90 bg-white hover:border-blue-200/80',
                ].join(' ')}
              >
                <div
                  className={[
                    'mb-4 flex h-12 w-12 items-center justify-center rounded-xl text-lg transition-colors duration-200',
                    isActive
                      ? 'bg-blue-600 text-white shadow-inner'
                      : 'bg-gradient-to-br from-blue-100 to-blue-200 text-blue-800 group-hover:from-blue-200 group-hover:to-blue-300',
                  ].join(' ')}
                >
                  <i className={`fas ${tip.icon}`} aria-hidden />
                </div>
                <span className="mb-1 inline-flex w-fit items-center rounded-full bg-slate-100 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-slate-600">
                  {isActive ? 'Active' : 'Tip'}
                </span>
                <h3 className="mb-2 font-outfit text-base font-semibold text-slate-900 sm:text-lg">{tip.title}</h3>
                <p className="mb-0 text-sm leading-relaxed text-slate-700">{tip.body}</p>
                {isActive && (
                  <p className="mt-4 border-t border-blue-100/80 pt-4 text-sm text-blue-900/90">
                    <span className="font-semibold text-blue-700">Easy step: </span>
                    {tip.hint}
                  </p>
                )}
              </button>
            );
          })}
        </div>
      </section>
    </div>
  );
}
