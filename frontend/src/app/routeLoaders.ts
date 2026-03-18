import { lazy } from 'react'

const loadDashboardPage = () => import('@/pages/DashboardPage')
const loadMonitoringPage = () => import('@/pages/MonitoringPage')
const loadStrategiesPage = () => import('@/pages/StrategiesPage')
const loadStrategyDetailPage = () => import('@/pages/StrategyDetailPage')
const loadStrategyEditPage = () => import('@/pages/StrategyEditPage')
const loadBacktestsPage = () => import('@/pages/BacktestsPage')
const loadComparePage = () => import('@/pages/ComparePage')
const loadLogsPage = () => import('@/pages/LogsPage')
const loadSettingsPage = () => import('@/pages/SettingsPage')

export const DashboardPage = lazy(loadDashboardPage)
export const MonitoringPage = lazy(loadMonitoringPage)
export const StrategiesPage = lazy(loadStrategiesPage)
export const StrategyDetailPage = lazy(loadStrategyDetailPage)
export const StrategyEditPage = lazy(loadStrategyEditPage)
export const BacktestsPage = lazy(loadBacktestsPage)
export const ComparePage = lazy(loadComparePage)
export const LogsPage = lazy(loadLogsPage)
export const SettingsPage = lazy(loadSettingsPage)

export function preloadStrategyEditPage() {
  return loadStrategyEditPage()
}
