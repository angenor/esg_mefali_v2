// F44 T032 — Helper de mapping de libellés statut candidature.
//
// Source de vérité : clés i18n `dashboard.statut.candidature.*` dans
// `frontend/app/locales/fr.ts`. Ce module sert d'aide centralisée pour
// les composants qui souhaitent un libellé sans dépendre d'un `t()`.
import type { LocaleKey } from "~/composables/useT"

export type CandidatureStatut =
  | "brouillon"
  | "en_cours"
  | "soumise"
  | "acceptee"
  | "refusee"
  | "retiree"
  | "archivee"

export function statutI18nKey(statut: string): LocaleKey {
  return `dashboard.statut.candidature.${statut}` as LocaleKey
}

export function knownStatuts(): readonly CandidatureStatut[] {
  return [
    "brouillon",
    "en_cours",
    "soumise",
    "acceptee",
    "refusee",
    "retiree",
    "archivee",
  ] as const
}
