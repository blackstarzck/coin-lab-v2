import { Box, IconButton, Tooltip, useTheme } from '@mui/material'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Activity,
  Layers,
  FlaskConical,
  GitCompare,
  ScrollText,
  Settings,
} from 'lucide-react'
const NAV_ITEMS = [
  { id: 'dashboard', path: '/', icon: LayoutDashboard, label: '대시보드' },
  { id: 'monitoring', path: '/monitoring', icon: Activity, label: '모니터링' },
  { id: 'strategies', path: '/strategies', icon: Layers, label: '전략' },
  { id: 'backtests', path: '/backtests', icon: FlaskConical, label: '백테스트' },
  { id: 'compare', path: '/compare', icon: GitCompare, label: '비교' },
  { id: 'logs', path: '/logs', icon: ScrollText, label: '로그' },
  { id: 'settings', path: '/settings', icon: Settings, label: '설정' },
]

export function AppShell() {
  const theme = useTheme()
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <Box sx={{ display: 'flex', height: '100vh', overflow: 'hidden', bgcolor: 'bg.canvas' }}>
      {/* Sidebar */}
      <Box
        sx={{
          width: 80,
          flexShrink: 0,
          bgcolor: 'bg.sidebar',
          borderRight: `1px solid ${theme.border.default}`,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          py: 3,
          gap: 1.5,
        }}
      >
        {/* Logo placeholder */}
        <Box
          sx={{
            width: 40,
            height: 40,
            borderRadius: '12px',
            bgcolor: 'rgba(34, 231, 107, 0.14)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            mb: 4,
          }}
        >
          <Activity color={theme.palette.primary.main} size={24} />
        </Box>

        {/* Nav Items */}
        {NAV_ITEMS.map((item) => {
          const isActive = item.path === '/' ? location.pathname === '/' : location.pathname.startsWith(item.path)
          const Icon = item.icon

          return (
            <Tooltip key={item.id} title={item.label} placement="right">
              <IconButton
                onClick={() => navigate(item.path)}
                sx={{
                  width: 40,
                  height: 40,
                  borderRadius: '12px',
                  bgcolor: isActive ? 'primary.main' : 'transparent',
                  color: isActive ? 'background.default' : 'text.tertiary',
                  '&:hover': {
                    bgcolor: isActive
                      ? 'primary.dark'
                      : 'bg.surface2',
                    color: isActive ? 'background.default' : 'text.primary',
                  },
                  transition: 'all 160ms cubic-bezier(0.2, 0.8, 0.2, 1)',
                }}
              >
                <Icon size={20} strokeWidth={isActive ? 2.5 : 2} />
              </IconButton>
            </Tooltip>
          )
        })}
      </Box>

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          height: '100%',
          overflow: 'auto',
          position: 'relative',
          p: 3,
        }}
      >
        <Outlet />
      </Box>
    </Box>
  )
}
