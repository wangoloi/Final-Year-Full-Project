/**
 * k6 — Meal Plan API GET /health (no auth)
 *   k6 run scripts/loadtest/k6-meal-health.js
 */
import http from 'k6/http'
import { check, sleep } from 'k6'

export const options = {
  vus: 100,
  duration: '1m',
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<800'],
  },
}

const BASE = __ENV.MEAL_API_URL || 'http://127.0.0.1:8001'

export default function () {
  const res = http.get(`${BASE}/health`)
  check(res, { 'status 200': (r) => r.status === 200 })
  sleep(0.05)
}
