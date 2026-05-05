// F40 T005 — Types partagés des composants <Viz*> (charts, table, mermaid, map).
// Réf. data-model.md §1.2-1.6.

export interface MoneyValue {
  amount: string
  currency: string
}

export type VizSize = 'sm' | 'md' | 'lg'

export interface BaseChartProps {
  title?: string
  caption?: string
  source_id?: string
  size?: VizSize
  loading?: boolean
  empty?: boolean
  ariaLabel?: string
  longDescription?: string
}

export type ColumnType = 'text' | 'number' | 'date' | 'badge' | 'money'

export interface ColumnDef<Row = Record<string, unknown>> {
  key: keyof Row & string
  label: string
  type: ColumnType
  format?: string
  sortable?: boolean
  searchable?: boolean
  align?: 'left' | 'center' | 'right'
}

export interface DataTablePaginate {
  pageSize: number
}

export interface DataTableProps<Row = Record<string, unknown>> {
  rows: Row[]
  columns: ColumnDef<Row>[]
  emptyMessage?: string
  paginate?: DataTablePaginate
  ariaLabel?: string
}

export interface MapPin {
  lat: number
  lng: number
  label?: string
  type?: string
}

export interface MermaidPayload {
  script: string
  diagramId?: string
}

export interface ChartSeriesPoint {
  x: number | string
  y: number
}

export interface ChartSeries {
  label: string
  points: ChartSeriesPoint[]
}

export interface CategorySeries {
  labels: string[]
  datasets: Array<{ label: string; data: number[] }>
}

export interface RadarSeries {
  axes: string[]
  datasets: Array<{ label: string; data: number[] }>
}

export interface PieSeries {
  labels: string[]
  data: number[]
}

export interface KPICardProps {
  label: string
  value: string | number
  unit?: string
  delta?: number
  deltaUnit?: string
  source_id?: string
  size?: VizSize
  loading?: boolean
  empty?: boolean
  ariaLabel?: string
  longDescription?: string
}
