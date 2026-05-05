// F51 — Helpers de navigation depuis le simulateur.
//
// Les helpers exposes ici sont des fonctions pures (sans I/O ni dependance
// Nuxt) afin de pouvoir etre testees a l'unite.

import type { SimulateurInputs } from "~/types/simulateur"

export interface MatchingNavTarget {
  path: "/matching"
  query: Record<string, string>
}

/**
 * Construit la cible `/matching?montant_max=X&duree_max=Y` a partir des
 * inputs courants du simulateur.
 *
 * Les inputs ont des valeurs par defaut (100k EUR / 60 mois) — la navigation
 * doit donc toujours fonctionner meme si `compute()` n'a jamais reussi
 * (cf. F51 quickstart, US3 SC-006).
 */
export function buildMatchingTargetFromInputs(
  inputs: Pick<SimulateurInputs, "montant" | "duree_mois">,
): MatchingNavTarget {
  const query: Record<string, string> = {}
  const montant = String(inputs.montant.amount ?? "").trim()
  if (montant) query.montant_max = montant
  const duree = inputs.duree_mois
  if (Number.isFinite(duree) && duree > 0) query.duree_max = String(duree)
  return { path: "/matching", query }
}
