/**
 * API client - calls Glocusense FastAPI via Vite proxy (/api → backend).
 * Sends Bearer token from localStorage when present.
 */
const API_BASE = '/api';
const DEFAULT_TIMEOUT_MS = 45_000;

/** FastAPI often returns `detail` as a string or a list of validation objects. */
function formatApiDetail(detail, status) {
  if (detail == null) return `Request failed (${status})`;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((x) => (typeof x === 'object' && x != null ? x.msg || JSON.stringify(x) : String(x)))
      .join('; ');
  }
  if (typeof detail === 'object') return detail.message || JSON.stringify(detail);
  return String(detail);
}

/** Vite proxy often returns 500/502 with HTML or empty body when the real API is down or on the wrong port. */
function explainProxyOrServerError(status, textSnippet) {
  const t = (textSnippet || '').toLowerCase();
  const looksLikeProxy =
    status === 502 ||
    status === 503 ||
    (status >= 500 && (t.includes('proxy') || t.includes('econnrefused') || t.includes('vite')));
  if (status >= 500 || looksLikeProxy) {
    return (
      'Could not reach the Meal Plan API through the dev proxy. ' +
      'From Meal-Plan-System/backend run: PORT=8001 python run.py (PowerShell: $env:PORT="8001"; python run.py). ' +
      'Then start this Vite app with the API on 8001 (default in vite.config.js), or set MEAL_PLAN_API_PROXY=http://127.0.0.1:8001. ' +
      'Check http://localhost:5174/api/health (or your Vite port) — expect {"app":"glocusense-meal-plan"}.'
    );
  }
  return null;
}

function getToken() {
  return localStorage.getItem('token');
}

async function request(path, options = {}, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const url = `${API_BASE}${path}`;

  const controller = new AbortController();
  const timeoutErr = () =>
    new Error(
      `Request timed out after ${timeoutMs / 1000}s. ` +
        'Start the Meal Plan API from Meal-Plan-System/backend: PORT=8001 python run.py ' +
        '(GlucoSense uses 8000). Open your Meal Plan Vite URL + /api/health — expect {"app":"glocusense-meal-plan"}.'
    );

  const runFetch = async () => {
    const res = await fetch(url, { ...options, headers, signal: controller.signal });
    const text = await res.text();
    let data = {};
    if (text.trim()) {
      try {
        data = JSON.parse(text);
      } catch {
        if (!res.ok) {
          throw new Error(text.slice(0, 300) || `Request failed: ${res.status}`);
        }
      }
    }
    if (!res.ok) {
      const snippet = text.trim().slice(0, 400);
      const proxyHint = explainProxyOrServerError(res.status, snippet);
      const msg =
        data.error ||
        data.message ||
        (data.detail != null ? formatApiDetail(data.detail, res.status) : null) ||
        proxyHint ||
        (snippet && !snippet.startsWith('<') ? snippet : null) ||
        `Request failed: ${res.status}`;
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    return data;
  };

  return new Promise((resolve, reject) => {
    let settled = false;
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      controller.abort();
      reject(timeoutErr());
    }, timeoutMs);

    runFetch()
      .then((data) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        resolve(data);
      })
      .catch((err) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        if (err.name === 'AbortError') {
          reject(timeoutErr());
          return;
        }
        if (err.name === 'TypeError' && err.message.includes('fetch')) {
          reject(new Error('Network error. Please check if the server is running.'));
          return;
        }
        reject(err);
      });
  });
}

/** Auth can be slower on cold start / slow disks; keep below Vite proxy limit */
const AUTH_TIMEOUT_MS = 45_000;

export const api = {
  auth: {
    login: (username, password) =>
      request('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }, AUTH_TIMEOUT_MS),
    register: (data) => request('/auth/register', { method: 'POST', body: JSON.stringify(data) }, AUTH_TIMEOUT_MS),
    me: () => request('/auth/me', {}, AUTH_TIMEOUT_MS),
    patchProfile: (patch) =>
      request('/auth/profile', { method: 'PATCH', body: JSON.stringify(patch) }, AUTH_TIMEOUT_MS),
    completeOnboarding: () =>
      request('/auth/onboarding/complete', { method: 'POST', body: '{}' }, AUTH_TIMEOUT_MS),
  },
  search: (q, limit = 20) => request(`/search?q=${encodeURIComponent(q)}&limit=${limit}`),
  chatbotSessions: {
    list: () => request('/chatbot/sessions'),
    create: () => request('/chatbot/sessions', { method: 'POST', body: '{}' }),
    delete: (sessionId) =>
      request(`/chatbot/sessions/${sessionId}`, { method: 'DELETE' }),
    messages: (sessionId) => request(`/chatbot/sessions/${sessionId}/messages`),
  },
  chatbot: (message, sessionId) =>
    request('/chatbot/message', {
      method: 'POST',
      body: JSON.stringify({ message, session_id: sessionId }),
    }),
  recommendations: (limit = 12) => request(`/recommendations?limit=${limit}`),
  glucose: {
    list: () => request('/glucose'),
    add: (reading_value, reading_type, notes) =>
      request('/glucose', { method: 'POST', body: JSON.stringify({ reading_value, reading_type, notes }) }),
  },
  /** SmartSensor_DiabetesMonitoring.csv demo (synthetic wearable-style rows). */
  sensorDemo: {
    meta: () => request('/sensor-demo/meta'),
    patients: (limit = 80) => request(`/sensor-demo/patients?limit=${limit}`),
    series: (patientId, limit = 200) =>
      request(`/sensor-demo/series?patient_id=${encodeURIComponent(patientId)}&limit=${limit}`),
    summary: (patientId, lastN = 96) =>
      request(`/sensor-demo/summary?patient_id=${encodeURIComponent(patientId)}&last_n=${lastN}`),
  },
};
