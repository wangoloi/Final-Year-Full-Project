import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

/**
 * GlucoSense uses :8000. Integrated dev runs Meal Plan FastAPI on :8001 (default below).
 * Meal-only dev (API on :8000): `set MEAL_PLAN_API_PROXY=http://127.0.0.1:8000` then `npm run dev`.
 */
const mealApiProxy = process.env.MEAL_PLAN_API_PROXY || 'http://127.0.0.1:8001';

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5174,
    strictPort: true,
    proxy: {
      '/api': {
        target: mealApiProxy,
        changeOrigin: true,
        timeout: 60_000,
        proxyTimeout: 60_000,
        configure(proxy) {
          proxy.on('error', (err) => {
            console.error(`[vite] /api proxy → ${mealApiProxy} failed:`, err?.message || err);
          });
        },
      },
    },
  },
});
