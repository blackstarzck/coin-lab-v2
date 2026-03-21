import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  Skeleton,
  Stack,
  Typography,
} from '@mui/material'

import { useRuntimeSettings, useRuntimeStatus, useRuntimeToggle } from '@/features/system/api'
import { translateConnectionState } from '@/shared/lib/i18n'
import { LabPageHeader } from '@/shared/ui/LabPageHeader'

function StatusRow({ label, value }: { label: string, value: string }) {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2 }}>
      <Typography variant="body2" color="text.secondary">{label}</Typography>
      <Typography variant="body2" sx={{ fontFamily: 'monospace', textAlign: 'right' }}>{value}</Typography>
    </Box>
  )
}

export default function SettingsPage() {
  const { data: runtimeStatus, isLoading: isLoadingStatus } = useRuntimeStatus()
  const { data: settings, isLoading: isLoadingSettings } = useRuntimeSettings()
  const runtimeToggle = useRuntimeToggle()

  if (isLoadingStatus || isLoadingSettings) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        <Skeleton variant="text" width={200} height={48} />
        <Grid container spacing={3}>
          {Array.from({ length: 6 }).map((_, index) => (
            <Grid item xs={12} md={6} key={index}>
              <Skeleton variant="rounded" height={220} />
            </Grid>
          ))}
        </Grid>
      </Box>
    )
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <LabPageHeader
        eyebrow="CONTROL ROOM"
        title="설정"
        description="런타임과 인프라 상태를 읽고 실전 보호 설정을 확인합니다."
        actions={(
          <Button
            variant={runtimeStatus?.running ? 'outlined' : 'contained'}
            color={runtimeStatus?.running ? 'warning' : 'success'}
            onClick={() => runtimeToggle.mutate(!(runtimeStatus?.running ?? false))}
            disabled={runtimeToggle.isPending}
          >
            {runtimeToggle.isPending ? '업데이트 중...' : runtimeStatus?.running ? '런타임 일시정지' : '런타임 시작'}
          </Button>
        )}
      />

      <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap>
        <Chip label={`런타임 ${runtimeStatus?.running ? '켜짐' : '꺼짐'}`} color={runtimeStatus?.running ? 'success' : 'default'} />
        <Chip label={translateConnectionState(runtimeStatus?.connection_state ?? 'UNKNOWN')} color={runtimeStatus?.connection_state === 'CONNECTED' ? 'success' : 'warning'} variant="outlined" />
        <Chip label={`실행 중 세션 ${runtimeStatus?.running_session_count ?? 0}개`} variant="outlined" />
        <Chip label={`활성 심볼 ${(runtimeStatus?.active_symbols ?? []).length}개`} variant="outlined" />
      </Stack>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              <Typography variant="h6">업비트 연결</Typography>
              <StatusRow label="REST 기본 URL" value={settings?.upbit.rest_base_url ?? '-'} />
              <StatusRow label="공용 WS URL" value={settings?.upbit.ws_public_url ?? '-'} />
              <StatusRow label="개인 WS URL" value={settings?.upbit.ws_private_url ?? '-'} />
              <StatusRow label="액세스 키" value={settings?.upbit.access_key_configured ? '설정됨' : '없음'} />
              <StatusRow label="시크릿 키" value={settings?.upbit.secret_key_configured ? '설정됨' : '없음'} />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              <Typography variant="h6">저장소</Typography>
              <StatusRow label="백엔드" value={settings?.storage.store_backend ?? '-'} />
              <StatusRow label="데이터베이스 URL" value={settings?.storage.database_configured ? '설정됨' : '없음'} />
              <StatusRow label="세션 수" value={String(runtimeStatus?.session_count ?? 0)} />
              <StatusRow label="실행 중 세션" value={String(runtimeStatus?.running_session_count ?? 0)} />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              <Typography variant="h6">실전 보호</Typography>
              <StatusRow label="실전 거래 허용" value={settings?.live_protection.live_trading_enabled ? '예' : '아니오'} />
              <StatusRow label="주문 테스트 필요" value={settings?.live_protection.live_require_order_test ? '예' : '아니오'} />
              <StatusRow label="주문 기준 금액(KRW)" value={String(settings?.live_protection.live_order_notional_krw ?? 0)} />
              <Alert severity={settings?.live_protection.live_trading_enabled ? 'warning' : 'info'}>
                {settings?.live_protection.live_trading_enabled
                  ? '사용자가 실전 세션을 명시적으로 시작하면 실제 주문이 실행될 수 있습니다.'
                  : '현재 백엔드 정책에 따라 실전 모드는 차단되어 있습니다.'}
              </Alert>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              <Typography variant="h6">런타임</Typography>
              <StatusRow label="연결 상태" value={translateConnectionState(runtimeStatus?.connection_state ?? '-')} />
              <StatusRow label="재연결 횟수(1시간)" value={String(runtimeStatus?.reconnect_count_1h ?? 0)} />
              <StatusRow label="활성 심볼" value={(runtimeStatus?.active_symbols ?? []).join(', ') || '-'} />
              <StatusRow label="저장소 백엔드" value={runtimeStatus?.store_backend ?? '-'} />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>이 페이지에서 확인하는 항목</Typography>
              <Typography variant="body2" color="text.secondary">
                설정 페이지는 현재 업비트 연결 상태, 저장소 모드, 런타임 상태, 실전 안전 장치를 보여줍니다. 운영자는 이를 통해 모의 세션이나 실전 세션을 시작하기 전에 환경을 점검할 수 있습니다.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}
