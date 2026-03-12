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
      <Box sx={{ p: 3, display: 'flex', flexDirection: 'column', gap: 3 }}>
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
    <Box sx={{ p: 3, display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 600 }}>Settings</Typography>
          <Typography variant="body2" color="text.secondary">
            Runtime and infrastructure settings are read-only in MVP and reflect the current backend state.
          </Typography>
        </Box>
        <Button
          variant={runtimeStatus?.running ? 'outlined' : 'contained'}
          color={runtimeStatus?.running ? 'warning' : 'success'}
          onClick={() => runtimeToggle.mutate(!(runtimeStatus?.running ?? false))}
          disabled={runtimeToggle.isPending}
        >
          {runtimeToggle.isPending ? 'Updating...' : runtimeStatus?.running ? 'Pause Runtime' : 'Start Runtime'}
        </Button>
      </Box>

      <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap>
        <Chip label={`Runtime ${runtimeStatus?.running ? 'ON' : 'OFF'}`} color={runtimeStatus?.running ? 'success' : 'default'} />
        <Chip label={runtimeStatus?.connection_state ?? 'UNKNOWN'} color={runtimeStatus?.connection_state === 'CONNECTED' ? 'success' : 'warning'} variant="outlined" />
        <Chip label={`${runtimeStatus?.running_session_count ?? 0} running sessions`} variant="outlined" />
        <Chip label={`${runtimeStatus?.active_symbols.length ?? 0} active symbols`} variant="outlined" />
      </Stack>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              <Typography variant="h6">Upbit Connection</Typography>
              <StatusRow label="REST Base URL" value={settings?.upbit.rest_base_url ?? '-'} />
              <StatusRow label="Public WS URL" value={settings?.upbit.ws_public_url ?? '-'} />
              <StatusRow label="Private WS URL" value={settings?.upbit.ws_private_url ?? '-'} />
              <StatusRow label="Access Key" value={settings?.upbit.access_key_configured ? 'configured' : 'missing'} />
              <StatusRow label="Secret Key" value={settings?.upbit.secret_key_configured ? 'configured' : 'missing'} />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              <Typography variant="h6">Storage</Typography>
              <StatusRow label="Backend" value={settings?.storage.store_backend ?? '-'} />
              <StatusRow label="Database URL" value={settings?.storage.database_configured ? 'configured' : 'missing'} />
              <StatusRow label="Session Count" value={String(runtimeStatus?.session_count ?? 0)} />
              <StatusRow label="Running Sessions" value={String(runtimeStatus?.running_session_count ?? 0)} />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              <Typography variant="h6">Live Protection</Typography>
              <StatusRow label="Live Trading Enabled" value={settings?.live_protection.live_trading_enabled ? 'true' : 'false'} />
              <StatusRow label="Order Test Required" value={settings?.live_protection.live_require_order_test ? 'true' : 'false'} />
              <StatusRow label="Order Notional KRW" value={String(settings?.live_protection.live_order_notional_krw ?? 0)} />
              <Alert severity={settings?.live_protection.live_trading_enabled ? 'warning' : 'info'}>
                {settings?.live_protection.live_trading_enabled
                  ? 'LIVE mode can place real orders if the user explicitly starts a LIVE session.'
                  : 'LIVE mode is currently blocked by backend policy.'}
              </Alert>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              <Typography variant="h6">Runtime</Typography>
              <StatusRow label="Connection State" value={runtimeStatus?.connection_state ?? '-'} />
              <StatusRow label="Reconnect Count (1h)" value={String(runtimeStatus?.reconnect_count_1h ?? 0)} />
              <StatusRow label="Active Symbols" value={(runtimeStatus?.active_symbols ?? []).join(', ') || '-'} />
              <StatusRow label="Store Backend" value={runtimeStatus?.store_backend ?? '-'} />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>What This Page Covers</Typography>
              <Typography variant="body2" color="text.secondary">
                MVP keeps Settings read-only. The page exposes current Upbit connectivity, storage mode, runtime state, and LIVE safety rails so operators can confirm the environment before launching PAPER or LIVE sessions.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}
