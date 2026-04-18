/**
 * k6 load test — Clinical POST /api/recommend
 *
 * Install: https://k6.io/docs/get-started/installation/
 * Run (with API running on localhost:8000, auth OFF):
 *   k6 run scripts/loadtest/k6-clinical-recommend.js
 *
 * With auth (production-like):
 *   K6_JWT="eyJ..." k6 run -e BASE_URL=https://your-api.example.com scripts/loadtest/k6-clinical-recommend.js
 */
import http from 'k6/http'
import { check, sleep } from 'k6'

export const options = {
  stages: [
    { duration: '30s', target: 50 },
    { duration: '1m', target: 100 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.05'],
    http_req_duration: ['p(95)<5000'],
  },
}

const BASE = __ENV.BASE_URL || 'http://127.0.0.1:8000'
const JWT = __ENV.K6_JWT || ''

const body = JSON.stringify({
  age: 45,
  gender: 'Female',
  food_intake: 'Medium',
  previous_medications: 'None',
  glucose_level: 140,
  BMI: 26,
  HbA1c: 7.0,
  weight: 72,
})

export default function () {
  const headers = { 'Content-Type': 'application/json' }
  if (JWT) headers.Authorization = `Bearer ${JWT}`
  const res = http.post(`${BASE}/api/recommend`, body, { headers })
  check(res, { 'status 200 or 503': (r) => r.status === 200 || r.status === 503 })
  sleep(0.3)
}
