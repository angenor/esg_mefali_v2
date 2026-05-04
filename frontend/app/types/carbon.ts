// F47 T002 — Types TS miroirs des schémas Pydantic carbon (F28 + extensions F47).
//
// Tous les Decimal sont conservés en `string` côté JS pour préserver la
// précision (P5 constitution). Conversion via `decimal.js` uniquement pour
// agrégation/format final.
//
// Cf. specs/047-empreinte-carbone-ui/data-model.md §3.1.

export type Scope = "1" | "2" | "3"
export type CarbonPosteCode = string

export interface CarbonBreakdownLine {
  code: string
  quantity: string // Decimal
  unit: string
  factor_id: string
  factor_value: string // Decimal kgCO2e/unit
  factor_source_id: string
  factor_version: number
  scope: Scope
  categorie: string
  kgco2e: string // Decimal
  source_id?: string | null // null = ligne legacy F28 sans source PME
}

export interface CarbonFactorVersion {
  factor_id: string
  version: number
  valid_from: string
  source_id: string
}

export interface CarbonFootprint {
  id: string
  year: number
  total_tco2e: string // Decimal
  by_scope_kgco2e: Record<Scope, string> // Decimal
  by_category_kgco2e: Record<string, string>
  breakdown: CarbonBreakdownLine[]
  factor_versions: CarbonFactorVersion[]
  computed_at?: string
  version?: number
}

export interface CarbonIndexEntry {
  footprint_id: string
  year: number
  total_tco2e: string
  computed_at: string
  version: number
}

export interface CarbonIndexOut {
  entries: CarbonIndexEntry[]
}

export interface CarbonSourceItemPayload {
  code: string
  quantity: string // Decimal
  country?: string | null
  source_id?: string | null
}

export interface CarbonEditLineRequest {
  code: string
  quantity: string // Decimal
  country?: string | null
  source_id: string // OBLIGATOIRE
}

export interface CarbonRecomputeResponse extends CarbonFootprint {
  previous_footprint_id: string | null
}

export interface CarbonEditLineResponse extends CarbonFootprint {
  previous_footprint_id: string
  edited_line_code: string
}

// Wizard empty-state — état persisté en localStorage
export interface WizardAnswers {
  energy?: { quantity: string; unit: "kWh" | "MJ"; source_id: string }
  mobility?: { quantity: string; unit: "km" | "litre"; source_id: string }
  purchases?: { quantity: string; unit: "EUR" | "FCFA"; source_id: string }
}

export interface WizardDraft {
  step: 1 | 2 | 3
  year: number
  answers: WizardAnswers
  saved_at: string // ISO timestamp pour TTL 7 jours
}
