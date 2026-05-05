// F51 T004 — Types partagés pour le wizard de candidature.

import type { Money, OffreType, DocumentRequis } from "~/types/matching"

export type CandidatureStatut =
  | "brouillon"
  | "soumise"
  | "en_revue"
  | "acceptee"
  | "refusee"

export type WizardStepKey = 1 | 2 | 3 | 4 | 5

export interface CandidatureRow {
  id: string
  offre_nom: string
  projet_titre: string
  statut: CandidatureStatut
  step_courant: WizardStepKey
  progression_pct: number
  updated_at: string
  submitted_at: string | null
}

export interface CandidatureOffreSummary {
  id: string
  nom: string
  intermediaire_nom: string
  type: OffreType
  montant_min: Money
  montant_max: Money
  documents_requis: DocumentRequis[]
}

export interface CandidatureProjetSummary {
  id: string
  titre: string
  description: string
}

export interface DocumentLie {
  document_id: string
  checklist_key: string
  filename: string
  uploaded_at: string
}

export interface TimelineEvent {
  ts: string
  event: string
  field?: string
  from?: string | number | null
  to?: string | number | null
  by?: string
  comment?: string | null
}

export interface DraftStep1 {
  offre_id?: string
  projet_id?: string
}

export interface DraftStep2 {
  entreprise_snapshot_at?: string
  entreprise?: Record<string, unknown>
}

export interface DraftStep3 {
  documents_links?: { document_id: string; checklist_key: string }[]
  checklist_completed?: string[]
}

export interface DraftStep4 {
  reponses_libres?: { question: string; reponse: string; asked_at: string }[]
}

export interface DraftStep5 {
  user_acknowledged_intangible?: boolean
  user_confirmed_at?: string
}

export interface DraftSnapshot {
  step1?: DraftStep1
  step2?: DraftStep2
  step3?: DraftStep3
  step4?: DraftStep4
  step5?: DraftStep5
}

export interface CandidatureDetail {
  id: string
  offre: CandidatureOffreSummary
  projet: CandidatureProjetSummary
  statut: CandidatureStatut
  step_courant: WizardStepKey
  progression_pct: number
  draft_snapshot_json: DraftSnapshot
  submitted_at: string | null
  snapshot_json: Record<string, unknown> | null
  timeline: TimelineEvent[]
  documents_lies: DocumentLie[]
  version: number
}

export interface WizardDraftPatch {
  step_courant?: WizardStepKey
  draft_snapshot_json?: Partial<DraftSnapshot>
  expected_version: number
}

export interface WizardDraftOut {
  id: string
  step_courant: WizardStepKey
  progression_pct: number
  draft_snapshot_json: DraftSnapshot
  version: number
  updated_at: string
}

export interface WizardSubmitIn {
  confirmed: true
  expected_version: number
  user_acknowledged_intangible: true
}

export interface WizardSubmitOut {
  id: string
  statut: "soumise"
  submitted_at: string
  snapshot_schema_version: string
  version: number
}

export interface DocumentChecklistItem extends DocumentRequis {
  joined: boolean
  document_id: string | null
}
