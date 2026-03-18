import { Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { AppShell } from '@/widgets/layout/AppShell'
import { Box, CircularProgress } from '@mui/material'
import {
  BacktestsPage,
  ComparePage,
  DashboardPage,
  LogsPage,
  MonitoringPage,
  SettingsPage,
  StrategiesPage,
  StrategyDetailPage,
  StrategyEditPage,
} from '@/app/routeLoaders'

function LoadingFallback() {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
      <CircularProgress color="primary" />
    </Box>
  )
}

export function App() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <Routes>
        <Route path="/" element={<AppShell />}>
          <Route index element={<DashboardPage />} />
          <Route path="monitoring" element={<MonitoringPage />} />
          <Route path="strategies" element={<StrategiesPage />} />
          <Route path="strategies/new" element={<StrategyEditPage />} />
          <Route path="strategies/:id" element={<StrategyDetailPage />} />
          <Route path="strategies/:id/edit" element={<StrategyEditPage />} />
          <Route path="backtests" element={<BacktestsPage />} />
          <Route path="compare" element={<ComparePage />} />
          <Route path="logs" element={<LogsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </Suspense>
  )
}
