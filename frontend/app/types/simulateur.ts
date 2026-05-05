// F51 T005 — Types partagés pour le simulateur de financement.

import type { Money } from "~/types/matching"

export type TypeInvestissement =
  | "renouvelable_solaire"
  | "renouvelable_eolien"
  | "efficacite_energetique"
  | "agriculture_durable"
  | "mobilite_electrique"
  | "autre"

export interface SimulateurInputs {
  montant: Money
  duree_mois: number
  type_investissement: TypeInvestissement
  part_subvention_pct: number // [0..100]
}

export interface MensualiteEntry {
  mois: number
  amount: string
  currency: "XOF" | "EUR"
}

export interface SimulationResults {
  mensualites: MensualiteEntry[]
  cout_total: Money
  economie_estimee: Money
  co2_evite_t: string
  decomposition_pct: {
    principal: number
    interets: number
    subvention: number
  }
  formula_refs: { formula_id: string; version: string }[]
  computed_at?: string
}

export interface SimulationSavedRow {
  id: string
  label: string
  projet_id: string | null
  offre_id: string | null
  hypotheses: SimulateurInputs
  results_summary: {
    cout_total: Money
    co2_evite_t: string
  }
  created_at: string
}

export interface SimulationSavedDetail extends Omit<SimulationSavedRow, "results_summary"> {
  results: SimulationResults
}

export interface SimulationSaveIn {
  label: string
  projet_id: string | null
  offre_id: string | null
  hypotheses: SimulateurInputs
  results: SimulationResults
}

export interface SimulationListOut {
  items: SimulationSavedRow[]
  count: number
  next_cursor: string | null
}

export interface SimulationComputeIn {
  projet_id: string | null
  offre_id: string | null
  hypotheses: SimulateurInputs
}
