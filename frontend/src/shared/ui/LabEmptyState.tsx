import { Box, Typography } from '@mui/material'
import { useTheme } from '@mui/material/styles'

export function LabEmptyState({
  message,
  minHeight = 152,
}: {
  message: string
  minHeight?: number
}) {
  const theme = useTheme()

  return (
    <Box
      sx={{
        minHeight,
        display: 'grid',
        placeItems: 'center',
        borderRadius: '10px',
        backgroundColor: theme.palette.surface.sunken,
        color: 'text.secondary',
        px: 2,
        textAlign: 'center',
      }}
    >
      <Typography variant="body2">{message}</Typography>
    </Box>
  )
}
