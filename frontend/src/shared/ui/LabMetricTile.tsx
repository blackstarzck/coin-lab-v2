import type { ReactNode } from 'react'
import { Box, Stack, Typography } from '@mui/material'
import { alpha, useTheme } from '@mui/material/styles'

export function LabMetricTile({
  label,
  value,
  hint,
  icon,
}: {
  label: string
  value: ReactNode
  hint?: ReactNode
  icon?: ReactNode
}) {
  const theme = useTheme()

  return (
    <Box
      sx={{
        height: '100%',
        px: 2.2,
        py: 2,
        borderRadius: '12px',
        backgroundColor: theme.palette.surface.low,
        boxShadow: `inset 4px 0 0 ${alpha(theme.palette.primary.main, 0.28)}`,
      }}
    >
      <Stack direction="row" spacing={1.1} alignItems="center" sx={{ mb: 1 }}>
        {icon ? (
          <Box
            sx={{
              width: 28,
              height: 28,
              display: 'grid',
              placeItems: 'center',
              borderRadius: '8px',
              backgroundColor: alpha(theme.palette.primary.main, 0.08),
              color: 'primary.main',
            }}
          >
            {icon}
          </Box>
        ) : null}
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase' }}>
          {label}
        </Typography>
      </Stack>
      <Typography variant="h4" sx={{ fontSize: 32, lineHeight: 1.05, fontVariantNumeric: 'tabular-nums' }}>
        {value}
      </Typography>
      {hint ? (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.9 }}>
          {hint}
        </Typography>
      ) : null}
    </Box>
  )
}
