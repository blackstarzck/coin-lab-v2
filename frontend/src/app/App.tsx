import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { AppShell } from '@/widgets/layout/AppShell'
import { Box, CircularProgress } from '@mui/material'

const DashboardPage = lazy(() => import('@/pages/DashboardPage'))
const MonitoringPage = lazy(() => import('@/pages/MonitoringPage'))
const StrategiesPage = lazy(() => import('@/pages/StrategiesPage'))
const StrategyDetailPage = lazy(() => import('@/pages/StrategyDetailPage'))
const StrategyEditPage = lazy(() => import('@/pages/StrategyEditPage'))
const BacktestsPage = lazy(() => import('@/pages/BacktestsPage'))
const ComparePage = lazy(() => import('@/pages/ComparePage'))
const LogsPage = lazy(() => import('@/pages/LogsPage'))
const SettingsPage = lazy(() => import('@/pages/SettingsPage'))

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
