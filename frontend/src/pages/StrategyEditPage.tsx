import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Tabs,
  Tab,
  TextField,
  Grid,
  Stack,
  IconButton,
  Alert,
  CircularProgress,
  Divider,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  FormControlLabel,
  Switch,
  Chip
} from '@mui/material'
import { ArrowLeft, Save, X, CheckCircle2, AlertCircle } from 'lucide-react'
import { useStrategy, useStrategyVersions, useValidateVersion } from '@/features/strategies/api'

interface TabPanelProps {
  children?: React.ReactNode
  index: number
  value: number
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`strategy-tabpanel-${index}`}
      aria-labelledby={`strategy-tab-${index}`}
      {...other}
      style={{ height: '100%' }}
    >
      {value === index && (
        <Box sx={{ p: 3, height: '100%', overflowY: 'auto' }}>
          {children}
        </Box>
      )}
    </div>
  )
}

export default function StrategyEditPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: strategy, isLoading: isLoadingStrategy } = useStrategy(id!)
  const { data: versions, isLoading: isLoadingVersions } = useStrategyVersions(id!)
  const validateMutation = useValidateVersion()

  const [tabValue, setTabValue] = useState(0)
  const [configJson, setConfigJson] = useState<Record<string, any>>({})
  const [jsonText, setJsonText] = useState('')
  const [jsonError, setJsonError] = useState<string | null>(null)
  const [validationResult, setValidationResult] = useState<{ is_valid: boolean, errors: string[], warnings: string[] } | null>(null)

  // Form state for basic info
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [labels, setLabels] = useState<string>('')

  useEffect(() => {
    if (strategy) {
      setName(strategy.name)
      setDescription(strategy.description || '')
      setLabels(strategy.labels.join(', '))
    }
  }, [strategy])

  useEffect(() => {
    if (versions && versions.length > 0) {
      const latest = versions[0]
      setConfigJson(latest.config_json)
      setJsonText(JSON.stringify(latest.config_json, null, 2))
    }
  }, [versions])

  const handleJsonChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const text = e.target.value
    setJsonText(text)
    try {
      const parsed = JSON.parse(text)
      setConfigJson(parsed)
      setJsonError(null)
    } catch (err: any) {
      setJsonError(err.message)
    }
  }

  const updateConfig = (path: string[], value: any) => {
    setConfigJson(prev => {
      const newConfig = { ...prev }
      let current = newConfig
      for (let i = 0; i < path.length - 1; i++) {
        if (!current[path[i]]) current[path[i]] = {}
        current = current[path[i]]
      }
      current[path[path.length - 1]] = value
      setJsonText(JSON.stringify(newConfig, null, 2))
      return newConfig
    })
  }

  const handleValidate = async () => {
    if (!versions?.[0]) return
    try {
      const result = await validateMutation.mutateAsync({
        versionId: versions[0].id,
        config_json: configJson
      })
      setValidationResult(result)
      setTabValue(9) // Switch to validation tab
    } catch (err) {
      console.error('Validation failed', err)
    }
  }

  if (isLoadingStrategy || isLoadingVersions) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Box>
    )
  }

  if (!strategy) {
    return <Typography>Strategy not found</Typography>
  }

  return (
    <Box sx={{ height: 'calc(100vh - 100px)', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 2, flexShrink: 0 }}>
        <IconButton onClick={() => navigate(`/strategies/${strategy.id}`)} sx={{ color: 'text.secondary' }}>
          <ArrowLeft size={20} />
        </IconButton>
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h5">Edit Strategy: {strategy.name}</Typography>
          <Typography variant="body2" color="text.tertiary">
            Editing based on v{versions?.[0]?.version_no || 1}
          </Typography>
        </Box>
        <Button 
          variant="outlined" 
          onClick={handleValidate}
          disabled={!!jsonError || validateMutation.isPending}
        >
          {validateMutation.isPending ? 'Validating...' : 'Validate'}
        </Button>
      </Box>

      {/* Main Editor Area */}
      <Card sx={{ flexGrow: 1, display: 'flex', flexDirection: 'row', overflow: 'hidden' }}>
        <Tabs
          orientation="vertical"
          variant="scrollable"
          value={tabValue}
          onChange={(_, newValue) => setTabValue(newValue)}
          sx={{ 
            borderRight: 1, 
            borderColor: 'divider',
            minWidth: 200,
            bgcolor: 'bg.surface2',
            '& .MuiTab-root': { alignItems: 'flex-start', textAlign: 'left', px: 3 }
          }}
        >
          <Tab label="Basic Info" />
          <Tab label="Market & Universe" />
          <Tab label="Entry" />
          <Tab label="Position" />
          <Tab label="Exit" />
          <Tab label="Risk" />
          <Tab label="Execution" />
          <Tab label="Backtest" />
          <Tab label="JSON Editor" />
          <Tab 
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                Validation
                {validationResult && (
                  validationResult.is_valid ? 
                    <CheckCircle2 size={14} color="var(--mui-palette-status-success)" /> : 
                    <AlertCircle size={14} color="var(--mui-palette-status-danger)" />
                )}
              </Box>
            } 
          />
        </Tabs>

        <Box sx={{ flexGrow: 1, overflow: 'hidden' }}>
          <TabPanel value={tabValue} index={0}>
            <Stack spacing={3} maxWidth={600}>
              <TextField 
                label="Strategy Name" 
                value={name} 
                onChange={(e) => setName(e.target.value)} 
                fullWidth 
              />
              <TextField 
                label="Description" 
                value={description} 
                onChange={(e) => setDescription(e.target.value)} 
                multiline 
                rows={3} 
                fullWidth 
              />
              <TextField 
                label="Labels (comma separated)" 
                value={labels} 
                onChange={(e) => setLabels(e.target.value)} 
                fullWidth 
                helperText="e.g. momentum, crypto, high-risk"
              />
              <TextField 
                label="Strategy Type" 
                value={strategy.strategy_type.toUpperCase()} 
                disabled 
                fullWidth 
              />
            </Stack>
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            <Typography variant="h6" mb={3}>Market Configuration</Typography>
            <Grid container spacing={3} maxWidth={800}>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Exchange</InputLabel>
                  <Select
                    value={configJson.market?.exchange || 'UPBIT'}
                    label="Exchange"
                    onChange={(e) => updateConfig(['market', 'exchange'], e.target.value)}
                  >
                    <MenuItem value="UPBIT">Upbit</MenuItem>
                    <MenuItem value="BINANCE">Binance</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Trade Basis</InputLabel>
                  <Select
                    value={configJson.market?.trade_basis || 'candle'}
                    label="Trade Basis"
                    onChange={(e) => updateConfig(['market', 'trade_basis'], e.target.value)}
                  >
                    <MenuItem value="candle">Candle</MenuItem>
                    <MenuItem value="tick">Tick</MenuItem>
                    <MenuItem value="hybrid">Hybrid</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12}>
                <TextField 
                  label="Timeframes (comma separated)" 
                  value={(configJson.market?.timeframes || []).join(', ')}
                  onChange={(e) => updateConfig(['market', 'timeframes'], e.target.value.split(',').map(s => s.trim()))}
                  fullWidth 
                  helperText="e.g. 1m, 5m, 1h, 1d"
                />
              </Grid>
            </Grid>

            <Divider sx={{ my: 4 }} />
            
            <Typography variant="h6" mb={3}>Universe Configuration</Typography>
            <Grid container spacing={3} maxWidth={800}>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Mode</InputLabel>
                  <Select
                    value={configJson.universe?.mode || 'dynamic'}
                    label="Mode"
                    onChange={(e) => updateConfig(['universe', 'mode'], e.target.value)}
                  >
                    <MenuItem value="dynamic">Dynamic</MenuItem>
                    <MenuItem value="static">Static</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField 
                  label="Max Symbols" 
                  type="number"
                  value={configJson.universe?.max_symbols || 10}
                  onChange={(e) => updateConfig(['universe', 'max_symbols'], parseInt(e.target.value))}
                  fullWidth 
                />
              </Grid>
            </Grid>
          </TabPanel>

          <TabPanel value={tabValue} index={2}>
            <Typography variant="h6" mb={2}>Entry Conditions</Typography>
            <Alert severity="info" sx={{ mb: 3 }}>
              For MVP, please edit entry conditions directly in JSON format.
            </Alert>
            <TextField
              multiline
              fullWidth
              rows={15}
              value={JSON.stringify(configJson.entry || {}, null, 2)}
              onChange={(e) => {
                try {
                  const parsed = JSON.parse(e.target.value)
                  updateConfig(['entry'], parsed)
                } catch (err) {
                  // Ignore parse errors while typing
                }
              }}
              sx={{ fontFamily: 'monospace' }}
            />
          </TabPanel>

          <TabPanel value={tabValue} index={3}>
            <Typography variant="h6" mb={3}>Position Sizing</Typography>
            <Grid container spacing={3} maxWidth={800}>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Size Mode</InputLabel>
                  <Select
                    value={configJson.position?.size_mode || 'fixed_percent'}
                    label="Size Mode"
                    onChange={(e) => updateConfig(['position', 'size_mode'], e.target.value)}
                  >
                    <MenuItem value="fixed_amount">Fixed Amount</MenuItem>
                    <MenuItem value="fixed_percent">Fixed Percent</MenuItem>
                    <MenuItem value="fractional_kelly">Fractional Kelly</MenuItem>
                    <MenuItem value="risk_per_trade">Risk Per Trade</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField 
                  label="Size Value" 
                  type="number"
                  value={configJson.position?.size_value || 0}
                  onChange={(e) => updateConfig(['position', 'size_value'], parseFloat(e.target.value))}
                  fullWidth 
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField 
                  label="Max Open Positions Per Symbol" 
                  type="number"
                  value={configJson.position?.max_open_positions_per_symbol || 1}
                  onChange={(e) => updateConfig(['position', 'max_open_positions_per_symbol'], parseInt(e.target.value))}
                  fullWidth 
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField 
                  label="Max Concurrent Positions" 
                  type="number"
                  value={configJson.position?.max_concurrent_positions || 5}
                  onChange={(e) => updateConfig(['position', 'max_concurrent_positions'], parseInt(e.target.value))}
                  fullWidth 
                />
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch 
                      checked={configJson.position?.allow_scale_in || false}
                      onChange={(e) => updateConfig(['position', 'allow_scale_in'], e.target.checked)}
                    />
                  }
                  label="Allow Scale In"
                />
              </Grid>
            </Grid>
          </TabPanel>

          <TabPanel value={tabValue} index={4}>
            <Typography variant="h6" mb={3}>Exit Conditions</Typography>
            <Grid container spacing={3} maxWidth={800}>
              <Grid item xs={12} sm={6}>
                <TextField 
                  label="Stop Loss %" 
                  type="number"
                  value={configJson.exit?.stop_loss_pct || ''}
                  onChange={(e) => updateConfig(['exit', 'stop_loss_pct'], parseFloat(e.target.value))}
                  fullWidth 
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField 
                  label="Take Profit %" 
                  type="number"
                  value={configJson.exit?.take_profit_pct || ''}
                  onChange={(e) => updateConfig(['exit', 'take_profit_pct'], parseFloat(e.target.value))}
                  fullWidth 
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField 
                  label="Trailing Stop %" 
                  type="number"
                  value={configJson.exit?.trailing_stop_pct || ''}
                  onChange={(e) => updateConfig(['exit', 'trailing_stop_pct'], parseFloat(e.target.value))}
                  fullWidth 
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField 
                  label="Time Stop (Bars)" 
                  type="number"
                  value={configJson.exit?.time_stop_bars || ''}
                  onChange={(e) => updateConfig(['exit', 'time_stop_bars'], parseInt(e.target.value))}
                  fullWidth 
                />
              </Grid>
            </Grid>
          </TabPanel>

          <TabPanel value={tabValue} index={5}>
            <Typography variant="h6" mb={3}>Risk Management</Typography>
            <Grid container spacing={3} maxWidth={800}>
              <Grid item xs={12} sm={6}>
                <TextField 
                  label="Daily Loss Limit %" 
                  type="number"
                  value={configJson.risk?.daily_loss_limit_pct || 0}
                  onChange={(e) => updateConfig(['risk', 'daily_loss_limit_pct'], parseFloat(e.target.value))}
                  fullWidth 
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField 
                  label="Max Strategy Drawdown %" 
                  type="number"
                  value={configJson.risk?.max_strategy_drawdown_pct || 0}
                  onChange={(e) => updateConfig(['risk', 'max_strategy_drawdown_pct'], parseFloat(e.target.value))}
                  fullWidth 
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField 
                  label="Max Order Retries" 
                  type="number"
                  value={configJson.risk?.max_order_retries || 3}
                  onChange={(e) => updateConfig(['risk', 'max_order_retries'], parseInt(e.target.value))}
                  fullWidth 
                />
              </Grid>
              <Grid item xs={12}>
                <Stack spacing={2}>
                  <FormControlLabel
                    control={
                      <Switch 
                        checked={configJson.risk?.prevent_duplicate_entry || false}
                        onChange={(e) => updateConfig(['risk', 'prevent_duplicate_entry'], e.target.checked)}
                      />
                    }
                    label="Prevent Duplicate Entry"
                  />
                  <FormControlLabel
                    control={
                      <Switch 
                        checked={configJson.risk?.kill_switch_enabled || false}
                        onChange={(e) => updateConfig(['risk', 'kill_switch_enabled'], e.target.checked)}
                      />
                    }
                    label="Enable Kill Switch"
                  />
                </Stack>
              </Grid>
            </Grid>
          </TabPanel>

          <TabPanel value={tabValue} index={6}>
            <Typography variant="h6" mb={3}>Execution Settings</Typography>
            <Grid container spacing={3} maxWidth={800}>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Entry Order Type</InputLabel>
                  <Select
                    value={configJson.execution?.entry_order_type || 'market'}
                    label="Entry Order Type"
                    onChange={(e) => updateConfig(['execution', 'entry_order_type'], e.target.value)}
                  >
                    <MenuItem value="market">Market</MenuItem>
                    <MenuItem value="limit">Limit</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Exit Order Type</InputLabel>
                  <Select
                    value={configJson.execution?.exit_order_type || 'market'}
                    label="Exit Order Type"
                    onChange={(e) => updateConfig(['execution', 'exit_order_type'], e.target.value)}
                  >
                    <MenuItem value="market">Market</MenuItem>
                    <MenuItem value="limit">Limit</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Slippage Model</InputLabel>
                  <Select
                    value={configJson.execution?.slippage_model || 'fixed_bps'}
                    label="Slippage Model"
                    onChange={(e) => updateConfig(['execution', 'slippage_model'], e.target.value)}
                  >
                    <MenuItem value="none">None</MenuItem>
                    <MenuItem value="fixed_bps">Fixed BPS</MenuItem>
                    <MenuItem value="volatility_scaled">Volatility Scaled</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Fee Model</InputLabel>
                  <Select
                    value={configJson.execution?.fee_model || 'per_fill'}
                    label="Fee Model"
                    onChange={(e) => updateConfig(['execution', 'fee_model'], e.target.value)}
                  >
                    <MenuItem value="per_fill">Per Fill</MenuItem>
                    <MenuItem value="per_order">Per Order</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
          </TabPanel>

          <TabPanel value={tabValue} index={7}>
            <Typography variant="h6" mb={3}>Backtest Assumptions</Typography>
            <Grid container spacing={3} maxWidth={800}>
              <Grid item xs={12} sm={6}>
                <TextField 
                  label="Initial Capital" 
                  type="number"
                  value={configJson.backtest?.initial_capital || 10000000}
                  onChange={(e) => updateConfig(['backtest', 'initial_capital'], parseFloat(e.target.value))}
                  fullWidth 
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField 
                  label="Fee (BPS)" 
                  type="number"
                  value={configJson.backtest?.fee_bps || 5}
                  onChange={(e) => updateConfig(['backtest', 'fee_bps'], parseFloat(e.target.value))}
                  fullWidth 
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField 
                  label="Slippage (BPS)" 
                  type="number"
                  value={configJson.backtest?.slippage_bps || 10}
                  onChange={(e) => updateConfig(['backtest', 'slippage_bps'], parseFloat(e.target.value))}
                  fullWidth 
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField 
                  label="Latency (ms)" 
                  type="number"
                  value={configJson.backtest?.latency_ms || 50}
                  onChange={(e) => updateConfig(['backtest', 'latency_ms'], parseInt(e.target.value))}
                  fullWidth 
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Fill Assumption</InputLabel>
                  <Select
                    value={configJson.backtest?.fill_assumption || 'next_bar_open'}
                    label="Fill Assumption"
                    onChange={(e) => updateConfig(['backtest', 'fill_assumption'], e.target.value)}
                  >
                    <MenuItem value="best_bid_ask">Best Bid/Ask</MenuItem>
                    <MenuItem value="mid">Mid Price</MenuItem>
                    <MenuItem value="next_tick">Next Tick</MenuItem>
                    <MenuItem value="next_bar_open">Next Bar Open</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
          </TabPanel>

          <TabPanel value={tabValue} index={8}>
            <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <Typography variant="h6" mb={2}>Raw JSON Editor</Typography>
              {jsonError && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  Invalid JSON: {jsonError}
                </Alert>
              )}
              <TextField
                multiline
                fullWidth
                value={jsonText}
                onChange={handleJsonChange}
                error={!!jsonError}
                sx={{ 
                  flexGrow: 1,
                  '& .MuiInputBase-root': { height: '100%', alignItems: 'flex-start' },
                  '& textarea': { fontFamily: 'monospace', fontSize: 13, height: '100% !important' }
                }}
              />
            </Box>
          </TabPanel>

          <TabPanel value={tabValue} index={9}>
            <Typography variant="h6" mb={3}>Validation Results</Typography>
            {!validationResult ? (
              <Typography color="text.secondary">
                Click "Validate" in the header to check your configuration against the schema.
              </Typography>
            ) : (
              <Stack spacing={3}>
                <Alert severity={validationResult.is_valid ? "success" : "error"}>
                  {validationResult.is_valid ? "Configuration is valid." : "Configuration has errors."}
                </Alert>
                
                {validationResult.errors.length > 0 && (
                  <Box>
                    <Typography variant="subtitle1" color="error" mb={1}>Errors ({validationResult.errors.length})</Typography>
                    <Stack spacing={1}>
                      {validationResult.errors.map((err, i) => (
                        <Alert key={i} severity="error" variant="outlined" sx={{ py: 0 }}>{err}</Alert>
                      ))}
                    </Stack>
                  </Box>
                )}

                {validationResult.warnings.length > 0 && (
                  <Box>
                    <Typography variant="subtitle1" color="warning.main" mb={1}>Warnings ({validationResult.warnings.length})</Typography>
                    <Stack spacing={1}>
                      {validationResult.warnings.map((warn, i) => (
                        <Alert key={i} severity="warning" variant="outlined" sx={{ py: 0 }}>{warn}</Alert>
                      ))}
                    </Stack>
                  </Box>
                )}
              </Stack>
            )}
          </TabPanel>
        </Box>
      </Card>

      {/* Bottom Action Bar */}
      <Box 
        sx={{ 
          mt: 2, 
          p: 2, 
          bgcolor: 'bg.surface1', 
          border: '1px solid', 
          borderColor: 'border.default',
          borderRadius: 2,
          display: 'flex',
          justifyContent: 'flex-end',
          gap: 2,
          flexShrink: 0
        }}
      >
        <Button 
          variant="outlined" 
          startIcon={<X size={16} />}
          onClick={() => navigate(`/strategies/${strategy.id}`)}
        >
          Discard Changes
        </Button>
        <Button 
          variant="contained" 
          color="primary" 
          startIcon={<Save size={16} />}
          disabled={!!jsonError}
        >
          Save as New Version
        </Button>
      </Box>
    </Box>
  )
}
