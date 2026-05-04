// F47 T006 — Service API carbone (encapsule $fetch + apiBase + JWT cookie).
//
// Pattern miroir de F46 services/api/scoring.ts. Aucun $fetch direct ailleurs
// dans la feature carbone.
//
// Cf. specs/047-empreinte-carbone-ui/contracts/frontend-api-consumption.md.

import type {
  CarbonEditLineRequest,
  CarbonEditLineResponse,
  CarbonFootprint,
  CarbonIndexEntry,
  CarbonIndexOut,
  CarbonRecomputeResponse,
  CarbonSourceItemPayload,
} from "~/types/carbon"

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

function csrfHeader(): Record<string, string> {
  if (typeof document === "undefined") return {}
  const m = document.cookie.match(/(?:^|;\s*)mefali_csrf=([^;]+)/)
  return m ? { "X-CSRF-Token": decodeURIComponent(m[1]!) } : {}
}

export interface CarbonApi {
  fetchIndex(opts?: { limitYears?: number }): Promise<CarbonIndexEntry[]>
  fetchFootprint(year: number): Promise<CarbonFootprint>
  recompute(year: number): Promise<CarbonRecomputeResponse>
  editLine(
    year: number,
    payload: CarbonEditLineRequest,
  ): Promise<CarbonEditLineResponse>
  computeInitial(
    year: number,
    sourceData: CarbonSourceItemPayload[],
  ): Promise<CarbonFootprint>
}

export const carbonApi: CarbonApi = {
  async fetchIndex(opts) {
    const limit = opts?.limitYears
    const url = `${apiBase()}/me/carbon`
    const result = await fetcher()<CarbonIndexOut>(url, {
      credentials: "include",
      query: limit ? { limit_years: limit } : undefined,
    })
    return result.entries
  },
  fetchFootprint(year) {
    const url = `${apiBase()}/me/carbon/${year}`
    return fetcher()<CarbonFootprint>(url, { credentials: "include" })
  },
  recompute(year) {
    const url = `${apiBase()}/me/carbon/${year}/recompute`
    return fetcher()<CarbonRecomputeResponse>(url, {
      method: "POST",
      credentials: "include",
      headers: csrfHeader(),
    })
  },
  editLine(year, payload) {
    const url = `${apiBase()}/me/carbon/${year}/edit-line`
    return fetcher()<CarbonEditLineResponse>(url, {
      method: "POST",
      credentials: "include",
      headers: { ...csrfHeader(), "Content-Type": "application/json" },
      body: payload,
    })
  },
  computeInitial(year, sourceData) {
    const url = `${apiBase()}/me/carbon/compute`
    return fetcher()<CarbonFootprint>(url, {
      method: "POST",
      credentials: "include",
      headers: { ...csrfHeader(), "Content-Type": "application/json" },
      body: { year, source_data: sourceData },
    })
  },
}
