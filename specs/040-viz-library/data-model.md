# Phase 1 — Data Model (UI / Store / Types)

**Feature** : 040-viz-library
**Date** : 2026-05-03

F40 ne touche à aucune table de base. Le « modèle de données » se situe entièrement côté frontend : types TypeScript partagés, structure du store Pinia, et contrat de l'endpoint de résolution des sources (voir `contracts/sources-resolve.openapi.yaml`).

---

## 1. Types TypeScript

### 1.1 `SourceRef` — `frontend/app/types/viz/source.ts`

```ts
export type SourcePillar =
  | 'E'
  | 'S'
  | 'G'
  | 'financial'
  | 'regulatory'
  | 'methodology'

export type SourceStatus = 'verified' | 'revoked'

export interface SourceRef {
  source_id: string           // UUID
  title: string
  url: string                 // absolute URL, validated by backend
  pillar: SourcePillar        // closed enum
  valid_from: string          // ISO-8601 date (YYYY-MM-DD)
  valid_to?: string | null    // ISO-8601 date or null = open
  status: SourceStatus
  revoked_reason?: string | null  // present when status === 'revoked'
}
```

**Validation** :
- `pillar` ∈ enum fermé (FR-009b). Toute valeur inconnue est traitée comme erreur d'intégration : log côté front + fallback badge neutre, pas de crash.
- `status` ∈ `{verified, revoked}`. `revoked` déclenche l'icône warning dans `<VizSourcePin>` (FR-009).
- `url` n'est pas re-validée côté front (responsabilité backend P1) ; l'ouverture du lien utilise systématiquement `target="_blank"` + `rel="noopener noreferrer"`.

**Origine** : résolu via `useSourcesStore().resolve(source_id)` qui appelle `GET /api/sources/{id}`.

---

### 1.2 `MoneyValue` — `frontend/app/types/viz/chart.ts`

```ts
export interface MoneyValue {
  amount: string              // sérialisation Decimal — JAMAIS number/float (P5)
  currency: string            // ISO 4217 — XOF, EUR, USD, …
}
```

**Validation** : `amount` doit être une chaîne convertible en `BigInt`/`Decimal` ; le formatage passe exclusivement par `formatMoney(value, locale='fr-FR')` exposé par `frontend/app/utils/moneyFormat.ts`.

---

### 1.3 `VizSize` et `BaseChartProps`

```ts
export type VizSize = 'sm' | 'md' | 'lg'

export interface BaseChartProps {
  title?: string
  caption?: string
  source_id?: string
  size?: VizSize              // défaut 'md'
  loading?: boolean           // défaut false — masque le contenu, affiche skeleton
  empty?: boolean             // défaut false — masque le contenu, affiche EmptyState
  // a11y (WCAG 2.1 AA)
  ariaLabel?: string          // défaut : auto-généré à partir de title + caption
  longDescription?: string    // texte alternatif détaillé (sr-only)
}
```

---

### 1.4 `ColumnDef` (DataTable) — `frontend/app/types/viz/chart.ts`

```ts
export type ColumnType = 'text' | 'number' | 'date' | 'badge' | 'money'

export interface ColumnDef<Row = Record<string, unknown>> {
  key: keyof Row & string
  label: string
  type: ColumnType
  format?: string             // ex. 'YYYY-MM-DD' pour date, 'fr-FR' pour number
  sortable?: boolean          // défaut true
  searchable?: boolean        // défaut true pour text/badge, false pour number/date/money
  align?: 'left' | 'center' | 'right'  // défaut auto selon type
}

export interface DataTableProps<Row = Record<string, unknown>> {
  rows: Row[]
  columns: ColumnDef<Row>[]
  emptyMessage?: string       // défaut 'Aucune donnée disponible'
  paginate?: { pageSize: number }   // si défini, désactive la virtualisation (FR-011)
  // a11y
  ariaLabel?: string
}
```

**Règles** :
- Quand `rows.length > 100` et `paginate` non défini → virtualisation `RecycleScroller` (R4).
- Quand `paginate` défini → mode paginé classique, virtualisation désactivée.
- Cellule `type: 'money'` reçoit obligatoirement un `MoneyValue` ; toute valeur `number` brute déclenche un warning console + fallback affichage `--`.

---

### 1.5 `MapPin` (LeafletMap) — `frontend/app/types/viz/chart.ts`

```ts
export interface MapPin {
  lat: number                 // -90..90
  lng: number                 // -180..180
  label?: string              // texte affiché dans le tooltip
  type?: string               // catégorie pour styling/icône
}
```

**Règles** : aucun identifiant utilisateur sensible n'est stocké dans `MapPin` (RGPD).

---

### 1.6 `MermaidPayload` (MermaidRenderer) — `frontend/app/types/viz/chart.ts`

```ts
export interface MermaidPayload {
  script: string              // source mermaid brut
  diagramId?: string          // id stable pour réémissions
}
```

**Règles** : le rendu produit un SVG passé par DOMPurify (profil `svg + svgFilters`) avant injection (R2).

---

## 2. Store Pinia — `frontend/app/stores/sources.ts`

```ts
interface SourcesState {
  cache: Map<string, { data: SourceRef; fetchedAt: number }>
  inFlight: Map<string, Promise<SourceRef>>
}
```

**API exposée** :
- `resolve(source_id: string): Promise<SourceRef>` — résolution avec cache TTL 5 min + dédoublonnage (R3).
- `peek(source_id: string): SourceRef | undefined` — lecture cache sans fetch (utile pour rendu immédiat si déjà connu).
- `invalidate(source_id?: string): void` — purge entrée(s) du cache (préparation P8 future).
- `reset(): void` — purge totale (utile en tests).

**TTL** : `5 * 60 * 1000 ms`. Constante exposée pour les tests (`SOURCES_TTL_MS`).

**Erreurs** :
- `404` → propage une `SourceNotFoundError` ; le pin reste invisible (US5 #3).
- `5xx` ou réseau → propage une erreur générique ; le pin reste invisible mais log console pour diagnostic (fail-silent côté UI).
- Pas de retry automatique (responsabilité du composant qui peut re-déclencher au prochain clic).

---

## 3. Composable `useChartTheme()` — `frontend/app/composables/useChartTheme.ts`

```ts
interface ChartTheme {
  palette: string[]                     // couleurs catégorielles ordonnées
  fonts: { family: string; size: number; weight: number }
  tooltip: { bg: string; fg: string; border: string; padding: number }
  animations: { duration: number; easing: string; reducedMotion: boolean }
  grid: { color: string; lineWidth: number }
  axis: { color: string; tick: string }
}

export function useChartTheme(): ChartTheme
```

**Lecture** : valeurs lues à partir des CSS variables F36 via `getComputedStyle(document.documentElement)`. Le composable observe `window.matchMedia('(prefers-reduced-motion: reduce)')` pour fixer `animations.reducedMotion = true` (FR-012).

---

## 4. Données de showcase (fixtures `/dev/viz-showcase`)

Les fixtures vivent dans `frontend/app/pages/dev/viz-showcase.vue` (inline `const`) ou dans `frontend/app/utils/__tests__/fixtures/viz/`. Elles couvrent :
- 1 KPI avec delta + source_id
- 1 KPI sans delta sans source_id
- 1 LineChart 12 points / 1 mois
- 1 AreaChart même série
- 1 BarChart 6 catégories + 1 StackedBar 3 séries
- 1 RadarChart 6 axes E/S/G
- 1 GaugeChart valeur 68
- 1 PieChart + 1 DonutChart 4 segments
- 1 MermaidRenderer flowchart valide + 1 invalide
- 1 DataTable 12 lignes (toutes les colonnes types)
- 1 DataTable 1000 lignes (mode virtualisé)
- 1 LeafletMap 50 pins Afrique de l'Ouest
- 1 EmptyState + 1 LoadingState

---

## 5. Relations & contraintes de cohérence

```
BaseChartProps  <─ étend ─  KPICardProps, LineChartProps, BarChartProps, RadarChartProps,
                              GaugeChartProps, PieChartProps, DonutChartProps,
                              MermaidRendererProps, LeafletMapProps
DataTableProps  ─ utilise ─ ColumnDef[]
ColumnDef.type='money'  ─ exige ─ Row[key] : MoneyValue
SourceRef       ─ produit par ─ useSourcesStore().resolve()
VizSourcePin    ─ consomme ─ useSourcesStore().resolve()
ChartTheme      ─ consommé par ─ tous les composants chart
```

**Invariants** :
- I1 : aucun composant `<Viz*>` n'expose de prop modifiant l'état (`v-model`, callbacks de soumission). Audit statique requis (SC-008).
- I2 : tout `MoneyValue` traversant un composant garde `amount: string`. Audit statique requis (SC-009).
- I3 : tout chart ayant des données respecte le couple `loading/empty` mutuellement exclusif et prioritaire sur le rendu.
- I4 : `<VizSourcePin>` ne rend rien si `resolve()` rejette (fail-silent).
