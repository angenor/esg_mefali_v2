// F40 T014 — exports lazy de la viz library + types.
import { defineAsyncComponent, inject, type InjectionKey } from 'vue'

// Sentinel posée par F39 quand un composant viz est monté à l'intérieur d'un
// bottom sheet (P10) — usage incorrect : viz est display-only en bulle, pas
// dans un sheet. T049 : guard runtime tolérant (warning console.dev).
export const BOTTOM_SHEET_CTX: InjectionKey<true> = Symbol('__BOTTOM_SHEET_CTX__')

export function assertNotInsideBottomSheet(componentName: string): void {
  if (typeof process !== 'undefined' && process.env?.NODE_ENV === 'production') return
  const flag = inject(BOTTOM_SHEET_CTX, false)
  if (flag) {
    // eslint-disable-next-line no-console
    console.warn(
      `[viz] ${componentName} monté à l'intérieur d'un bottom sheet — display-only attendu en bulle, pas en sheet (P10).`,
    )
  }
}

// Composants légers chargés directement (pas de chunk asynchrone)
export { default as VizSourcePin } from './VizSourcePin.vue'
export { default as VizKPICard } from './VizKPICard.vue'
export { default as VizLoadingState } from './VizLoadingState.vue'
export { default as VizEmptyState } from './VizEmptyState.vue'

// Composants lourds : lazy via defineAsyncComponent → chart.js / mermaid /
// leaflet ne chargent que sur demande (NFR-004 / SC-007).
export const VizLineChart = defineAsyncComponent(() => import('./VizLineChart.vue'))
export const VizAreaChart = defineAsyncComponent(() => import('./VizAreaChart.vue'))
export const VizBarChart = defineAsyncComponent(() => import('./VizBarChart.vue'))
export const VizStackedBarChart = defineAsyncComponent(() => import('./VizStackedBarChart.vue'))
export const VizRadarChart = defineAsyncComponent(() => import('./VizRadarChart.vue'))
export const VizGaugeChart = defineAsyncComponent(() => import('./VizGaugeChart.vue'))
export const VizPieChart = defineAsyncComponent(() => import('./VizPieChart.vue'))
export const VizDonutChart = defineAsyncComponent(() => import('./VizDonutChart.vue'))
export const VizMermaidRenderer = defineAsyncComponent(() => import('./VizMermaidRenderer.vue'))
export const VizDataTable = defineAsyncComponent(() => import('./VizDataTable.vue'))
export const VizLeafletMap = defineAsyncComponent(() => import('./VizLeafletMap.vue'))

// Types réexportés pour confort consommateur.
export type {
  BaseChartProps,
  ChartSeries,
  ChartSeriesPoint,
  CategorySeries,
  ColumnDef,
  ColumnType,
  DataTableProps,
  KPICardProps,
  MapPin,
  MermaidPayload,
  MoneyValue,
  PieSeries,
  RadarSeries,
  VizSize,
} from '~/types/viz/chart'
export type {
  SourcePillar,
  SourceRef,
  SourceStatus,
} from '~/types/viz/source'
export { SourceNotFoundError, isSourcePillar } from '~/types/viz/source'
