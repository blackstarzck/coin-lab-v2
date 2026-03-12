import { useEffect, useRef } from 'react'
import { createChart, ColorType, CandlestickSeries } from "lightweight-charts";
import type { IChartApi, ISeriesApi, CandlestickData, Time } from 'lightweight-charts'
import { Box, useTheme } from '@mui/material'
import type { CandlePoint } from '@/entities/market/types'

interface CandlestickChartProps {
  data: CandlePoint[]
  width?: number
  height?: number
}

export function CandlestickChart({ data, width, height = 400 }: CandlestickChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const theme = useTheme()

  useEffect(() => {
    if (!chartContainerRef.current) return

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: theme.palette.text.secondary,
      },
      grid: {
        vertLines: { color: theme.border.default },
        horzLines: { color: theme.border.default },
      },
      width: width || chartContainerRef.current.clientWidth,
      height,
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
      },
    })

    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: theme.palette.success.main,
      downColor: theme.palette.error.main,
      borderVisible: false,
      wickUpColor: theme.palette.success.main,
      wickDownColor: theme.palette.error.main,
    })

    chartRef.current = chart
    seriesRef.current = candlestickSeries

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth })
      }
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [theme, width, height])

  useEffect(() => {
    if (seriesRef.current && data.length > 0) {
      const formattedData: CandlestickData<Time>[] = data.map(d => ({
        time: (new Date(d.time).getTime() / 1000) as Time,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      }))
      seriesRef.current.setData(formattedData)
    }
  }, [data])

  return <Box ref={chartContainerRef} sx={{ width: '100%', height }} />
}
