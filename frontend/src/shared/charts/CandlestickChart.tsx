import { useEffect, useMemo, useRef } from 'react'
import { Box } from '@mui/material'
import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  LineSeries,
  LineStyle,
  createChart,
  createSeriesMarkers,
} from 'lightweight-charts'
import type {
  CandlestickData,
  HistogramData,
  IChartApi,
  IPriceLine,
  ISeriesApi,
  ISeriesMarkersPluginApi,
  LineData,
  MouseEventParams,
  SeriesMarker,
  Time,
  UTCTimestamp,
} from 'lightweight-charts'

import type { CandlePoint } from '@/entities/market/types'
import type { Signal } from '@/entities/session/types'
import {
  buildChartIndicatorData,
  type ChartIndicatorSettings,
  type HistogramPoint,
  type MovingAverageSetting,
  type TimeValuePoint,
} from '@/shared/charts/chartIndicators'

interface CandlestickChartProps {
  data: CandlePoint[]
  indicatorSettings: ChartIndicatorSettings
  signals: Signal[]
  showSignalMarkers?: boolean
  showVolume?: boolean
  showMovingAverages?: boolean
  onMarkerSelect?: (signalId: string) => void
  height?: number
}

interface TooltipRefs {
  root: HTMLDivElement | null
  time: HTMLDivElement | null
  open: HTMLSpanElement | null
  high: HTMLSpanElement | null
  low: HTMLSpanElement | null
  close: HTMLSpanElement | null
  volume: HTMLSpanElement | null
}

const KST_TIME_ZONE = 'Asia/Seoul'
const CHART_COLORS = {
  background: '#0b1120',
  surface: '#131b2e',
  text: '#a9b4c7',
  muted: '#6f7b91',
  grid: 'rgba(255, 255, 255, 0.07)',
  border: 'rgba(255, 255, 255, 0.12)',
  up: '#f04452',
  down: '#4c86ff',
  currentPrice: '#7aa2ff',
  maPalette: ['#f5b700', '#67e8f9', '#d8b4fe', '#fb7185', '#86efac'],
  rsi: '#c084fc',
  signal: '#ff9f43',
  macd: '#5dade2',
  macdPositive: 'rgba(44, 208, 126, 0.82)',
  macdNegative: 'rgba(255, 98, 98, 0.82)',
  rsiBand: 'rgba(192, 132, 252, 0.08)',
  levelLine: 'rgba(255, 255, 255, 0.18)',
  tooltip: '#101827',
}

const AXIS_TIME_FORMATTER = new Intl.DateTimeFormat('ko-KR', {
  timeZone: KST_TIME_ZONE,
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})

const CROSSHAIR_TIME_FORMATTER = new Intl.DateTimeFormat('ko-KR', {
  timeZone: KST_TIME_ZONE,
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})

function toChartTime(time: string): UTCTimestamp {
  return Math.floor(new Date(time).getTime() / 1000) as UTCTimestamp
}

function toDateFromChartTime(time: Time): Date | null {
  if (typeof time === 'number') {
    return new Date(time * 1000)
  }

  if (typeof time === 'string') {
    const parsed = new Date(time)
    return Number.isNaN(parsed.getTime()) ? null : parsed
  }

  return new Date(Date.UTC(time.year, time.month - 1, time.day))
}

function formatAxisTime(time: Time): string | null {
  const date = toDateFromChartTime(time)
  return date ? AXIS_TIME_FORMATTER.format(date) : null
}

function formatCrosshairTime(time: Time): string {
  const date = toDateFromChartTime(time)
  return date ? CROSSHAIR_TIME_FORMATTER.format(date) : ''
}

function formatKrwPrice(value: number): string {
  return Math.round(value).toLocaleString('ko-KR')
}

function formatIndicatorValue(value: number): string {
  return value.toFixed(2)
}

function formatVolume(value: number): string {
  return Math.round(value).toLocaleString('ko-KR')
}

function toCandlestickDatum(point: CandlePoint): CandlestickData<Time> {
  return {
    time: toChartTime(point.time),
    open: point.open,
    high: point.high,
    low: point.low,
    close: point.close,
  }
}

function toLineData(points: TimeValuePoint[]): LineData<Time>[] {
  return points.map((point) => ({
    time: toChartTime(point.time),
    value: point.value,
  }))
}

function toHistogramData(points: HistogramPoint[]): HistogramData<Time>[] {
  return points.map((point) => ({
    time: toChartTime(point.time),
    value: point.value,
    color: point.color,
  }))
}

function shouldResetSeries(previousData: CandlestickData<Time>[], nextData: CandlestickData<Time>[]): boolean {
  if (!previousData.length || !nextData.length) {
    return true
  }

  if (nextData.length < previousData.length) {
    return true
  }

  if (previousData[0]?.time !== nextData[0]?.time) {
    return true
  }

  return previousData.slice(0, -1).some((point, index) => point.time !== nextData[index]?.time)
}

function getMovingAverageColor(setting: MovingAverageSetting, index: number): string {
  return CHART_COLORS.maPalette[index % CHART_COLORS.maPalette.length] ?? (setting.type === 'ema' ? '#f5b700' : '#94a3b8')
}

function isCandlestickPoint(value: unknown): value is CandlestickData<Time> {
  if (!value || typeof value !== 'object') {
    return false
  }

  return ['open', 'high', 'low', 'close'].every((key) => typeof (value as Record<string, unknown>)[key] === 'number')
}

function buildSignalMarkers(signals: Signal[], showSignalMarkers: boolean): SeriesMarker<Time>[] {
  if (!showSignalMarkers) {
    return []
  }

  return signals.map((signal) => ({
    time: toChartTime(signal.snapshot_time),
    position: signal.action === 'ENTER' ? 'belowBar' : 'aboveBar',
    shape: signal.action === 'ENTER' ? 'arrowUp' : 'arrowDown',
    color: signal.blocked || Boolean(signal.explain_payload?.risk_blocks?.length)
      ? '#f59e0b'
      : (signal.action === 'ENTER' ? '#22c55e' : '#ef4444'),
    text: signal.blocked ? '차단' : (signal.action === 'ENTER' ? '매수' : '매도'),
    id: signal.id,
  }))
}

interface ChartSeriesRefs {
  candle: ISeriesApi<'Candlestick'> | null
  volume: ISeriesApi<'Histogram'> | null
  movingAverages: Map<string, ISeriesApi<'Line'>>
  rsi: ISeriesApi<'Line'> | null
  macdLine: ISeriesApi<'Line'> | null
  macdSignal: ISeriesApi<'Line'> | null
  macdHistogram: ISeriesApi<'Histogram'> | null
}

export function CandlestickChart({
  data,
  indicatorSettings,
  signals,
  showSignalMarkers = true,
  showVolume = true,
  showMovingAverages = true,
  onMarkerSelect,
  height,
}: CandlestickChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const resizeObserverRef = useRef<ResizeObserver | null>(null)
  const seriesRefs = useRef<ChartSeriesRefs>({
    candle: null,
    volume: null,
    movingAverages: new Map(),
    rsi: null,
    macdLine: null,
    macdSignal: null,
    macdHistogram: null,
  })
  const markerPluginRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null)
  const signalsRef = useRef(signals)
  const onMarkerSelectRef = useRef(onMarkerSelect)
  const candleLookupRef = useRef<Map<UTCTimestamp, CandlePoint>>(new Map())
  const tooltipRefs = useRef<TooltipRefs>({
    root: null,
    time: null,
    open: null,
    high: null,
    low: null,
    close: null,
    volume: null,
  })
  const previousCandlesRef = useRef<CandlestickData<Time>[]>([])
  const rsiPriceLinesRef = useRef<IPriceLine[]>([])
  const macdZeroLineRef = useRef<IPriceLine | null>(null)
  const autoFollowRef = useRef(true)
  const hasInitialFitRef = useRef(false)

  const indicatorData = useMemo(
    () => buildChartIndicatorData(data, indicatorSettings),
    [data, indicatorSettings],
  )

  const markerData = useMemo(
    () => buildSignalMarkers(signals, showSignalMarkers),
    [showSignalMarkers, signals],
  )

  useEffect(() => {
    signalsRef.current = signals
  }, [signals])

  useEffect(() => {
    onMarkerSelectRef.current = onMarkerSelect
  }, [onMarkerSelect])

  useEffect(() => {
    candleLookupRef.current = new Map(
      data.map((point) => [toChartTime(point.time), point]),
    )
  }, [data])

  useEffect(() => {
    if (!containerRef.current) {
      return
    }

    const container = containerRef.current
    const chart = createChart(container, {
      autoSize: false,
      width: container.clientWidth,
      height: Math.max(height ?? container.clientHeight ?? 0, 520),
      layout: {
        background: { type: ColorType.Solid, color: CHART_COLORS.background },
        textColor: CHART_COLORS.text,
      },
      grid: {
        vertLines: { color: CHART_COLORS.grid },
        horzLines: { color: CHART_COLORS.grid },
      },
      localization: {
        locale: 'ko-KR',
        timeFormatter: formatCrosshairTime,
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: CHART_COLORS.levelLine,
          style: LineStyle.Dashed,
          labelBackgroundColor: CHART_COLORS.tooltip,
        },
        horzLine: {
          color: CHART_COLORS.levelLine,
          style: LineStyle.Dashed,
          labelBackgroundColor: CHART_COLORS.currentPrice,
        },
      },
      rightPriceScale: {
        borderVisible: false,
      },
      timeScale: {
        borderVisible: false,
        timeVisible: true,
        secondsVisible: false,
        tickMarkFormatter: (time: Time) => formatAxisTime(time),
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: false,
      },
      handleScale: {
        axisPressedMouseMove: {
          time: true,
          price: true,
        },
        mouseWheel: true,
        pinch: true,
      },
    })

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: CHART_COLORS.up,
      downColor: CHART_COLORS.down,
      wickUpColor: CHART_COLORS.up,
      wickDownColor: CHART_COLORS.down,
      borderUpColor: CHART_COLORS.up,
      borderDownColor: CHART_COLORS.down,
      priceFormat: {
        type: 'custom',
        formatter: formatKrwPrice,
        minMove: 1,
      },
      priceLineVisible: true,
      priceLineColor: CHART_COLORS.currentPrice,
      priceLineStyle: LineStyle.Dotted,
      lastValueVisible: true,
    })
    candleSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.06,
        bottom: 0.22,
      },
      borderVisible: false,
    })

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceScaleId: 'volume',
      priceFormat: {
        type: 'volume',
      },
      priceLineVisible: false,
      lastValueVisible: false,
      base: 0,
    })
    chart.priceScale('volume', 0).applyOptions({
      visible: false,
      scaleMargins: {
        top: 0.76,
        bottom: 0.02,
      },
    })

    const movingAverageSeries = new Map<string, ISeriesApi<'Line'>>()
    indicatorSettings.movingAverages.forEach((movingAverage, index) => {
      const series = chart.addSeries(LineSeries, {
        color: getMovingAverageColor(movingAverage, index),
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      })
      movingAverageSeries.set(movingAverage.id, series)
    })

    const rsiSeries = chart.addSeries(LineSeries, {
      color: CHART_COLORS.rsi,
      lineWidth: 2,
      priceFormat: {
        type: 'custom',
        formatter: formatIndicatorValue,
        minMove: 0.01,
      },
      priceLineVisible: false,
      lastValueVisible: true,
      crosshairMarkerVisible: false,
    }, 1)
    rsiSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.12,
        bottom: 0.12,
      },
      borderVisible: false,
      autoScale: true,
    })
    rsiPriceLinesRef.current = [70, 50, 30].map((price) => rsiSeries.createPriceLine({
      price,
      color: CHART_COLORS.levelLine,
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: price !== 50,
      title: '',
    }))

    const macdHistogramSeries = chart.addSeries(HistogramSeries, {
      priceFormat: {
        type: 'custom',
        formatter: formatIndicatorValue,
        minMove: 0.01,
      },
      priceLineVisible: false,
      lastValueVisible: true,
      base: 0,
    }, 2)
    const macdLineSeries = chart.addSeries(LineSeries, {
      color: CHART_COLORS.macd,
      lineWidth: 2,
      priceFormat: {
        type: 'custom',
        formatter: formatIndicatorValue,
        minMove: 0.01,
      },
      priceLineVisible: false,
      lastValueVisible: true,
      crosshairMarkerVisible: false,
    }, 2)
    const macdSignalSeries = chart.addSeries(LineSeries, {
      color: CHART_COLORS.signal,
      lineWidth: 2,
      priceFormat: {
        type: 'custom',
        formatter: formatIndicatorValue,
        minMove: 0.01,
      },
      priceLineVisible: false,
      lastValueVisible: true,
      crosshairMarkerVisible: false,
    }, 2)
    macdLineSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.12,
        bottom: 0.12,
      },
      borderVisible: false,
      autoScale: true,
    })
    macdZeroLineRef.current = macdLineSeries.createPriceLine({
      price: 0,
      color: CHART_COLORS.levelLine,
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: false,
      title: '',
    })

    const markerPlugin = createSeriesMarkers(candleSeries)
    const hideTooltip = () => {
      if (!tooltipRefs.current.root) {
        return
      }

      tooltipRefs.current.root.style.opacity = '0'
      tooltipRefs.current.root.style.visibility = 'hidden'
    }
    const handleClick = (param: MouseEventParams<Time>) => {
      if (!onMarkerSelectRef.current || param.time == null) {
        return
      }

      const selectedSignal = signalsRef.current.find((signal) => toChartTime(signal.snapshot_time) === param.time)
      if (selectedSignal) {
        onMarkerSelectRef.current(selectedSignal.id)
      }
    }
    const disableAutoFollow = () => {
      autoFollowRef.current = false
    }
    const handleCrosshairMove = (param: MouseEventParams<Time>) => {
      const tooltipRoot = tooltipRefs.current.root
      const tooltipTime = tooltipRefs.current.time
      const tooltipOpen = tooltipRefs.current.open
      const tooltipHigh = tooltipRefs.current.high
      const tooltipLow = tooltipRefs.current.low
      const tooltipClose = tooltipRefs.current.close
      const tooltipVolume = tooltipRefs.current.volume

      if (
        !tooltipRoot
        || !tooltipTime
        || !tooltipOpen
        || !tooltipHigh
        || !tooltipLow
        || !tooltipClose
        || !tooltipVolume
        || !param.point
        || param.time == null
        || !seriesRefs.current.candle
      ) {
        hideTooltip()
        return
      }

      if (
        param.point.x < 0
        || param.point.y < 0
        || param.point.x > container.clientWidth
        || param.point.y > container.clientHeight
      ) {
        hideTooltip()
        return
      }

      const hoveredBar = param.seriesData.get(seriesRefs.current.candle)
      if (!isCandlestickPoint(hoveredBar)) {
        hideTooltip()
        return
      }

      const candle = candleLookupRef.current.get(param.time as UTCTimestamp)
      tooltipTime.textContent = formatCrosshairTime(param.time)
      tooltipOpen.textContent = formatKrwPrice(hoveredBar.open)
      tooltipHigh.textContent = formatKrwPrice(hoveredBar.high)
      tooltipLow.textContent = formatKrwPrice(hoveredBar.low)
      tooltipClose.textContent = formatKrwPrice(hoveredBar.close)
      tooltipVolume.textContent = formatVolume(candle?.volume ?? 0)

      const tooltipWidth = 196
      const tooltipHeight = 112
      const left = Math.min(
        Math.max(param.point.x + 16, 12),
        Math.max(container.clientWidth - tooltipWidth - 12, 12),
      )
      const top = Math.min(
        Math.max(param.point.y - tooltipHeight - 16, 12),
        Math.max(container.clientHeight - tooltipHeight - 12, 12),
      )

      tooltipRoot.style.transform = `translate(${left}px, ${top}px)`
      tooltipRoot.style.opacity = '1'
      tooltipRoot.style.visibility = 'visible'
    }

    resizeObserverRef.current = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (!entry) {
        return
      }

      chart.applyOptions({
        width: entry.contentRect.width,
        height: Math.max(height ?? entry.contentRect.height, 520),
      })
    })
    resizeObserverRef.current.observe(container)
    container.addEventListener('wheel', disableAutoFollow, { passive: true })
    container.addEventListener('pointerdown', disableAutoFollow)
    container.addEventListener('touchstart', disableAutoFollow, { passive: true })
    chart.subscribeClick(handleClick)
    chart.subscribeCrosshairMove(handleCrosshairMove)

    chartRef.current = chart
    markerPluginRef.current = markerPlugin
    autoFollowRef.current = true
    hasInitialFitRef.current = false
    seriesRefs.current = {
      candle: candleSeries,
      volume: volumeSeries,
      movingAverages: movingAverageSeries,
      rsi: rsiSeries,
      macdLine: macdLineSeries,
      macdSignal: macdSignalSeries,
      macdHistogram: macdHistogramSeries,
    }

    const panes = chart.panes()
    panes[0]?.setStretchFactor(0.62)
    panes[1]?.setStretchFactor(0.16)
    panes[2]?.setStretchFactor(0.22)

    return () => {
      resizeObserverRef.current?.disconnect()
      resizeObserverRef.current = null
      container.removeEventListener('wheel', disableAutoFollow)
      container.removeEventListener('pointerdown', disableAutoFollow)
      container.removeEventListener('touchstart', disableAutoFollow)
      chart.unsubscribeClick(handleClick)
      chart.unsubscribeCrosshairMove(handleCrosshairMove)
      markerPlugin.detach()
      markerPluginRef.current = null
      rsiPriceLinesRef.current.forEach((line) => rsiSeries.removePriceLine(line))
      rsiPriceLinesRef.current = []
      if (macdZeroLineRef.current) {
        macdLineSeries.removePriceLine(macdZeroLineRef.current)
        macdZeroLineRef.current = null
      }
      previousCandlesRef.current = []
      autoFollowRef.current = true
      hasInitialFitRef.current = false
      seriesRefs.current = {
        candle: null,
        volume: null,
        movingAverages: new Map(),
        rsi: null,
        macdLine: null,
        macdSignal: null,
        macdHistogram: null,
      }
      chartRef.current = null
      chart.remove()
    }
  }, [height, indicatorSettings])

  useEffect(() => {
    const candleSeries = seriesRefs.current.candle
    const volumeSeries = seriesRefs.current.volume
    const rsiSeries = seriesRefs.current.rsi
    const macdLineSeries = seriesRefs.current.macdLine
    const macdSignalSeries = seriesRefs.current.macdSignal
    const macdHistogramSeries = seriesRefs.current.macdHistogram

    if (!candleSeries || !volumeSeries || !rsiSeries || !macdLineSeries || !macdSignalSeries || !macdHistogramSeries) {
      return
    }

    const candleData = data.map(toCandlestickDatum)
    const resetSeries = shouldResetSeries(previousCandlesRef.current, candleData)

    candleSeries.setData(candleData)
    volumeSeries.setData(showVolume ? toHistogramData(indicatorData.volume) : [])
    indicatorSettings.movingAverages.forEach((movingAverage) => {
      seriesRefs.current.movingAverages.get(movingAverage.id)?.setData(
        showMovingAverages
          ? toLineData(indicatorData.movingAverages[movingAverage.id] ?? [])
          : [],
      )
    })
    rsiSeries.setData(toLineData(indicatorData.rsi))
    macdLineSeries.setData(toLineData(indicatorData.macd.macdLine))
    macdSignalSeries.setData(toLineData(indicatorData.macd.signalLine))
    macdHistogramSeries.setData(toHistogramData(
      indicatorData.macd.histogram.map((point) => ({
        ...point,
        color: point.value >= 0 ? CHART_COLORS.macdPositive : CHART_COLORS.macdNegative,
      })),
    ))
    markerPluginRef.current?.setMarkers(markerData)

    if (resetSeries) {
      if (!hasInitialFitRef.current || autoFollowRef.current) {
        chartRef.current?.timeScale().fitContent()
        hasInitialFitRef.current = true
      }
    } else if (
      autoFollowRef.current
      && hasInitialFitRef.current
      && chartRef.current
      && previousCandlesRef.current[previousCandlesRef.current.length - 1]?.time !== candleData[candleData.length - 1]?.time
    ) {
      chartRef.current.timeScale().scrollToRealTime()
    }

    previousCandlesRef.current = candleData
  }, [data, indicatorData, indicatorSettings.movingAverages, markerData, showMovingAverages, showVolume])

  return (
    <Box
      sx={{
        position: 'relative',
        width: '100%',
        height: height ?? '100%',
        minHeight: 0,
        flexGrow: 1,
        alignSelf: 'stretch',
        borderRadius: 0,
        overflow: 'hidden',
      }}
    >
      <Box
        ref={containerRef}
        sx={{
          position: 'absolute',
          inset: 0,
        }}
      />
      <Box
        ref={(node: HTMLDivElement | null) => {
          tooltipRefs.current.root = node
        }}
        sx={{
          position: 'absolute',
          top: 0,
          left: 0,
          zIndex: 3,
          width: 196,
          px: 1.25,
          py: 1,
          borderRadius: 1,
          bgcolor: 'rgba(16, 24, 39, 0.96)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          boxShadow: '0 12px 24px rgba(0, 0, 0, 0.32)',
          pointerEvents: 'none',
          opacity: 0,
          visibility: 'hidden',
          transform: 'translate(12px, 12px)',
          transition: 'opacity 120ms ease',
        }}
      >
        <Box
          ref={(node: HTMLDivElement | null) => {
            tooltipRefs.current.time = node
          }}
          sx={{
            mb: 0.75,
            color: '#e2e8f0',
            fontSize: 11,
            fontWeight: 600,
            lineHeight: 1.2,
          }}
        />
        <Box sx={{ display: 'grid', gridTemplateColumns: 'auto 1fr', columnGap: 1, rowGap: 0.25, fontSize: 11, lineHeight: 1.25 }}>
          <Box sx={{ color: '#94a3b8' }}>시가</Box>
          <Box ref={(node: HTMLSpanElement | null) => { tooltipRefs.current.open = node }} component="span" sx={{ color: '#e5e7eb', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }} />
          <Box sx={{ color: '#94a3b8' }}>고가</Box>
          <Box ref={(node: HTMLSpanElement | null) => { tooltipRefs.current.high = node }} component="span" sx={{ color: '#f87171', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }} />
          <Box sx={{ color: '#94a3b8' }}>저가</Box>
          <Box ref={(node: HTMLSpanElement | null) => { tooltipRefs.current.low = node }} component="span" sx={{ color: '#60a5fa', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }} />
          <Box sx={{ color: '#94a3b8' }}>종가</Box>
          <Box ref={(node: HTMLSpanElement | null) => { tooltipRefs.current.close = node }} component="span" sx={{ color: '#f8fafc', textAlign: 'right', fontWeight: 700, fontVariantNumeric: 'tabular-nums' }} />
          <Box sx={{ color: '#94a3b8' }}>거래량</Box>
          <Box ref={(node: HTMLSpanElement | null) => { tooltipRefs.current.volume = node }} component="span" sx={{ color: '#cbd5e1', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }} />
        </Box>
      </Box>
    </Box>
  )
}
