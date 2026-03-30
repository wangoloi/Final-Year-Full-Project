/**
 * Start GlucoSense FastAPI from repo root (avoids PATH issues with ';' in Windows paths).
 * Uses .venv if present and runnable; skips broken venvs (e.g. copied from another PC).
 * Override: set GLUCOSENSE_PYTHON to a full path to python.exe
 */
const { spawn, execFileSync } = require('child_process')
const fs = require('fs')
const path = require('path')

const repoRoot = path.resolve(__dirname, '..', '..')
const API_PORT = Number(process.env.GLUCOSENSE_API_PORT || 8000)

/**
 * Windows: WinError 10048 when another uvicorn (or any process) still holds 127.0.0.1:8000.
 * Free listeners on API_PORT before spawning. Set GLUCOSENSE_SKIP_FREE_PORT=1 to skip.
 *
 * Uses netstat + taskkill (reliable) and PowerShell Get-NetTCPConnection (no State filter —
 * the Listen-only filter can miss rows depending on TcpState enum / locale).
 */
function sleepSyncMs(ms) {
  if (ms <= 0) return
  try {
    if (process.platform === 'win32') {
      execFileSync('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command', `Start-Sleep -Milliseconds ${ms}`], {
        stdio: 'ignore',
      })
    } else {
      execFileSync('sleep', [String(ms / 1000)], { stdio: 'ignore' })
    }
  } catch {
    const end = Date.now() + ms
    while (Date.now() < end) {
      /* last-resort spin */
    }
  }
}

function freeListenPortWin32(port) {
  const pids = new Set()
  try {
    const out = execFileSync('cmd.exe', ['/c', 'netstat -ano -p tcp'], { encoding: 'utf8' })
    // Trim trailing CRLF junk so $ anchors match; netstat lines can end with \r.
    const localPortRe = new RegExp(`^\\s*TCP\\s+\\S+:${port}\\s+`, 'i')
    for (const raw of out.split(/\r?\n/)) {
      const line = raw.replace(/\r$/, '').trimEnd()
      if (!/LISTENING/i.test(line)) continue
      if (!localPortRe.test(line)) continue
      const m = line.match(/LISTENING\s+(\d+)\s*$/i)
      if (m) pids.add(parseInt(m[1], 10))
    }
  } catch {
    /* netstat missing or no listeners */
  }
  for (const pid of pids) {
    try {
      execFileSync('taskkill', ['/F', '/PID', String(pid)], { stdio: 'ignore' })
    } catch {
      /* access denied or already gone */
    }
  }
  try {
    const ps = [
      '$ErrorActionPreference = "SilentlyContinue"',
      `$c = Get-NetTCPConnection -LocalPort ${port} -State Listen -ErrorAction SilentlyContinue`,
      'if ($c) { $c | ForEach-Object { $opid = $_.OwningProcess; if ($opid -gt 0) { Stop-Process -Id $opid -Force -ErrorAction SilentlyContinue } } }',
    ].join('; ')
    execFileSync('powershell.exe', ['-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-Command', ps], {
      stdio: 'ignore',
    })
  } catch {
    /* ignore */
  }
}

function freeListenPort(port) {
  if (process.env.GLUCOSENSE_SKIP_FREE_PORT === '1') return
  if (!Number.isFinite(port) || port < 1) return
  try {
    if (process.platform === 'win32') {
      freeListenPortWin32(port)
    } else {
      try {
        const out = execFileSync('lsof', ['-nP', '-iTCP:' + port, '-sTCP:LISTEN', '-t'], { encoding: 'utf8' })
        for (const line of out.trim().split(/\n/)) {
          const n = parseInt(line.trim(), 10)
          if (n > 0) {
            try {
              process.kill(n, 'SIGKILL')
            } catch {
              /* ignore */
            }
          }
        }
      } catch {
        /* no lsof or nothing listening */
      }
    }
  } catch {
    /* ignore — bind will fail with a clear error if still busy */
  }
}

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

/** Resolve bare `python` to a full path so we never need shell:true (avoids Node DEP0190). */
function resolvePythonExecutable() {
  const p = resolvePython()
  if (p !== 'python' && p !== 'py') return p
  try {
    if (process.platform === 'win32') {
      const out = execFileSync('where.exe', ['python'], { encoding: 'utf8' })
      const line = out
        .split(/\r?\n/)
        .map((s) => s.trim())
        .find(Boolean)
      if (line) return line
    } else {
      const out = execFileSync('which', ['python'], { encoding: 'utf8' })
      const line = out.trim().split('\n')[0]
      if (line) return line
    }
  } catch {
    /* fall through */
  }
  return p
}

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
if (reload) uvicornArgs.push('--reload')
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
  }
)

child.on('error', (err) => {
  console.error('[api] Failed to spawn Python/uvicorn:', err.message)
  console.error('[api] Set GLUCOSENSE_PYTHON to python.exe or create .venv in the repo root.')
  process.exit(1)
})

child.on('exit', (code) => process.exit(code == null ? 0 : code))
