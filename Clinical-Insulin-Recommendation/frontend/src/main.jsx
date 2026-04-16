/**
 * GlucoSense SPA entry: Router + global ClinicalProvider (session, theme, patients, API gate data).
 * API calls use relative /api (Vite dev server proxies to FastAPI :8000).
 */
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ClinicalProvider } from './context/ClinicalContext'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <ClinicalProvider>
        <App />
      </ClinicalProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
