/**
 * Wait for the Meal Plan API readiness endpoint before starting Vite.
 */
const fs = require('fs')
const http = require('http')
const path = require('path')
const { spawn } = require('child_process')

const frontendRoot = path.resolve(__dirname, '..')
const vite = path.join(frontendRoot, 'node_modules', 'vite', 'bin', 'vite.js')
const apiHost = process.env.MEAL_PLAN_API_HOST || '127.0.0.1'
const apiPort = Number(process.env.MEAL_PLAN_API_PORT || 8001)
const vitePort = Number(process.env.MEAL_PLAN_VITE_PORT || 5175)
const timeoutMs = Number(process.env.MEAL_PLAN_READY_TIMEOUT_MS || 120000)
const startedAt = Date.now()
const readinessPaths = ['/health/ready', '/api/health', '/health']

function requestReady(pathname) {
  return new Promise((resolve, reject) => {
    const req = http.get(
      {
        host: apiHost,
        port: apiPort,
        path: pathname,
        timeout: 3000,
      },
      (res) => {
        const chunks = []
        res.on('data', (chunk) => chunks.push(chunk))
        res.on('end', () => {
          const body = Buffer.concat(chunks).toString('utf8')
          if (res.statusCode && res.statusCode >= 200 && res.statusCode < 300) {
            resolve(body)
            return
          }
          reject(new Error(`Meal API readiness returned ${res.statusCode || 'unknown'} on ${pathname}: ${body}`))
        })
      }
    )
    req.on('timeout', () => req.destroy(new Error('Meal API readiness request timed out')))
    req.on('error', reject)
  })
}

async function waitForReady() {
  for (;;) {
    if (Date.now() - startedAt > timeoutMs) {
      throw new Error(`Timed out waiting for Meal API readiness on http://${apiHost}:${apiPort}`)
    }
    let ready = false
    for (const pathname of readinessPaths) {
      try {
        await requestReady(pathname)
        ready = true
        break
      } catch (err) {
        /* try next readiness path */
      }
    }
    if (ready) {
      return
    }
    {
      await new Promise((resolve) => setTimeout(resolve, 500))
      if ((Date.now() - startedAt) % 5000 < 500) {
        console.log(`[meal-web] Waiting for Meal API readiness on ${apiHost}:${apiPort}...`)
      }
    }
  }
}

async function main() {
  if (!fs.existsSync(vite)) {
    console.error('[meal-web] Missing Vite binary. Run npm install in Meal-Plan-System/frontend first.')
    process.exit(1)
  }

  try {
    await waitForReady()
    console.log('[meal-web] Meal API ready, starting Vite...')
  } catch (err) {
    console.error('[meal-web] wait-for-ready failed:', err.message || err)
    process.exit(1)
  }

  const child = spawn(process.execPath, [vite, '--port', String(vitePort), '--strictPort'], {
    cwd: frontendRoot,
    stdio: 'inherit',
    env: { ...process.env },
  })
  child.on('exit', (code, signal) => {
    if (signal) process.exit(1)
    process.exit(code == null ? 0 : code)
  })
}

main()
