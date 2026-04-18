import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  // Allow VITE_* and MEAL_* so .env can use MEAL_PLAN_API_URL (docs) or VITE_MEAL_PLAN_API_URL.
  envPrefix: ['VITE_', 'MEAL_'],
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    exclude: ['**/node_modules/**', '**/e2e/**', '**/dist/**'],
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          recharts: ['recharts'],
          'jspdf-vendor': ['jspdf', 'jspdf-autotable'],
        },
      },
    },
  },
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': {
        target: `http://${process.env.GLUCOSENSE_API_HOST || '127.0.0.1'}:${process.env.GLUCOSENSE_API_PORT || 8000}`,
        changeOrigin: true,
        secure: false,
      },
      '/static': {
        target: `http://${process.env.GLUCOSENSE_API_HOST || '127.0.0.1'}:${process.env.GLUCOSENSE_API_PORT || 8000}`,
        changeOrigin: true,
        secure: false,
      },
    },
  },
})
