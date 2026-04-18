/**
 * Wait for GlucoSense API, then start Vite (Windows-safe; avoids `&&` in concurrently).
 */
const waitOn = require('wait-on')
const { spawn } = require('child_process')
const fs = require('fs')
const path = require('path')

const frontendRoot = path.resolve(__dirname, '..')
const vite = path.join(frontendRoot, 'node_modules', 'vite', 'bin', 'vite.js')
const repoRoot = path.resolve(frontendRoot, '..')
const apiPortFile = path.join(frontendRoot, '.glucosense-api-port')
const apiHost = process.env.GLUCOSENSE_API_HOST || '127.0.0.1'
const webPort = Number(process.env.GLUCOSENSE_WEB_PORT || 5173)

function resolveApiPort() {
  if (process.env.GLUCOSENSE_API_PORT && String(process.env.GLUCOSENSE_API_PORT).trim()) {
    return Number(process.env.GLUCOSENSE_API_PORT)
  }
  try {
    const raw = fs.readFileSync(apiPortFile, 'utf8').trim()
    const n = Number(raw)
    if (Number.isFinite(n) && n > 0) return n
  } catch {
    /* ignore */
  }
  return 8000
}

const apiPort = resolveApiPort()
process.env.GLUCOSENSE_API_PORT = String(apiPort)

waitOn({
  // Prefix required — bare http:// is treated as a file path by wait-on
  resources: [`http-get://${apiHost}:${apiPort}/api/health/ready`],
  timeout: 120000,
  interval: 400,
})
  .then(() => {
    console.log('[web] API and model readiness confirmed, starting Vite...')
    const child = spawn(process.execPath, [vite, '--port', String(webPort), '--strictPort'], {
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
