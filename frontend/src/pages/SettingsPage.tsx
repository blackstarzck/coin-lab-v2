import { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  TextField,
  Select,
  MenuItem,
  Button,
  Switch,
  FormControlLabel,
  InputLabel,
  FormControl,
  Alert,
  Snackbar,
} from '@mui/material'

export default function SettingsPage() {
  const [toastOpen, setToastOpen] = useState(false)

  const handleSave = () => {
    setToastOpen(true)
  }

  return (
    <Box sx={{ p: 3, display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Typography variant="h4" sx={{ fontWeight: 600 }}>
        Settings
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Typography variant="h6">Upbit Connection</Typography>
              <TextField label="API Key" type="password" fullWidth defaultValue="************************" />
              <TextField label="Secret Key" type="password" fullWidth defaultValue="************************" />
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mt: 1 }}>
                <Typography variant="body2" color="status.success">Connected successfully</Typography>
                <Button variant="outlined" size="small">Test Connection</Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Typography variant="h6">Storage</Typography>
              <TextField label="Database URL" fullWidth defaultValue="postgresql://user:pass@localhost:5432/coinlab" />
              <FormControl fullWidth>
                <InputLabel>Storage Mode</InputLabel>
                <Select label="Storage Mode" defaultValue="postgres">
                  <MenuItem value="memory">In-Memory (Fast, Volatile)</MenuItem>
                  <MenuItem value="postgres">PostgreSQL (Persistent)</MenuItem>
                </Select>
              </FormControl>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Typography variant="h6">Universe Policy</Typography>
              <FormControl fullWidth>
                <InputLabel>Mode</InputLabel>
                <Select label="Mode" defaultValue="dynamic">
                  <MenuItem value="dynamic">Dynamic (Auto-update)</MenuItem>
                  <MenuItem value="static">Static (Fixed list)</MenuItem>
                </Select>
              </FormControl>
              <TextField label="Max Symbols" type="number" fullWidth defaultValue={50} />
              <TextField label="Min Turnover Threshold (KRW)" type="number" fullWidth defaultValue={10000000000} />
              <TextField label="Refresh Interval (seconds)" type="number" fullWidth defaultValue={3600} />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Typography variant="h6">Chart Settings</Typography>
              <FormControl fullWidth>
                <InputLabel>Default Timeframe</InputLabel>
                <Select label="Default Timeframe" defaultValue="5m">
                  <MenuItem value="1m">1 Minute</MenuItem>
                  <MenuItem value="5m">5 Minutes</MenuItem>
                  <MenuItem value="15m">15 Minutes</MenuItem>
                  <MenuItem value="1h">1 Hour</MenuItem>
                </Select>
              </FormControl>
              <FormControlLabel control={<Switch defaultChecked />} label="Show volume by default" />
              <FormControlLabel control={<Switch defaultChecked />} label="Show signal markers by default" />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Typography variant="h6">Risk Defaults</Typography>
              <TextField label="Daily Loss Limit %" type="number" fullWidth defaultValue={5} />
              <TextField label="Max Drawdown %" type="number" fullWidth defaultValue={10} />
              <FormControlLabel control={<Switch defaultChecked />} label="Kill switch enabled" />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%' }}>
            <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Typography variant="h6">Live Protection</Typography>
              <FormControlLabel control={<Switch defaultChecked disabled />} label="Require explicit confirmation (Always ON)" />
              <TextField label="Max Trade Amount (KRW)" type="number" fullWidth defaultValue={1000000} />
              <Alert severity="warning" sx={{ mt: 1 }}>
                LIVE TRADING ACTIVE — Real money at risk
              </Alert>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
        <Button variant="contained" color="primary" size="large" onClick={handleSave}>
          Save Settings
        </Button>
      </Box>

      <Snackbar
        open={toastOpen}
        autoHideDuration={3000}
        onClose={() => setToastOpen(false)}
        message="Settings persistence coming soon"
      />
    </Box>
  )
}
