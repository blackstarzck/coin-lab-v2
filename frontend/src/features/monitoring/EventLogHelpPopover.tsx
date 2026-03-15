import { Box, Divider, Popover, Stack, Typography } from '@mui/material'
import { ChevronDown } from 'lucide-react'
import { useState, type MouseEvent } from 'react'

export interface GuideItem {
  label: string
  description: string
}

export interface GuideSection {
  title: string
  items: GuideItem[]
}

const GUIDE_OVERLAY_BG = 'rgba(7, 10, 18, 0.86)'

export const EVENT_LOG_GUIDE_SECTIONS: GuideSection[] = [
  {
    title: '어떻게 읽나',
    items: [
      {
        label: '메시지',
        description: '사람이 빠르게 읽을 수 있도록 적은 설명입니다.',
      },
      {
        label: 'event_type',
        description: '시스템이 기록하는 이벤트 코드입니다. 같은 흐름을 묶어 볼 때 기준이 됩니다.',
      },
    ],
  },
  {
    title: '채널',
    items: [
      {
        label: '전략 실행',
        description: '전략 평가 시작, 완료, 건너뜀, 신호 생성처럼 전략 판단 흐름을 남깁니다.',
      },
      {
        label: '주문 시뮬레이션',
        description: '주문 생성, 체결, 청산 체결처럼 주문 처리 결과를 남깁니다.',
      },
      {
        label: '리스크 제어',
        description: '리스크 규칙 때문에 신호가 차단된 경우를 남깁니다.',
      },
    ],
  },
  {
    title: '레벨',
    items: [
      {
        label: '정보',
        description: '정상 흐름 기록입니다. 평가 완료, 신호 생성, 주문 체결이 여기에 많습니다.',
      },
      {
        label: '경고',
        description: '차단, 건너뜀, 주의가 필요한 상태입니다. 즉시 오류는 아니지만 확인이 필요할 수 있습니다.',
      },
      {
        label: '오류/치명적',
        description: '실행 실패나 즉시 확인이 필요한 상태입니다.',
      },
    ],
  },
  {
    title: '대표 event_type',
    items: [
      {
        label: 'EVALUATION_STARTED',
        description: '새 스냅샷을 기준으로 전략 평가를 시작했다는 뜻입니다.',
      },
      {
        label: 'EVALUATION_COMPLETED',
        description: '전략 평가가 끝났고, 결과는 payload의 decision이나 reason_codes에 함께 남습니다.',
      },
      {
        label: 'EVALUATION_SKIPPED',
        description: '세션 상태나 평가 조건 때문에 이번 평가는 건너뛰었다는 뜻입니다.',
      },
      {
        label: 'SIGNAL_EMITTED',
        description: '전략이 진입 또는 청산 신호를 생성했다는 뜻입니다.',
      },
      {
        label: 'SIGNAL_BLOCKED',
        description: '신호는 있었지만 리스크 규칙에 의해 실행되지 않았다는 뜻입니다.',
      },
      {
        label: 'ORDER_CREATED',
        description: '주문이 생성되었고 아직 체결 전일 수 있다는 뜻입니다.',
      },
      {
        label: 'ORDER_FILLED',
        description: '진입 주문이 체결되었다는 뜻입니다.',
      },
      {
        label: 'EXIT_FILLED',
        description: '청산 주문이 체결되었다는 뜻입니다.',
      },
    ],
  },
]

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
