import { useEffect, useRef } from 'react'
import { createChart, ColorType, LineSeries } from "lightweight-charts";
import type { IChartApi, ISeriesApi, LineData, Time } from 'lightweight-charts'
import { Box, useTheme } from '@mui/material'

interface LineChartProps {
  data: { time: string; value: number }[]
  width?: number
  height?: number
  color?: string
}

export function LineChart({ data, width, height = 400, color }: LineChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const theme = useTheme()

  const lineColor = color || theme.palette.primary.main

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

    const lineSeries = chart.addSeries(LineSeries, {
      color: lineColor,
      lineWidth: 2,
      crosshairMarkerVisible: true,
      crosshairMarkerRadius: 4,
    })

    chartRef.current = chart
    seriesRef.current = lineSeries

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
  }, [theme, width, height, lineColor])

  useEffect(() => {
    if (seriesRef.current && data.length > 0) {
      const formattedData: LineData<Time>[] = data.map(d => ({
        time: (new Date(d.time).getTime() / 1000) as Time,
        value: d.value,
      }))
      seriesRef.current.setData(formattedData)
    }
  }, [data])

  return <Box ref={chartContainerRef} sx={{ width: '100%', height }} />
}
