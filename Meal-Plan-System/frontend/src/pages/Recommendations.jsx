import React, { useState, useEffect } from 'react';
import { api } from '../api';

export default function Recommendations() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api.recommendations(20)
      .then((data) => setItems(data.recommendations || []))
      .catch((err) => setError(err.message || 'Failed to load recommendations'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="page-content">
      <div className="page-header">
        <h1><i className="fas fa-seedling" /> Food Recommendations</h1>
        <p>Personalized low-glycemic index, diabetes-friendly foods</p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {loading ? (
        <div className="text-center p-5">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
          <p className="text-muted mt-2 mb-0">Loading recommendations...</p>
        </div>
      ) : items.length === 0 ? (
        <div className="card text-center p-5">
          <i className="fas fa-seedling icon-3xl text-muted mb-3" />
          <p className="text-muted mb-0">No recommendations yet. Complete your profile for personalized suggestions.</p>
        </div>
      ) : (
        <div className="grid-2 gap-3">
          {items.map((item) => (
            <div key={item.id} className="card card-clickable rec-card">
              <h4 className="text-xl mb-2 break-words">{item.name}{item.local_name ? ` (${item.local_name})` : ''}</h4>
              <p className="text-sm text-muted mb-2">
                {item.calories} cal · Glycemic index: {item.glycemic_index ?? 'N/A'} · <span className="badge bg-success">{item.category}</span>
              </p>
              <p className="text-sm mb-3">
                <i className="fas fa-dumbbell" /> Protein: <strong>{item.protein}g</strong> · 
                <i className="fas fa-carrot" /> Carbs: <strong>{item.carbs}g</strong> · 
                <i className="fas fa-seedling" /> Fiber: <strong>{item.fiber}g</strong>
              </p>
              {item.diabetes_friendly && (
                <div className="badge bg-success fs-6 px-3 py-2">
                  <i className="fas fa-check-circle" /> Diabetes-friendly
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

