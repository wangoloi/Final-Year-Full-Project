/**
 * Start GlucoSense FastAPI from repo root (avoids PATH issues with ';' in Windows paths).
 * Uses .venv if present and runnable; skips broken venvs (e.g. copied from another PC).
 * Override: set GLUCOSENSE_PYTHON to a full path to python.exe
 */
const { spawn, execFileSync } = require('child_process')
const fs = require('fs')
const path = require('path')

const repoRoot = path.resolve(__dirname, '..', '..')

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
      execFileSync(p, ['-c', 'import sys'], { stdio: 'ignore' })
      return p
    } catch {
      /* broken venv */
    }
  }
  return 'python'
}

const pythonExe = resolvePython()
const child = spawn(
  pythonExe,
  ['-m', 'uvicorn', 'app:app', '--reload', '--host', '127.0.0.1', '--port', '8000'],
  {
    cwd: repoRoot,
    stdio: 'inherit',
    shell: pythonExe === 'python',
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
  }
)

child.on('exit', (code) => process.exit(code == null ? 0 : code))
