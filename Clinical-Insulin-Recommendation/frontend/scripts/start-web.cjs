/**
 * Wait for GlucoSense API, then start Vite (Windows-safe; avoids `&&` in concurrently).
 */
const waitOn = require('wait-on')
const { spawn } = require('child_process')
const path = require('path')

const frontendRoot = path.resolve(__dirname, '..')
const vite = path.join(frontendRoot, 'node_modules', 'vite', 'bin', 'vite.js')

// First cold import (ML stack + FastAPI routes) can exceed 2 minutes on some machines.
const WAIT_MS = Number(process.env.GLUCOSENSE_API_WAIT_MS) || 600000

console.log(
  `[web] Waiting for API (GET /api/health/live), up to ${Math.round(WAIT_MS / 1000)}s — first start can be slow…`
)

waitOn({
  // Prefix required — bare http:// is treated as a file path by wait-on
  resources: ['http-get://127.0.0.1:8000/api/health/live'],
  timeout: WAIT_MS,
  interval: 500,
})
  .then(() => {
    console.log('[web] API ready, starting Vite...')
    const child = spawn(process.execPath, [vite], {
      cwd: frontendRoot,
      stdio: 'inherit',
      env: { ...process.env },
    })
    child.on('exit', (code, signal) => {
      if (signal) process.exit(1)
      process.exit(code == null ? 0 : code)
    })
  })
  .catch((err) => {
    console.error('[web] wait-on failed:', err.message || err)
    process.exit(1)
  })
