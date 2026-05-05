// F51 T006 — Service API offres (catalogue filtrable global).
//
// Encapsule $fetch + apiBase + JWT cookie. Aucun $fetch direct ailleurs.
// Cf. specs/051-matching-candidatures-simulateur-ui/contracts/matching_api_extensions.md.

import type {
  MatchingFilters,
  OffreDetail,
  OffreListOut,
} from "~/types/matching"

interface RuntimeConfigShape {
  public?: { apiBase?: string }
}

function apiBase(): string {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const g = globalThis as any
  const cfg =
    (g.useRuntimeConfig?.() as RuntimeConfigShape | undefined) ??
    (g.useNuxtApp?.()?.$config as RuntimeConfigShape | undefined)
  return String(cfg?.public?.apiBase ?? "").replace(/\/$/, "")
}

type FetchFn = <T>(u: string, o?: Record<string, unknown>) => Promise<T>

function fetcher(): FetchFn {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const f = (globalThis as any).$fetch as FetchFn | undefined
  if (!f) throw new Error("$fetch unavailable")
  return f
}

export interface OffresApi {
  list(filters: MatchingFilters & { limit?: number }): Promise<OffreListOut>
  getDetail(offreId: string): Promise<OffreDetail>
}

export const offresApi: OffresApi = {
  list(filters) {
    const url = `${apiBase()}/me/offres`
    const query: Record<string, unknown> = {}
    if (filters.type) query.type = filters.type
    if (filters.montant_min_eur !== undefined)
      query.montant_min_eur = filters.montant_min_eur
    if (filters.montant_max_eur !== undefined)
      query.montant_max_eur = filters.montant_max_eur
    if (filters.duree_min_mois !== undefined)
      query.duree_min_mois = filters.duree_min_mois
    if (filters.duree_max_mois !== undefined)
      query.duree_max_mois = filters.duree_max_mois
    if (filters.intermediaire_id) query.intermediaire_id = filters.intermediaire_id
    if (filters.secteur) query.secteur = filters.secteur
    if (filters.q) query.q = filters.q
    if (filters.limit) query.limit = filters.limit
    return fetcher()<OffreListOut>(url, { query, credentials: "include" })
  },
  getDetail(offreId) {
    const url = `${apiBase()}/me/offres/${encodeURIComponent(offreId)}`
    return fetcher()<OffreDetail>(url, { credentials: "include" })
  },
}
