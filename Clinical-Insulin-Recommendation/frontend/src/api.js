/**
 * Fetch wrapper that adds ngrok-skip-browser-warning header.
 * Required when the app is served through ngrok free tier to avoid 403 Forbidden.
 */
const NGROK_HEADER = { 'ngrok-skip-browser-warning': '1' }

/**
 * Fetch with ngrok header. On network failure (backend down, Vite down, CORS), returns a
 * synthetic 503 JSON Response so callers never get an uncaught "Failed to fetch".
 */
export async function apiFetch(url, options = {}) {
  const headers = { ...NGROK_HEADER, ...options.headers }
  try {
    return await fetch(url, { ...options, headers })
  } catch (err) {
    const detail =
      err instanceof TypeError
        ? 'Network error: start the FastAPI backend on port 8000 and the Vite dev server (npm run start in frontend). If the page shows connection refused, the dev server exited — restart it.'
        : String(err?.message || err)
    return new Response(JSON.stringify({ detail }), {
      status: 503,
      statusText: 'Service Unavailable',
      headers: { 'Content-Type': 'application/json' },
    })
  }
}
