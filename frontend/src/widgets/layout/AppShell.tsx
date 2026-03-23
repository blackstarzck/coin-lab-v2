import type { ReactNode } from 'react'
import { Box, Button, Stack, Typography } from '@mui/material'
import { alpha, useTheme } from '@mui/material/styles'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import {
  Activity,
  Bell,
  FlaskConical,
  GitCompare,
  Layers,
  LayoutDashboard,
  Radio,
  ScrollText,
  Settings,
  UserCircle2,
} from 'lucide-react'

const TOP_NAV = [
  { path: '/', label: 'Dashboard' },
  { path: '/monitoring', label: 'Monitoring' },
  { path: '/strategies', label: 'Strategies' },
  { path: '/backtests', label: 'Markets' },
] as const

const SIDE_NAV = [
  { id: 'dashboard', path: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { id: 'monitoring', path: '/monitoring', icon: Activity, label: 'Monitoring' },
  { id: 'strategies', path: '/strategies', icon: Layers, label: 'Strategies' },
  { id: 'backtests', path: '/backtests', icon: FlaskConical, label: 'Backtests' },
  { id: 'compare', path: '/compare', icon: GitCompare, label: 'Compare' },
  { id: 'logs', path: '/logs', icon: ScrollText, label: 'Logs' },
  { id: 'settings', path: '/settings', icon: Settings, label: 'Settings' },
] as const

function isCurrent(pathname: string, path: string) {
  return path === '/' ? pathname === '/' : pathname.startsWith(path)
}

export function AppShell() {
  const theme = useTheme()
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <Box
      sx={{
        minHeight: '100vh',
        color: 'text.primary',
        background:
          `radial-gradient(circle at top right, ${alpha(theme.palette.primary.main, 0.08)} 0%, transparent 22%),` +
          `radial-gradient(circle at 0% 0%, ${alpha(theme.palette.secondary.main, 0.06)} 0%, transparent 18%),` +
          theme.palette.surface.base,
      }}
    >
      <Box
        component="header"
        sx={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          zIndex: 50,
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          px: { xs: 2, md: 3 },
          backgroundColor: alpha(theme.palette.surface.base, 0.92),
          backdropFilter: 'blur(18px)',
        }}
      >
        <Stack direction="row" spacing={4} alignItems="center">
          <Stack direction="row" spacing={1.25} alignItems="center">
            <Typography
              variant="h6"
              sx={{
                fontSize: 24,
                color: 'text.primary',
                letterSpacing: '-0.04em',
                cursor: 'pointer',
              }}
              onClick={() => navigate('/')}
            >
              COIN LAB
            </Typography>
            <Box
              sx={{
                px: 1,
                py: 0.35,
                borderRadius: '999px',
                border: `1px solid ${alpha(theme.palette.primary.main, 0.35)}`,
                backgroundColor: alpha(theme.palette.primary.main, 0.08),
              }}
            >
              <Typography
                variant="caption"
                sx={{
                  display: 'block',
                  color: 'primary.main',
                  fontWeight: 700,
                  letterSpacing: '0.04em',
                }}
              >
                DEPLOY TEST 0323
              </Typography>
            </Box>
          </Stack>
          <Stack direction="row" spacing={2.5} sx={{ display: { xs: 'none', md: 'flex' } }}>
            {TOP_NAV.map((item) => (
              <Box
                key={item.path}
                onClick={() => navigate(item.path)}
                sx={{
                  cursor: 'pointer',
                  color: isCurrent(location.pathname, item.path) ? 'primary.main' : 'text.secondary',
                  borderBottom: isCurrent(location.pathname, item.path) ? `2px solid ${theme.palette.primary.main}` : '2px solid transparent',
                  pb: 0.6,
                  fontFamily: theme.typography.h6.fontFamily,
                  fontSize: 13,
                  fontWeight: 700,
                  letterSpacing: '-0.01em',
                  transition: `color ${theme.motion.quick}`,
                  '&:hover': {
                    color: 'text.primary',
                  },
                }}
              >
                {item.label}
              </Box>
            ))}
          </Stack>
        </Stack>

        <Stack direction="row" spacing={1.25} alignItems="center">
          <Button
            variant="contained"
            size="small"
            onClick={() => navigate('/monitoring')}
            sx={{ px: 1.8, minHeight: 34 }}
          >
            Open Monitoring
          </Button>
          <HeaderIcon><Radio size={15} /></HeaderIcon>
          <HeaderIcon><Bell size={15} /></HeaderIcon>
          <HeaderIcon><UserCircle2 size={16} /></HeaderIcon>
        </Stack>
      </Box>

      <Box
        component="aside"
        sx={{
          position: 'fixed',
          top: 64,
          left: 0,
          bottom: 0,
          zIndex: 40,
          width: { xs: 72, md: 80 },
          '&:hover': {
            width: { md: 220 },
            '& .lab-nav-label': {
              opacity: 1,
            },
          },
          backgroundColor: alpha(theme.palette.surface.base, 0.76),
          backdropFilter: 'blur(20px)',
          borderRight: `1px solid ${theme.palette.border.soft}`,
          transition: `width ${theme.motion.regular}`,
          overflow: 'hidden',
        }}
      >
        <Stack sx={{ height: '100%', px: 1.5, py: 2 }} spacing={1.2}>
          <Box
            sx={{
              width: 44,
              height: 44,
              borderRadius: '999px',
              backgroundColor: theme.palette.surface.high,
              display: 'grid',
              placeItems: 'center',
              color: 'primary.main',
            }}
          >
            <UserCircle2 size={18} />
          </Box>

          <Stack spacing={1}>
            {SIDE_NAV.map((item) => {
              const Icon = item.icon
              const active = isCurrent(location.pathname, item.path)
              return (
                <Box
                  key={item.id}
                  onClick={() => navigate(item.path)}
                  sx={{
                    height: 44,
                    px: 1.2,
                    borderRadius: '10px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1.5,
                    cursor: 'pointer',
                    color: active ? 'text.primary' : 'text.tertiary',
                    backgroundColor: active ? theme.palette.surface.container : 'transparent',
                    transition: `background-color ${theme.motion.quick}, color ${theme.motion.quick}`,
                    '&:hover': {
                      backgroundColor: theme.palette.surface.container,
                      color: 'text.primary',
                    },
                  }}
                >
                  <Box sx={{ minWidth: 20, display: 'grid', placeItems: 'center', color: active ? 'primary.main' : 'inherit' }}>
                    <Icon size={16} />
                  </Box>
                  <Typography
                    className="lab-nav-label"
                    variant="body2"
                    sx={{
                      opacity: { xs: 0, md: 0 },
                      whiteSpace: 'nowrap',
                      transition: `opacity ${theme.motion.quick}`,
                      fontFamily: theme.typography.subtitle1.fontFamily,
                      fontWeight: 700,
                    }}
                  >
                    {item.label}
                  </Typography>
                </Box>
              )
            })}
          </Stack>
        </Stack>
      </Box>

      <Box
        component="main"
        sx={{
          minHeight: '100vh',
          ml: { xs: '72px', md: '80px' },
          pt: '88px',
          px: { xs: 2, md: 4 },
          pb: 5,
        }}
      >
        <Outlet />
      </Box>
    </Box>
  )
}

function HeaderIcon({ children }: { children: ReactNode }) {
  const theme = useTheme()

  return (
    <Box
      sx={{
        width: 32,
        height: 32,
        borderRadius: '999px',
        display: 'grid',
        placeItems: 'center',
        color: 'text.secondary',
        cursor: 'pointer',
        transition: `background-color ${theme.motion.quick}, color ${theme.motion.quick}`,
        '&:hover': {
          backgroundColor: alpha(theme.palette.surface.high, 0.95),
          color: 'primary.main',
        },
      }}
    >
      {children}
    </Box>
  )
}
