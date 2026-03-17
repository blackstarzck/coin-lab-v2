import { Stack, Typography } from '@mui/material'

import { formatDate, formatTime } from '@/shared/lib/i18n'

interface TwoLineDateTimeProps {
  value: string | Date | null | undefined
  emptyText?: string
}

export function TwoLineDateTime({
  value,
  emptyText = '-',
}: TwoLineDateTimeProps) {
  if (!value) {
    return (
      <Typography variant="caption" color="text.secondary">
        {emptyText}
      </Typography>
    )
  }

  return (
    <Stack spacing={0} sx={{ color: 'text.secondary', lineHeight: 1.2 }}>
      <Typography variant="caption" color="inherit" sx={{ fontVariantNumeric: 'tabular-nums' }}>
        {formatDate(value)}
      </Typography>
      <Typography variant="caption" color="inherit" sx={{ fontVariantNumeric: 'tabular-nums' }}>
        {formatTime(value)}
      </Typography>
    </Stack>
  )
}
