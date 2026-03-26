/**
 * Fetch wrapper that adds ngrok-skip-browser-warning header.
 * Required when the app is served through ngrok free tier to avoid 403 Forbidden.
 */
const NGROK_HEADER = { 'ngrok-skip-browser-warning': '1' }

export function apiFetch(url, options = {}) {
  const headers = { ...NGROK_HEADER, ...options.headers }
  return fetch(url, { ...options, headers })
}
