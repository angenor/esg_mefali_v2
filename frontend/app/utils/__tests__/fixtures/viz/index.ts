// F40 T044 — Fixtures partagées pour la viz library (showcase + tests).
import type {
  CategorySeries,
  ChartSeries,
  ColumnDef,
  KPICardProps,
  MapPin,
  MermaidPayload,
  MoneyValue,
  PieSeries,
  RadarSeries,
} from '~/types/viz/chart'
import type { SourceRef } from '~/types/viz/source'

export const KPI_SAMPLES: KPICardProps[] = [
  { label: 'Score E', value: 72, unit: '/100', delta: 5, deltaUnit: 'pts', source_id: 'src_demo' },
  { label: 'Émissions tCO2e', value: 1240, unit: 't', delta: -8, deltaUnit: '%' },
  { label: 'Effectif', value: 87, unit: 'pers.' },
]

export const LINE_SERIES: ChartSeries[] = [
  {
    label: 'Score E',
    points: Array.from({ length: 12 }, (_, i) => ({ x: `M${i + 1}`, y: 50 + Math.sin(i / 2) * 15 + i })),
  },
]

export const BAR_SERIES: CategorySeries = {
  labels: ['Énergie', 'Eau', 'Déchets', 'Genre', 'Santé', 'Conformité'],
  datasets: [{ label: '2024', data: [62, 58, 70, 80, 65, 72] }],
}

export const STACKED_SERIES: CategorySeries = {
  labels: ['Q1', 'Q2', 'Q3', 'Q4'],
  datasets: [
    { label: 'Énergie', data: [10, 12, 11, 14] },
    { label: 'Eau', data: [5, 6, 5, 7] },
    { label: 'Déchets', data: [3, 4, 4, 5] },
  ],
}

export const RADAR_ESG: RadarSeries = {
  axes: ['Climat', 'Eau', 'Biodiv.', 'Travail', 'Communauté', 'Gouvernance'],
  datasets: [{ label: 'Société X', data: [70, 60, 50, 75, 65, 80] }],
}

export const PIE_SAMPLE: PieSeries = {
  labels: ['Renouvelable', 'Fossile', 'Nucléaire', 'Autre'],
  data: [45, 30, 15, 10],
}

export const MERMAID_VALID: MermaidPayload = {
  script: 'graph TD; A[Audit ESG] --> B[Score]; B --> C[Plan d\'action]',
}

export const MERMAID_INVALID: MermaidPayload = {
  script: 'this is not a valid mermaid script @@@@',
}

export const TABLE_COLUMNS: ColumnDef<TableRow>[] = [
  { key: 'id', label: 'ID', type: 'text', searchable: false },
  { key: 'nom', label: 'Nom', type: 'text', searchable: true },
  { key: 'pays', label: 'Pays', type: 'badge' },
  { key: 'date', label: 'Date', type: 'date' },
  { key: 'effectif', label: 'Effectif', type: 'number' },
  { key: 'ca', label: 'CA', type: 'money' },
]

export interface TableRow {
  id: string
  nom: string
  pays: string
  date: string
  effectif: number
  ca: MoneyValue
  source_id?: string
}

export function makeTableRows(n: number): TableRow[] {
  const pays = ['CI', 'SN', 'BJ', 'TG', 'BF', 'ML']
  return Array.from({ length: n }, (_, i) => ({
    id: `pme-${i.toString().padStart(4, '0')}`,
    nom: i % 3 === 0 ? `PME Atlantique ${i}` : `Coopérative ${i}`,
    pays: pays[i % pays.length]!,
    date: new Date(2024, i % 12, (i % 27) + 1).toISOString().slice(0, 10),
    effectif: 5 + (i % 200),
    ca: { amount: String(1_000_000 + i * 12345), currency: 'XOF' },
  }))
}

export const MAP_PINS_50: MapPin[] = Array.from({ length: 50 }, (_, i) => ({
  lat: 5 + (i % 10) * 1.5,
  lng: -15 + (i % 8) * 2,
  label: `Site ${i + 1}`,
  type: i % 3 === 0 ? 'usine' : 'agence',
}))

export const SOURCE_VALID: SourceRef = {
  source_id: 'src_demo',
  title: 'Rapport GIEC AR6 (résumé décideurs)',
  url: 'https://www.ipcc.ch/report/ar6/',
  pillar: 'E',
  valid_from: '2024-03-01',
  valid_to: null,
  status: 'verified',
  revoked_reason: null,
}

export const SOURCE_REVOKED: SourceRef = {
  ...SOURCE_VALID,
  source_id: 'src_revoked',
  status: 'revoked',
  revoked_reason: 'Méthodologie remplacée en 2025-12',
}
