/**
 * Wait for GlucoSense API, then start Vite (Windows-safe; avoids `&&` in concurrently).
 */
const waitOn = require('wait-on')
const { spawn } = require('child_process')
const path = require('path')

const frontendRoot = path.resolve(__dirname, '..')
const vite = path.join(frontendRoot, 'node_modules', 'vite', 'bin', 'vite.js')

waitOn({
  // Prefix required — bare http:// is treated as a file path by wait-on
  resources: ['http-get://127.0.0.1:8000/api/health/live'],
  timeout: 120000,
  interval: 400,
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
