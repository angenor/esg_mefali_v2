// F51 T009 — Service API simulateur (calcul + historique sauvegardé).

import type {
  SimulationComputeIn,
  SimulationListOut,
  SimulationResults,
  SimulationSavedDetail,
  SimulationSaveIn,
} from "~/types/simulateur"

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

export interface SimulateurApi {
  compute(req: SimulationComputeIn, signal?: AbortSignal): Promise<SimulationResults>
  save(body: SimulationSaveIn): Promise<{ id: string; label: string; created_at: string }>
  listHistory(limit?: number): Promise<SimulationListOut>
  getDetail(id: string): Promise<SimulationSavedDetail>
  softDelete(id: string): Promise<void>
}

export const simulateurApi: SimulateurApi = {
  compute(req, signal) {
    const url = `${apiBase()}/me/simulations`
    return fetcher()<SimulationResults>(url, {
      method: "POST",
      body: req,
      credentials: "include",
      headers: csrfHeader(),
      signal,
    })
  },
  save(body) {
    const url = `${apiBase()}/me/simulations/save`
    return fetcher()<{ id: string; label: string; created_at: string }>(url, {
      method: "POST",
      body,
      credentials: "include",
      headers: csrfHeader(),
    })
  },
  listHistory(limit = 20) {
    const url = `${apiBase()}/me/simulations`
    return fetcher()<SimulationListOut>(url, {
      method: "GET",
      query: { limit },
      credentials: "include",
    })
  },
  getDetail(id) {
    const url = `${apiBase()}/me/simulations/${encodeURIComponent(id)}`
    return fetcher()<SimulationSavedDetail>(url, { credentials: "include" })
  },
  softDelete(id) {
    const url = `${apiBase()}/me/simulations/${encodeURIComponent(id)}`
    return fetcher()<void>(url, {
      method: "DELETE",
      credentials: "include",
      headers: csrfHeader(),
    })
  },
}
