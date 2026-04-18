import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ClinicalProvider } from './context/ClinicalContext'
import ErrorBoundary from './ErrorBoundary'
import App from './App'
import './index.css'

const rootEl = document.getElementById('root')
if (!rootEl) {
  throw new Error('Missing #root element')
}

ReactDOM.createRoot(rootEl).render(
  <React.StrictMode>
    <ErrorBoundary>
      <BrowserRouter
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <ClinicalProvider>
          <App />
        </ClinicalProvider>
      </BrowserRouter>
    </ErrorBoundary>
  </React.StrictMode>,
)
