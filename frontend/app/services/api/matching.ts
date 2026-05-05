// F51 T007 — Service API matching (scoring projet ↔ offre, F25).

import type { MatchingListOut } from "~/types/matching"

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

export interface MatchingApi {
  listProjetMatching(projetId: string, limit?: number): Promise<MatchingListOut>
  getMatchingDetail(projetId: string, offreId: string): Promise<unknown>
  comparator(fondsId: string, projetId: string, limit?: number): Promise<unknown>
}

export const matchingApi: MatchingApi = {
  listProjetMatching(projetId, limit = 10) {
    const url = `${apiBase()}/me/projets/${encodeURIComponent(projetId)}/matching`
    return fetcher()<MatchingListOut>(url, {
      query: { limit },
      credentials: "include",
    })
  },
  getMatchingDetail(projetId, offreId) {
    const url = `${apiBase()}/me/projets/${encodeURIComponent(projetId)}/matching/${encodeURIComponent(offreId)}`
    return fetcher()<unknown>(url, { credentials: "include" })
  },
  comparator(fondsId, projetId, limit = 5) {
    const url = `${apiBase()}/me/fonds/${encodeURIComponent(fondsId)}/intermediaires-comparator`
    return fetcher()<unknown>(url, {
      query: { projet_id: projetId, limit },
      credentials: "include",
    })
  },
}
