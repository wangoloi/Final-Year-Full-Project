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

function devHealthCheckUrl() {
  if (typeof window !== 'undefined' && window.location?.origin) {
    return `${window.location.origin}/api/health`;
  }
  return 'http://localhost:5175/api/health (or your Vite dev URL + /api/health)';
}

/**
 * When the Meal Plan FastAPI is not running (or wrong port), Vite often returns 502/503 or 500 with HTML/empty body.
 * Do NOT treat every HTTP 500 as a proxy failure — FastAPI may return 500 JSON with `detail` for real server errors.
 */
function explainProxyOrServerError(status, textSnippet) {
  const raw = textSnippet || '';
  const t = raw.toLowerCase();
  const empty = !raw.trim();
  const isHtml =
    /^\s*</.test(raw) && (t.includes('<!doctype') || t.includes('<html') || t.includes('<head'));
  const looksLikeProxy =
    status === 502 ||
    status === 503 ||
    status === 504 ||
    (empty && status >= 500) ||
    isHtml ||
    t.includes('econnrefused') ||
    t.includes('socket hang up') ||
    t.includes('proxy error') ||
    (status >= 500 && (t.includes('proxy') || t.includes('vite')));
  if (!looksLikeProxy) return null;
  return (
    'Could not reach the Meal Plan API (nothing listening on the port Vite proxies to — usually 8001). ' +
    'Start the API: cd Meal-Plan-System/backend then: $env:PORT="8001"; python run.py ' +
    '(or from repo root: npm run meal-api). ' +
    'If the API uses another port, set MEAL_PLAN_API_PROXY before npm run dev, e.g. ' +
    '$env:MEAL_PLAN_API_PROXY="http://127.0.0.1:9000". ' +
    `Then open ${devHealthCheckUrl()} — expect JSON with "app":"glocusense-meal-plan".`
  );
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
        'Start the Meal Plan API: cd Meal-Plan-System/backend && python run.py (default port 8001). ' +
        'GlucoSense clinical API uses 8000 — do not confuse the two. ' +
        `Check ${devHealthCheckUrl()} for {"app":"glocusense-meal-plan"}.`
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
          const snippet = text.trim().slice(0, 400);
          const proxyHint = explainProxyOrServerError(res.status, snippet);
          throw new Error(proxyHint || snippet.slice(0, 300) || `Request failed: ${res.status}`);
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
          reject(
            new Error(
              `Network error (API may be down or on the wrong port). ${explainProxyOrServerError(502, '') || ''}`.trim()
            )
          );
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
  recommendationEngineMeta: () => request('/recommendations/engine'),
  recommendationFeedback: (foodId, action) =>
    request('/recommendations/feedback', {
      method: 'POST',
      body: JSON.stringify({ food_id: foodId, action }),
    }),
  glucose: {
    list: () => request('/glucose'),
    add: (reading_value, reading_type, notes) =>
      request('/glucose', { method: 'POST', body: JSON.stringify({ reading_value, reading_type, notes }) }),
  },
};
