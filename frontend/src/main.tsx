import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { AppProviders } from './app/providers'
import { App } from './app/App'
import 'odometer/themes/odometer-theme-minimal.css'
import './index.css'

const app = (
  <AppProviders>
    <App />
  </AppProviders>
)

createRoot(document.getElementById('root')!).render(
  import.meta.env.DEV ? app : <StrictMode>{app}</StrictMode>,
)
