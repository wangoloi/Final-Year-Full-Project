import React, { useState, useEffect } from 'react';
import { api } from '../../lib/api';

export default function Glucose() {
  const [readings, setReadings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ reading_value: '', reading_type: 'fasting', notes: '' });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    api.glucose.list()
      .then((data) => setReadings(data.readings || []))
      .catch(() => setError('Failed to load readings'))
      .finally(() => setLoading(false));
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.reading_value || isNaN(parseFloat(form.reading_value))) {
      setError('Please enter a valid reading value');
      return;
    }
    setError('');
    setSuccess('');
    try {
      await api.glucose.add(parseFloat(form.reading_value), form.reading_type, form.notes || null);
      setSuccess('Reading recorded successfully!');
      setForm({ reading_value: '', reading_type: 'fasting', notes: '' });
      const data = await api.glucose.list();
      setReadings(data.readings || []);
    } catch (err) {
      setError(err.message || 'Failed to save reading');
    }
  }

  return (
    <div className="page-content">
      <div className="page-header">
        <h1><i className="fas fa-heart-pulse" /> Record Glucose</h1>
        <p>Track your blood glucose readings (mg/dL)</p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="card">
        <h2 className="text-xl mb-3">Add New Reading</h2>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <div className="mb-3">
            <label className="form-label text-strong">Value (mg/dL)</label>
            <input
              type="number"
              step="0.1"
              className="form-input"
              value={form.reading_value}
              onChange={(e) => setForm((f) => ({ ...f, reading_value: e.target.value }))}
              placeholder="e.g. 120"
              required
            />
          </div>
          <div className="mb-3">
            <label className="form-label text-strong">Type</label>
            <select
              className="form-select"
              value={form.reading_type}
              onChange={(e) => setForm((f) => ({ ...f, reading_type: e.target.value }))}
            >
              <option value="fasting">Fasting</option>
              <option value="pre_meal">Pre-meal</option>
              <option value="post_meal">Post-meal</option>
              <option value="random">Random</option>
            </select>
          </div>
          <div className="mb-4">
            <label className="form-label text-strong">Notes (optional)</label>
            <input
              type="text"
              className="form-input"
              value={form.notes}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
              placeholder="e.g. Before breakfast, after exercise"
              maxLength={200}
            />
          </div>
          <button type="submit" className="btn btn-primary btn-full">
            <i className="fas fa-save" /> Save Reading
          </button>
        </form>
      </div>

      <div className="card">
        <h2 className="text-xl mb-3">Recent Readings</h2>
        {loading ? (
          <div className="text-center p-5">
            <div className="spinner-border text-primary" role="status">
              <span className="visually-hidden">Loading...</span>
            </div>
          </div>
        ) : readings.length === 0 ? (
          <div className="text-center p-5">
            <i className="fas fa-heart-pulse icon-2xl text-muted mb-3" />
            <p className="text-muted mb-0">No readings yet. Record your first one above!</p>
          </div>
        ) : (
          <div className="d-flex flex-wrap gap-3">
            {readings.map((r) => (
              <div key={r.id} className="p-4 bg-gray-50 rounded border-start transition hover:shadow-md reading-item">
                <div className="d-flex justify-content-between align-items-start mb-1">
                  <strong className="text-2xl text-primary">{r.reading_value} mg/dL</strong>
                  <span className="badge bg-secondary text-sm">{r.reading_type.toUpperCase()}</span>
                </div>
                <div className="text-sm text-muted mb-2">{new Date(r.reading_time).toLocaleString()}</div>
                {r.notes && (
                  <p className="text-sm text-muted mb-0 break-words">{r.notes}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

