import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  /** Meal Plan FastAPI (auth, meals, chat). Must not hit the clinical API on :8000. */
  const mealPlanApi =
    env.MEAL_PLAN_API_PROXY || env.VITE_MEAL_PLAN_API_URL || 'http://127.0.0.1:8001'
  const clinicalApi = env.CLINICAL_API_PROXY || 'http://127.0.0.1:8000'

  return {
    plugins: [react()],
    server: {
      host: true,
      port: 5173,
      proxy: {
        // More specific first: GlucoSense UI must not send /api/auth/* to the clinical backend.
        '/api/auth': {
          target: mealPlanApi,
          changeOrigin: true,
          secure: false,
        },
        '/api': {
          target: clinicalApi,
          changeOrigin: true,
          secure: false,
        },
        '/static': {
          target: clinicalApi,
          changeOrigin: true,
          secure: false,
        },
      },
    },
  }
})
