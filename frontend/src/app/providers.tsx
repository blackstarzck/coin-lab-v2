import type { ReactNode } from 'react'
import { BrowserRouter } from 'react-router-dom'
import { ThemeProvider, CssBaseline } from '@mui/material'
import { QueryClientProvider } from '@tanstack/react-query'
import { MonitoringSummaryStreamProvider } from '@/features/monitoring/useMonitoringSummaryStream'
import { queryClient } from '@/shared/query/client'
import { theme } from '@/theme/theme'

interface AppProvidersProps {
  children: ReactNode
}

export function AppProviders({ children }: AppProvidersProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <MonitoringSummaryStreamProvider>
          <BrowserRouter>
            {children}
          </BrowserRouter>
        </MonitoringSummaryStreamProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
