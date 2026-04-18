import React, { useState } from 'react';
import { api } from '../api';

export default function Search() {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [notFound, setNotFound] = useState(false);
  const [suggestOpen, setSuggestOpen] = useState(false);
  const [suggestLoading, setSuggestLoading] = useState(false);

  async function fetchSuggest(next) {
    const q = (next || '').trim();
    if (q.length < 1) {
      setSuggestions([]);
      return;
    }
    setSuggestLoading(true);
    try {
      const data = await api.searchSuggest(q, 8);
      setSuggestions(data.results || []);
    } catch {
      setSuggestions([]);
    } finally {
      setSuggestLoading(false);
    }
  }

  async function handleSearch(e) {
    e?.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError('');
    setNotFound(false);
    setResults([]);
    setSuggestOpen(false);
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
            onChange={(e) => {
              const next = e.target.value;
              setQuery(next);
              setSuggestOpen(true);
              fetchSuggest(next);
            }}
            onBlur={() => setTimeout(() => setSuggestOpen(false), 140)}
            onFocus={() => query.trim() && setSuggestOpen(true)}
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
        {suggestOpen && (suggestions.length > 0 || suggestLoading) && (
          <div className="mt-2 rounded-xl border border-slate-200 bg-white shadow-sm">
            {suggestLoading && (
              <div className="px-4 py-3 text-sm text-muted">
                <i className="fas fa-spinner fa-spin" /> Loading suggestions...
              </div>
            )}
            {!suggestLoading && suggestions.map((s) => (
              <button
                key={`s-${s.id}`}
                type="button"
                className="w-full text-left px-4 py-3 hover:bg-gray-50 border-0 bg-transparent"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => {
                  const label = `${s.name}${s.local_name ? ` (${s.local_name})` : ''}`;
                  setQuery(label);
                  setSuggestOpen(false);
                  setSuggestions([]);
                }}
              >
                <div className="text-sm font-medium text-slate-900">{s.name}{s.local_name ? ` (${s.local_name})` : ''}</div>
                <div className="text-xs text-muted">{s.category} · {s.calories} cal · GI {s.glycemic_index ?? 'N/A'}</div>
              </button>
            ))}
          </div>
        )}
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

