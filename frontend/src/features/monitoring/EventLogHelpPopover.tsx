import { Box, Divider, Popover, Stack, Typography } from '@mui/material'
import { ChevronDown } from 'lucide-react'
import { useState, type MouseEvent } from 'react'
import type { GuideSection } from './eventLogGuide'

const GUIDE_OVERLAY_BG = 'rgba(7, 10, 18, 0.86)'

interface DetailGuidePopoverProps {
  summary: string
  sections: GuideSection[]
  footnote?: string
}

export function DetailGuidePopover({
  summary,
  sections,
  footnote,
}: DetailGuidePopoverProps) {
  const [anchorEl, setAnchorEl] = useState<HTMLButtonElement | null>(null)

  const handleOpen = (event: MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget)
  }

  const handleClose = () => {
    setAnchorEl(null)
  }

  const open = Boolean(anchorEl)

  return (
    <Box
      sx={{
        px: 2,
        py: 1.25,
        borderBottom: '1px solid',
        borderColor: 'divider',
        bgcolor: 'rgba(15, 23, 42, 0.34)',
      }}
    >
      <Box
        component="button"
        type="button"
        onClick={handleOpen}
        sx={{
          display: 'flex',
          width: '100%',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 1.5,
          border: 0,
          p: 0,
          bgcolor: 'transparent',
          color: 'inherit',
          textAlign: 'left',
          cursor: 'pointer',
        }}
      >
        <Typography
          variant="caption"
          sx={{
            color: 'rgba(222, 230, 242, 0.72)',
            lineHeight: 1.55,
          }}
        >
          {summary}
        </Typography>
        <Box
          sx={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            color: '#8b96aa',
          }}
        >
          <ChevronDown size={16} strokeWidth={2} />
        </Box>
      </Box>

      <Popover
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
        PaperProps={{
          sx: {
            mt: 1,
            width: 'max-content',
            minWidth: 420,
            maxWidth: 'min(680px, calc(100vw - 32px))',
            maxHeight: 520,
            overflowY: 'auto',
            p: 2,
            color: '#e7edf7',
            bgcolor: GUIDE_OVERLAY_BG,
            backgroundImage: 'none',
            backdropFilter: 'blur(18px)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            boxShadow: '0 24px 48px rgba(0, 0, 0, 0.42)',
          },
        }}
      >
        <Stack spacing={1.5}>
          <Typography variant="caption" sx={{ color: 'rgba(222, 230, 242, 0.72)', lineHeight: 1.55 }}>
            {summary}
          </Typography>

          {sections.map((section, index) => (
            <Stack key={section.title} spacing={1}>
              {index > 0 ? <Divider flexItem sx={{ borderColor: 'rgba(255, 255, 255, 0.08)' }} /> : null}
              <Typography variant="caption" sx={{ color: 'rgba(208, 219, 235, 0.62)', letterSpacing: '0.02em' }}>
                {section.title}
              </Typography>
              <Stack spacing={0.9}>
                {section.items.map((item) => (
                  <Box
                    key={`${section.title}-${item.label}`}
                    sx={{
                      display: 'flex',
                      gap: 1.5,
                      alignItems: 'flex-start',
                      maxWidth: '100%',
                    }}
                  >
                    <Box
                      sx={{
                        minWidth: section.title.includes('event_type') ? 176 : 112,
                        flexShrink: 0,
                      }}
                    >
                      <Typography
                        variant="caption"
                        sx={{
                          color: '#f2f5fa',
                          lineHeight: 1.55,
                          overflowWrap: 'anywhere',
                          wordBreak: 'break-word',
                          ...(section.title.includes('event_type')
                            ? {
                                fontFamily: 'Consolas, "SFMono-Regular", Menlo, monospace',
                                letterSpacing: '-0.01em',
                              }
                            : null),
                        }}
                      >
                        {item.label}
                      </Typography>
                    </Box>
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Typography variant="caption" sx={{ color: 'rgba(222, 230, 242, 0.72)', lineHeight: 1.55 }}>
                        {item.description}
                      </Typography>
                    </Box>
                  </Box>
                ))}
              </Stack>
            </Stack>
          ))}

          {footnote ? (
            <Typography variant="caption" sx={{ color: 'rgba(222, 230, 242, 0.66)', lineHeight: 1.55 }}>
              {footnote}
            </Typography>
          ) : null}
        </Stack>
      </Popover>
    </Box>
  )
}
