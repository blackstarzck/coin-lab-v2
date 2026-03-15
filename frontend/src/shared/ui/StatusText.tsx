import { Typography } from '@mui/material'
import type { Theme } from '@mui/material/styles'
import type { ReactNode } from 'react'

export type StatusTextTone = 'success' | 'danger' | 'warning' | 'info' | 'default'

interface StatusTextProps {
  children: ReactNode
  tone?: StatusTextTone
  variant?: 'body2' | 'caption'
  fontWeight?: number
}

function getToneColor(theme: Theme, tone: StatusTextTone): string {
  switch (tone) {
    case 'success':
      return theme.palette.status.success
    case 'danger':
      return theme.palette.status.danger
    case 'warning':
      return theme.palette.status.warning
    case 'info':
      return theme.palette.status.info
    default:
      return theme.palette.text.secondary
  }
}

export function StatusText({
  children,
  tone = 'default',
  variant = 'caption',
  fontWeight,
}: StatusTextProps) {
  return (
    <Typography
      component="span"
      variant={variant}
      sx={(theme) => ({
        color: getToneColor(theme, tone),
        ...(fontWeight == null ? {} : { fontWeight }),
        letterSpacing: '-0.01em',
        whiteSpace: 'nowrap',
      })}
    >
      {children}
    </Typography>
  )
}
