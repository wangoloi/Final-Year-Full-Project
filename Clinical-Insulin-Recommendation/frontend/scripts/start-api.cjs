/**
 * Start GlucoSense FastAPI from repo root (avoids PATH issues with ';' in Windows paths).
 * Uses .venv if present and runnable; skips broken venvs (e.g. copied from another PC).
 * Override: set GLUCOSENSE_PYTHON to a full path to python.exe
 */
const { spawn, execFileSync } = require('child_process')
const fs = require('fs')
const net = require('net')
const path = require('path')

const repoRoot = path.resolve(__dirname, '..', '..')
const apiHost = process.env.GLUCOSENSE_API_HOST || '127.0.0.1'
const apiPortDefault = Number(process.env.GLUCOSENSE_API_PORT || 8000)
const apiPortFile = path.join(repoRoot, 'frontend', '.glucosense-api-port')
const legacyBundlePath = path.join(repoRoot, 'outputs', 'best_model', 'inference_bundle.joblib')
const legacyBundleTrainer = path.join(repoRoot, 'scripts', 'quick_train_inference_bundle.py')
const reservedPorts = new Set(
  String(process.env.GLUCOSENSE_RESERVED_PORTS || '')
    .split(',')
    .map((value) => Number(String(value).trim()))
    .filter((value) => Number.isFinite(value) && value > 0)
)

function resolvePython() {
  if (process.env.GLUCOSENSE_PYTHON && fs.existsSync(process.env.GLUCOSENSE_PYTHON)) {
    return process.env.GLUCOSENSE_PYTHON
  }
  const candidates = [
    path.join(repoRoot, '.venv', 'Scripts', 'python.exe'),
    path.join(repoRoot, '.venv', 'bin', 'python'),
  ]
  for (const p of candidates) {
    if (!fs.existsSync(p)) continue
    try {
      // Ensure the chosen interpreter can actually run our API entrypoint.
      // Common issue on Windows: a copied/partial .venv exists but is missing uvicorn.
      execFileSync(p, ['-c', 'import uvicorn'], { stdio: 'ignore' })
      return p
    } catch {
      /* broken venv */
    }
  }
  return 'python'
}

const pythonExe = resolvePython()

function verifyApiImports() {
  try {
    execFileSync(pythonExe, ['-c', 'import app'], {
      cwd: repoRoot,
      stdio: 'ignore',
      env: { ...process.env, PYTHONUNBUFFERED: '1' },
    })
  } catch (err) {
    console.error(
      '\n[GlucoSense API] Python environment is missing one or more backend dependencies.\n' +
      'Install the clinical requirements in the interpreter used for startup, for example:\n\n' +
      `  ${pythonExe} -m pip install -r requirements.txt\n`
    )
    throw err
  }
}

function assertPortAvailable(port) {
  return new Promise((resolve, reject) => {
    const server = net.createServer()
    server.unref()
    server.on('error', (err) => reject(err))
    server.listen({ host: apiHost, port }, () => {
      server.close(() => resolve(true))
    })
  })
}

async function pickApiPort(preferredPort) {
  // If user set GLUCOSENSE_API_PORT explicitly, don't auto-scan: fail fast.
  const userSpecified = typeof process.env.GLUCOSENSE_API_PORT === 'string' && process.env.GLUCOSENSE_API_PORT.trim()
  const candidates = userSpecified
    ? [preferredPort]
    : [preferredPort, preferredPort + 1, preferredPort + 2, preferredPort + 3, preferredPort + 4, preferredPort + 5]
  for (const p of candidates) {
    if (!userSpecified && reservedPorts.has(p)) continue
    try {
      await assertPortAvailable(p)
      return p
    } catch (err) {
      if (err && err.code === 'EADDRINUSE') continue
      throw err
    }
  }
  const err = new Error(`No free port found near ${preferredPort}`)
  err.code = 'EADDRINUSE'
  throw err
}

function writeSelectedPort(port) {
  try {
    fs.writeFileSync(apiPortFile, String(port), 'utf8')
  } catch {
    /* ignore */
  }
}

<<<<<<< HEAD
async function main() {
  let apiPort = apiPortDefault
  try {
    apiPort = await pickApiPort(apiPortDefault)
  } catch (err) {
    if (err && err.code === 'EADDRINUSE') {
      console.error(
        `\n[GlucoSense API] Port ${apiPortDefault} is already in use.\n` +
        `Close the old API process, or run with a different port:\n\n` +
        `  PowerShell: $env:GLUCOSENSE_API_PORT=${apiPortDefault + 1}; npm run dev:api\n\n` +
        `If you want to stop the process on ${apiPortDefault}:\n` +
        `  PowerShell (Admin): Stop-Process -Id (Get-NetTCPConnection -LocalPort ${apiPortDefault} -State Listen).OwningProcess -Force\n`
      )
      process.exit(1)
    }
    console.error('\n[GlucoSense API] Could not check port availability:', err)
    process.exit(1)
=======
const pythonExe = resolvePythonExecutable()
// On Windows, uvicorn --reload can trigger Errno 10048 (bind race with the reloader). Default
// reload OFF on win32; set GLUCOSENSE_UVICORN_RELOAD=1 or true to enable. Other OS: unchanged.
const rEnv = process.env.GLUCOSENSE_UVICORN_RELOAD
let reload
if (process.platform === 'win32') {
  reload = rEnv === '1' || rEnv === 'true'
} else {
  reload = rEnv !== '0' && rEnv !== 'false'
}
const uvicornArgs = ['-m', 'uvicorn', 'app:app']
if (reload) {
  uvicornArgs.push('--reload')
  // Narrow reload scope (especially on Windows) so file watching is cheaper and the reloader
  // is less likely to fight the main process on the same port.
  const backendSrc = path.join(repoRoot, 'backend', 'src')
  if (fs.existsSync(backendSrc)) {
    uvicornArgs.push('--reload-dir', backendSrc)
  }
  const backendDir = path.join(repoRoot, 'backend')
  if (fs.existsSync(backendDir)) {
    uvicornArgs.push('--reload-dir', backendDir)
  }
}
uvicornArgs.push('--host', '127.0.0.1', '--port', String(API_PORT))

freeListenPort(API_PORT)
if (process.platform === 'win32') {
  sleepSyncMs(200)
  freeListenPort(API_PORT)
  sleepSyncMs(400)
}

const child = spawn(
  pythonExe,
  uvicornArgs,
  {
    cwd: repoRoot,
    stdio: 'inherit',
    shell: false,
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
>>>>>>> b6816fd33938d1f6eb4b13b3b7093ccb1d6508fa
  }

  writeSelectedPort(apiPort)
  process.env.GLUCOSENSE_API_PORT = String(apiPort)

  try {
    verifyApiImports()
  } catch {
    process.exit(1)
  }

  // Ensure the legacy (fallback) bundle exists so /api/recommend doesn't 503 on first run.
  // If Smart Sensor bundle exists, the API will use that automatically; this just prevents
  // the fallback path from failing in fresh clones.
  const autoTrainDisabled = String(process.env.GLUCOSENSE_AUTO_TRAIN || '').trim() === '0'
  if (!autoTrainDisabled && !fs.existsSync(legacyBundlePath) && fs.existsSync(legacyBundleTrainer)) {
    console.log(`\n[GlucoSense API] Legacy bundle missing. Generating: ${path.relative(repoRoot, legacyBundlePath)}\n`)
    try {
      execFileSync(pythonExe, [legacyBundleTrainer], {
        cwd: repoRoot,
        stdio: 'inherit',
        env: { ...process.env, PYTHONUNBUFFERED: '1' },
      })
    } catch (e) {
      console.warn('\n[GlucoSense API] Auto-train failed. The API may return 503 for legacy endpoints.\n', e)
    }
  }

  const child = spawn(
    pythonExe,
    ['-m', 'uvicorn', 'app:app', '--reload', '--host', apiHost, '--port', String(apiPort)],
    {
      cwd: repoRoot,
      stdio: 'inherit',
      shell: pythonExe === 'python',
      env: { ...process.env, PYTHONUNBUFFERED: '1' },
    }
  )

  child.on('exit', (code) => process.exit(code == null ? 0 : code))
}

main()
