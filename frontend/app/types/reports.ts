// F49 T013 — Types TS pour la liste des rapports + machine d'état de génération.
//
// Cf. specs/049-rapports-attestations-ui/contracts/ui-backend.md §A et data-model.md §1.
// Le backend F24 actuel expose `entity_type` + `entity_id` + `referentiels[]` au
// lieu de `type` + `referentiel_id` + `period_*` du contrat F49 ; le store
// adapte. Les types ci-dessous suivent le contrat F49 cible (aligné UI).

export type RapportType = "conformite" | "carbone" | "candidature"

export type RapportStatus = "ready" | "generating" | "failed"

export interface Rapport {
  id: string
  type: RapportType
  referentiel_id: string | null
  period_from: string | null // ISO date "yyyy-MM-dd"
  period_to: string | null
  created_at: string // ISO datetime
  size_bytes: number | null
  status: RapportStatus
  download_filename: string
  hash_sha256?: string | null
  // Champs back F24 pour adaptation
  entity_type?: "entreprise" | "projet"
  entity_id?: string
  referentiels?: string[]
  language?: "fr" | "en"
}

export interface GenerateRequest {
  type: RapportType
  referentiel_id: string | null
  period_from: string
  period_to: string
  // Adaptation F24 : entity_type/entity_id explicites côté UI
  entity_type?: "entreprise" | "projet"
  entity_id?: string
  referentiels?: string[]
  language?: "fr" | "en"
}

export type GenerationPhase =
  | "idle"
  | "pending"
  | "running"
  | "ready"
  | "failed"
  | "downloaded"

export interface GenerationState {
  generation_id: string
  phase: GenerationPhase
  step: string | null
  percent: number
  rapport_id: string | null
  download_filename: string | null
  error: string | null
  last_event_id: number
  started_at: string
}

export interface PreviewUrl {
  url: string
  expires_at: string // ISO datetime
}
