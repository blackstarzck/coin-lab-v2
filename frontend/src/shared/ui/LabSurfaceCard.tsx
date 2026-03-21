import type { ReactNode } from 'react'
import { Box, Card, CardContent, Stack, Typography } from '@mui/material'
import { alpha, useTheme } from '@mui/material/styles'
import type { SxProps, Theme } from '@mui/material/styles'

export function LabSurfaceCard({
  title,
  subtitle,
  action,
  children,
  variant = 'container',
  sx,
  contentSx,
  bodySx,
  headerDivider = true,
  dataTestId,
}: {
  title?: string
  subtitle?: string
  action?: ReactNode
  children: ReactNode
  variant?: 'low' | 'container' | 'high' | 'glass' | 'sunken'
  sx?: SxProps<Theme>
  contentSx?: SxProps<Theme>
  bodySx?: SxProps<Theme>
  headerDivider?: boolean
  dataTestId?: string
}) {
  const theme = useTheme()
  const surfaceStyles = {
    low: {
      backgroundColor: theme.palette.surface.low,
      border: `1px solid ${theme.palette.border.soft}`,
      backdropFilter: 'none',
      boxShadow: 'none',
    },
    container: {
      backgroundColor: theme.palette.surface.container,
      border: `1px solid ${theme.palette.border.soft}`,
      backdropFilter: 'none',
      boxShadow: 'none',
    },
    high: {
      backgroundColor: theme.palette.surface.high,
      border: `1px solid ${theme.palette.border.default}`,
      backdropFilter: 'none',
      boxShadow: 'none',
    },
    glass: {
      backgroundColor: theme.palette.surface.glass,
      border: `1px solid ${theme.palette.border.soft}`,
      backdropFilter: 'blur(20px)',
      boxShadow: `0 24px 48px ${alpha('#000000', 0.38)}`,
    },
    sunken: {
      backgroundColor: theme.palette.surface.sunken,
      border: `1px solid ${theme.palette.border.soft}`,
      backdropFilter: 'none',
      boxShadow: `inset 0 0 0 1px ${alpha(theme.palette.common.black, 0.18)}`,
    },
  }[variant]

  return (
    <Card
      data-testid={dataTestId}
      sx={[
        {
          height: '100%',
          borderRadius: '12px',
          background:
            variant === 'glass'
              ? `linear-gradient(180deg, ${alpha(theme.palette.common.white, 0.02)} 0%, ${alpha(theme.palette.common.white, 0.01)} 100%)`
              : 'none',
          overflow: 'hidden',
          ...surfaceStyles,
        },
        ...(Array.isArray(sx) ? sx : sx ? [sx] : []),
      ]}
    >
      <CardContent
        sx={[
          {
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            p: { xs: 2, md: 2.5 },
            '&:last-child': {
              pb: { xs: 2, md: 2.5 },
            },
          },
          ...(Array.isArray(contentSx) ? contentSx : contentSx ? [contentSx] : []),
        ]}
      >
        {title || subtitle || action ? (
          <Box
            sx={{
              pb: headerDivider ? 1.8 : 0,
              mb: headerDivider ? 1.8 : 0,
              borderBottom: headerDivider ? `1px solid ${theme.palette.border.soft}` : 'none',
            }}
          >
            <Stack
              direction={{ xs: 'column', md: 'row' }}
              spacing={1}
              justifyContent="space-between"
              alignItems={{ xs: 'flex-start', md: 'center' }}
            >
              <Box>
                {title ? <Typography variant="h6">{title}</Typography> : null}
                {subtitle ? (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.45, maxWidth: 760 }}>
                    {subtitle}
                  </Typography>
                ) : null}
              </Box>
              {action}
            </Stack>
          </Box>
        ) : null}
        <Box
          sx={[
            {
              flex: 1,
              minHeight: 0,
            },
            ...(Array.isArray(bodySx) ? bodySx : bodySx ? [bodySx] : []),
          ]}
        >
          {children}
        </Box>
      </CardContent>
    </Card>
  )
}
