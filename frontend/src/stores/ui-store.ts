import { create } from 'zustand'

interface ChartOverlays {
  ma: boolean;
  rsi: boolean;
  volume: boolean;
  signalMarkers: boolean;
  stopTpLines: boolean;
  activeOrders: boolean;
}

interface UiState {
  selectedSessionId: string | null;
  selectedSymbol: string | null;
  sidebarCollapsed: boolean;
  chartTimeframe: string;
  selectedCompareSessionIds: string[];
  chartOverlays: ChartOverlays;
  panelLayoutMode: string;
  setSelectedSession: (id: string | null) => void;
  setSelectedSymbol: (symbol: string | null) => void;
  toggleSidebar: () => void;
  setChartTimeframe: (timeframe: string) => void;
  setCompareSessionIds: (ids: string[]) => void;
  toggleChartOverlay: (overlay: keyof ChartOverlays) => void;
  setPanelLayoutMode: (mode: string) => void;
}

export const useUiStore = create<UiState>((set) => ({
  selectedSessionId: null,
  selectedSymbol: null,
  sidebarCollapsed: false,
  chartTimeframe: '5m',
  selectedCompareSessionIds: [],
  chartOverlays: {
    ma: false,
    rsi: false,
    volume: true,
    signalMarkers: true,
    stopTpLines: true,
    activeOrders: true,
  },
  panelLayoutMode: 'default',
  setSelectedSession: (id) => set({ selectedSessionId: id }),
  setSelectedSymbol: (symbol) => set({ selectedSymbol: symbol }),
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  setChartTimeframe: (timeframe) => set({ chartTimeframe: timeframe }),
  setCompareSessionIds: (ids) => set({ selectedCompareSessionIds: ids }),
  toggleChartOverlay: (overlay) => set((state) => ({
    chartOverlays: {
      ...state.chartOverlays,
      [overlay]: !state.chartOverlays[overlay]
    }
  })),
  setPanelLayoutMode: (mode) => set({ panelLayoutMode: mode }),
}))
