import React, { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';

function fmt(v) {
  if (v == null || Number.isNaN(v)) return '—';
  return typeof v === 'number' && !Number.isInteger(v) ? v.toFixed(1) : String(v);
}

export default function SmartSensor() {
  const [meta, setMeta] = useState(null);
  const [patients, setPatients] = useState([]);
  const [patientId, setPatientId] = useState('');
  const [summary, setSummary] = useState(null);
  const [readings, setReadings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setErr('');
      setLoading(true);
      try {
        const [m, p] = await Promise.all([api.sensorDemo.meta(), api.sensorDemo.patients(100)]);
        if (cancelled) return;
        setMeta(m);
        const list = p.patients || [];
        setPatients(list);
        if (list.length && !patientId) setPatientId(list[0]);
      } catch (e) {
        if (!cancelled) setErr(e.message || 'Failed to load sensor demo');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!patientId) return;
    let cancelled = false;
    (async () => {
      setErr('');
      try {
        const [s, r] = await Promise.all([
          api.sensorDemo.summary(patientId, 96),
          api.sensorDemo.series(patientId, 120),
        ]);
        if (cancelled) return;
        setSummary(s);
        setReadings(r.readings || []);
      } catch (e) {
        if (!cancelled) setErr(e.message || 'Failed to load patient series');
        setReadings([]);
        setSummary(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [patientId]);

  const latest = summary?.latest;

  const glucoseSpark = useMemo(() => {
    const g = readings.map((x) => x.glucose_level).filter((x) => x != null);
    if (g.length < 2) return null;
    const min = Math.min(...g);
    const max = Math.max(...g);
    const range = max - min || 1;
    return g.map((v, i) => ({
      x: (i / (g.length - 1)) * 100,
      y: 100 - ((v - min) / range) * 100,
      v,
    }));
  }, [readings]);

  return (
    <div className="page-content mx-auto w-full max-w-6xl gap-10 sm:gap-12">
      <header className="page-header overflow-hidden rounded-2xl px-5 py-6 shadow-header-chat sm:px-8 sm:py-8">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex items-start gap-4 sm:gap-5">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-white/15 text-2xl text-white shadow-inner sm:h-16 sm:w-16">
              <i className="fas fa-chart-line" aria-hidden />
            </div>
            <div>
              <p className="mb-2 inline-flex rounded-full bg-white/20 px-3 py-1 text-[0.6875rem] font-semibold uppercase tracking-[0.12em] text-white/95">
                Demo dataset
              </p>
              <h1 className="!mb-2 text-3xl font-bold tracking-tight text-white sm:text-4xl">Smart sensor data</h1>
              <p className="m-0 max-w-2xl text-sm leading-relaxed text-white/90 sm:text-base">
                Explore <strong className="font-semibold text-white">SmartSensor_DiabetesMonitoring.csv</strong>—glucose,
                heart rate, activity, sleep, and more. Synthetic research-style rows for UI and integration demos (not live
                devices).
              </p>
            </div>
          </div>
          <Link
            to="/app/glucose"
            className="inline-flex shrink-0 items-center justify-center gap-2 self-start rounded-xl border border-white/45 bg-white/10 px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-white/15"
          >
            <i className="fas fa-heart-pulse" />
            Your glucose log
          </Link>
        </div>
      </header>

      {err && <div className="alert alert-error rounded-xl">{err}</div>}

      {loading && !meta ? (
        <div className="rounded-2xl border border-slate-200/90 bg-white py-16 text-center shadow-sm">
          <div className="spinner-border text-primary mx-auto" />
          <p className="mt-4 mb-0 text-slate-600">Loading dataset…</p>
        </div>
      ) : (
        <>
          <section className="rounded-2xl border border-slate-200/90 bg-white p-6 shadow-sm sm:p-8">
            <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-blue-700 sm:text-xl">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                <i className="fas fa-database" />
              </span>
              Dataset
            </h2>
            <dl className="grid gap-3 text-sm sm:grid-cols-2">
              <div className="rounded-lg bg-slate-50 px-4 py-3">
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Rows loaded</dt>
                <dd className="mb-0 text-lg font-semibold text-slate-900">{meta?.row_count ?? 0}</dd>
              </div>
              <div className="rounded-lg bg-slate-50 px-4 py-3">
                <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Source file</dt>
                <dd className="mb-0 break-all font-mono text-xs text-slate-700">{meta?.csv_path || '—'}</dd>
              </div>
            </dl>
            {meta?.load_error && (
              <p className="mt-4 mb-0 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                {meta.load_error}
              </p>
            )}
          </section>

          <section className="rounded-2xl border border-slate-200/90 bg-white p-6 shadow-sm sm:p-8">
            <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
              <h2 className="mb-0 flex items-center gap-2 text-lg font-semibold text-blue-700 sm:text-xl">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                  <i className="fas fa-user" />
                </span>
                Patient preview
              </h2>
              <label className="flex flex-col gap-1 text-sm text-slate-600 sm:min-w-[12rem]">
                <span className="font-medium text-slate-700">Patient ID</span>
                <select
                  className="form-select rounded-xl border-slate-200 text-slate-900"
                  value={patientId}
                  onChange={(e) => setPatientId(e.target.value)}
                  disabled={!patients.length}
                >
                  {!patients.length ? <option value="">No patients</option> : null}
                  {patients.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            {latest && (
              <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Avg glucose (window)</p>
                  <p className="mb-0 text-2xl font-bold text-slate-900">{fmt(summary?.avg_glucose)} mg/dL</p>
                </div>
                <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Latest glucose</p>
                  <p className="mb-0 text-2xl font-bold text-slate-900">{fmt(latest.glucose_level)} mg/dL</p>
                </div>
                <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Heart rate</p>
                  <p className="mb-0 text-2xl font-bold text-slate-900">{fmt(latest.heart_rate)} bpm</p>
                </div>
                <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Steps (row)</p>
                  <p className="mb-0 text-2xl font-bold text-slate-900">{fmt(latest.step_count)}</p>
                </div>
              </div>
            )}

            {glucoseSpark && (
              <div className="mb-6 rounded-xl border border-slate-100 bg-slate-50/80 p-4">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Glucose trend (loaded window)</p>
                <svg viewBox="0 0 100 40" className="h-24 w-full text-blue-600" preserveAspectRatio="none" aria-hidden>
                  <polyline
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="0.8"
                    vectorEffect="non-scaling-stroke"
                    points={glucoseSpark.map((p) => `${p.x},${p.y}`).join(' ')}
                  />
                </svg>
              </div>
            )}

            <div className="overflow-x-auto rounded-xl border border-slate-100">
              <table className="w-full min-w-[640px] border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-600">
                    <th className="px-3 py-2.5">Time</th>
                    <th className="px-3 py-2.5">Glucose</th>
                    <th className="px-3 py-2.5">HR</th>
                    <th className="px-3 py-2.5">Activity</th>
                    <th className="px-3 py-2.5">Steps</th>
                    <th className="px-3 py-2.5">Stress</th>
                    <th className="px-3 py-2.5">Progression</th>
                  </tr>
                </thead>
                <tbody>
                  {[...readings].reverse().slice(0, 24).map((r, i) => (
                    <tr key={`${r.timestamp}-${i}`} className="border-b border-slate-100 text-slate-700">
                      <td className="whitespace-nowrap px-3 py-2 font-mono text-xs text-slate-600">{r.timestamp}</td>
                      <td className="px-3 py-2 font-medium text-slate-900">{fmt(r.glucose_level)}</td>
                      <td className="px-3 py-2">{fmt(r.heart_rate)}</td>
                      <td className="px-3 py-2">{fmt(r.activity_level)}</td>
                      <td className="px-3 py-2">{fmt(r.step_count)}</td>
                      <td className="px-3 py-2">{fmt(r.stress_level)}</td>
                      <td className="px-3 py-2">{fmt(r.predicted_progression)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-3 mb-0 text-xs text-slate-500">Showing last 24 rows of the loaded window (newest first).</p>
          </section>
        </>
      )}

      <section className="rounded-2xl border border-blue-100 bg-blue-50/60 p-6 text-sm leading-relaxed text-slate-700">
        <p className="mb-2 font-semibold text-blue-900">
          <i className="fas fa-file-pdf mr-2" aria-hidden />
          Using <code className="rounded bg-white/80 px-1.5 py-0.5 text-xs">Prompt.pdf</code> with the assistant
        </p>
        <p className="mb-0">
          Export or paste the PDF into{' '}
          <code className="rounded bg-white/80 px-1.5 py-0.5 text-xs">backend/knowledge/clinical_prompt_supplement.txt</code>{' '}
          (see <code className="rounded bg-white/80 px-1.5 py-0.5 text-xs">backend/knowledge/README.md</code>). When an LLM is
          configured, that text is appended to the system prompt. Optional:{' '}
          <code className="rounded bg-white/80 px-1.5 py-0.5 text-xs">python scripts/extract_prompt_pdf.py Prompt.pdf</code>{' '}
          after <code className="rounded bg-white/80 px-1.5 py-0.5 text-xs">pip install pypdf</code>.
        </p>
      </section>
    </div>
  );
}
