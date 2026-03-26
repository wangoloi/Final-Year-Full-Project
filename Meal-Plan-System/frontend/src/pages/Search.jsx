import React, { useState } from 'react';
import { api } from '../api';

export default function Search() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [notFound, setNotFound] = useState(false);

  async function handleSearch(e) {
    e?.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError('');
    setNotFound(false);
    setResults([]);
    try {
      const data = await api.search(query.trim(), 20);
      setResults(data.results || []);
      setNotFound(data.not_found || false);
    } catch (err) {
      setError(err.message || 'Search failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page-content">
      <div className="page-header">
        <h1><i className="fas fa-apple-whole" /> Search Foods</h1>
        <p>Find diabetes-friendly local and healthy foods</p>
      </div>
      <div className="card">
        <form onSubmit={handleSearch} className="d-flex gap-2 flex-wrap">
          <input
            type="search"
            className="form-input min-w-0 flex-1"
            style={{ minWidth: '200px' }}
            placeholder="e.g. matooke, low sugar fruit, beans..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? (
                <>
                  <i className="fas fa-spinner fa-spin" /> Searching...
                </>
              ) : (
                <>
                  <i className="fas fa-search" /> Search
                </>
              )}
            </button>
        </form>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {notFound && results.length === 0 && (
        <div className="card text-center p-5">
          <i className="fas fa-question-circle icon-3xl text-muted mb-3" />
          <h3 className="text-xl mb-2 text-muted">No results found</h3>
          <p className="text-muted mb-0">Try a different search term or spelling.</p>
        </div>
      )}

      {results.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h2 className="text-xl mb-0">Found <strong>{results.length}</strong> result(s)</h2>
          </div>
          <div className="grid-2 gap-3">
            {results.map((f) => (
              <div key={f.id} className="p-4 bg-gray-50 rounded transition hover:shadow-md break-words grid-item">
                <h4 className="text-lg mb-1 break-words">{f.name}{f.local_name ? ` (${f.local_name})` : ''}</h4>
                <p className="text-sm text-muted mb-0">
                  {f.calories} cal · Glycemic index: {f.glycemic_index ?? 'N/A'} · <span className="badge bg-secondary">{f.category}</span>
                  {f.diabetes_friendly && (
                    <span className="badge bg-success ms-1"><i className="fas fa-check" /> Diabetes-friendly</span>
                  )}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

