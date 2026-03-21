import type { ReactNode } from 'react'
import { Box, Stack, Typography } from '@mui/material'

export function LabPageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string
  title: string
  description?: string
  actions?: ReactNode
}) {
  return (
    <Stack
      direction={{ xs: 'column', lg: 'row' }}
      justifyContent="space-between"
      alignItems={{ xs: 'flex-start', lg: 'flex-end' }}
      spacing={2.5}
      sx={{ mb: 3.5 }}
    >
      <Box sx={{ minWidth: 0 }}>
        {eyebrow ? (
          <Typography variant="overline" color="primary.main" sx={{ display: 'block', mb: 1 }}>
            {eyebrow}
          </Typography>
        ) : null}
        <Typography variant="h3">{title}</Typography>
        {description ? (
          <Typography variant="body1" color="text.secondary" sx={{ mt: 1.1, maxWidth: 760 }}>
            {description}
          </Typography>
        ) : null}
      </Box>
      {actions ? <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">{actions}</Stack> : null}
    </Stack>
  )
}
