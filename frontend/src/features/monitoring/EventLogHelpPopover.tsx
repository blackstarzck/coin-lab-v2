import { Box, Button, Divider, Popover, Stack, Typography } from '@mui/material'
import { Info } from 'lucide-react'
import { useState, type MouseEvent } from 'react'

interface EventLogHelpPopoverProps {
  active?: boolean
}

interface GuideItem {
  label: string
  description: string
}

interface GuideSection {
  title: string
  items: GuideItem[]
}

const GUIDE_SECTIONS: GuideSection[] = [
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

export function EventLogHelpPopover({ active = false }: EventLogHelpPopoverProps) {
  const [anchorEl, setAnchorEl] = useState<HTMLButtonElement | null>(null)

  const handleOpen = (event: MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget)
  }

  const handleClose = () => {
    setAnchorEl(null)
  }

  const open = Boolean(anchorEl)

  return (
    <>
      <Button
        size="small"
        variant="text"
        onClick={handleOpen}
        sx={{
          minWidth: 0,
          px: 0,
          py: 0,
          fontSize: 12,
          fontWeight: 500,
          color: active ? '#d0b06f' : '#8b96aa',
          textTransform: 'none',
          alignSelf: 'flex-start',
          gap: 0.75,
          '&:hover': {
            backgroundColor: 'transparent',
            color: active ? '#dfbe7a' : '#a2aec4',
          },
        }}
      >
        <Info size={14} strokeWidth={2.1} />
        로그 설명
      </Button>
      <Popover
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
        PaperProps={{
          sx: {
            mt: 1,
            width: 380,
            maxWidth: 'calc(100vw - 32px)',
            maxHeight: 520,
            overflowY: 'auto',
            p: 2,
            color: '#e7edf7',
            bgcolor: 'rgba(7, 10, 18, 0.86)',
            backgroundImage: 'none',
            backdropFilter: 'blur(18px)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            boxShadow: '0 24px 48px rgba(0, 0, 0, 0.42)',
          },
        }}
      >
        <Stack spacing={1.5}>
          <Box>
            <Typography variant="subtitle2" fontWeight={600} sx={{ color: '#f4f7fb' }}>
              이벤트 로그 설명
            </Typography>
            <Typography variant="caption" sx={{ color: 'rgba(222, 230, 242, 0.72)' }}>
              채널, 레벨, 이벤트 코드를 함께 보면 로그 의미를 빠르게 파악할 수 있습니다.
            </Typography>
          </Box>

          {GUIDE_SECTIONS.map((section, index) => (
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
                      display: 'grid',
                      gridTemplateColumns: 'minmax(0, 128px) minmax(0, 1fr)',
                      gap: 1.25,
                      alignItems: 'start',
                    }}
                  >
                    <Typography
                      variant="caption"
                      sx={{
                        color: '#f2f5fa',
                        lineHeight: 1.55,
                        overflowWrap: 'anywhere',
                        wordBreak: 'break-word',
                        ...(section.title === '대표 event_type'
                          ? {
                              fontFamily: 'Consolas, "SFMono-Regular", Menlo, monospace',
                              fontSize: 11,
                              letterSpacing: '-0.01em',
                            }
                          : null),
                      }}
                    >
                      {item.label}
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'rgba(222, 230, 242, 0.72)', lineHeight: 1.55 }}>
                      {item.description}
                    </Typography>
                  </Box>
                ))}
              </Stack>
            </Stack>
          ))}

          <Typography variant="caption" sx={{ color: 'rgba(222, 230, 242, 0.66)', lineHeight: 1.55 }}>
            로그 코드는 버전에 따라 조금 달라질 수 있습니다. 해석할 때는 채널과 메시지도 함께 보세요.
          </Typography>
        </Stack>
      </Popover>
    </>
  )
}
