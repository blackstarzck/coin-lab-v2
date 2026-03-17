import { Box, Typography } from '@mui/material'
import type { RefObject } from 'react'

interface IncrementalTableLoadMoreProps {
  batchSize: number
  visibleCount: number
  totalCount: number
  sentinelRef: RefObject<HTMLDivElement | null>
}

export function IncrementalTableLoadMore({
  batchSize,
  visibleCount,
  totalCount,
  sentinelRef,
}: IncrementalTableLoadMoreProps) {
  if (visibleCount >= totalCount) {
    return null
  }

  return (
    <Box ref={sentinelRef} sx={{ px: 2, py: 1.5 }}>
      <Typography variant="caption" color="text.secondary">
        스크롤하면 {batchSize}개씩 더 표시됩니다. {visibleCount}/{totalCount}
      </Typography>
    </Box>
  )
}
