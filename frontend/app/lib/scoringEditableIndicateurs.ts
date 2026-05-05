// F46 T003 — MIRROR — keep in sync with backend/app/scoring/value_source.py
// Toute modification de VALUE_SOURCE_MAP côté backend DOIT être reflétée ici.
// Cf. specs/046-scoring-esg-ui/data-model.md §5.2.

export type ScoringEditablePathType = 'number' | 'string' | 'boolean' | 'money'

export interface ScoringEditablePath {
  field: string
  jsonPath?: string
  type: ScoringEditablePathType
}

export const SCORING_EDITABLE_INDICATEUR_CODES: ReadonlySet<string> = new Set([
  'EFFECTIFS_TOTAL',
  'DEMO_S1',
  'CA_AMOUNT',
  'DEMO_E1',
  'PAYS_SIEGE',
  'GOUVERNANCE_BOARD_INDEPENDENCE',
  'GOUVERNANCE_AUDIT_INTERNE',
  'PRATIQUE_POLITIQUE_RSE',
  'PRATIQUE_BILAN_CARBONE',
  'DEMO_G1',
])

export const SCORING_INDICATEUR_TO_ENTREPRISE_PATH: Readonly<
  Record<string, ScoringEditablePath>
> = {
  EFFECTIFS_TOTAL: { field: 'taille_effectifs', type: 'number' },
  DEMO_S1: { field: 'taille_effectifs', type: 'number' },
  CA_AMOUNT: { field: 'taille_ca_amount', type: 'money' },
  DEMO_E1: { field: 'taille_ca_amount', type: 'money' },
  PAYS_SIEGE: { field: 'localisation_siege_pays_iso2', type: 'string' },
  GOUVERNANCE_BOARD_INDEPENDENCE: {
    field: 'gouvernance_json',
    jsonPath: 'board_independence',
    type: 'boolean',
  },
  GOUVERNANCE_AUDIT_INTERNE: {
    field: 'gouvernance_json',
    jsonPath: 'audit_interne',
    type: 'boolean',
  },
  PRATIQUE_POLITIQUE_RSE: {
    field: 'pratiques_actuelles_json',
    jsonPath: 'politique_rse',
    type: 'boolean',
  },
  PRATIQUE_BILAN_CARBONE: {
    field: 'pratiques_actuelles_json',
    jsonPath: 'bilan_carbone',
    type: 'boolean',
  },
  DEMO_G1: {
    field: 'gouvernance_json',
    jsonPath: 'audit_interne',
    type: 'boolean',
  },
}
