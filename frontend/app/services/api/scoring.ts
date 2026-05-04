// F46 T012 — Service API scoring (encapsule $fetch + apiBase + JWT cookie).
//
// Pattern miroir de F45 — toutes les requêtes scoring passent par ce module ;
// aucun `$fetch` direct ailleurs dans la feature scoring.
//
// Cf. specs/046-scoring-esg-ui/contracts/frontend-api-consumption.md.

import {
  SCORING_INDICATEUR_TO_ENTREPRISE_PATH,
  type ScoringEditablePath,
} from "~/lib/scoringEditableIndicateurs"
import type {
  ScoreDetailOut,
  ScoreHistoryOut,
  ScoreListOut,
} from "~/types/scoring"

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

type FetchFn = <T>(
  u: string,
  o?: Record<string, unknown>,
) => Promise<T>

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

export type EntityType = "entreprise" | "projet"

export interface ScoringApi {
  listSummaries(
    entityType: EntityType,
    entityId: string,
  ): Promise<ScoreListOut>
  getDetail(
    entityType: EntityType,
    entityId: string,
    referentielCode: string,
  ): Promise<ScoreDetailOut>
  recompute(
    entityType: EntityType,
    entityId: string,
    referentielCode: string,
  ): Promise<ScoreDetailOut>
  getHistory(
    entityType: EntityType,
    entityId: string,
    referentielCode: string,
    limit?: number,
  ): Promise<ScoreHistoryOut>
  editIndicateurValue(
    indicateurCode: string,
    newValue: unknown,
    currentEntreprise?: Record<string, unknown> | null,
  ): Promise<unknown>
  exportPdf(payload: ExportPdfPayload): Promise<Blob>
}

export interface ExportPdfPayload {
  entity_type: EntityType
  entity_id: string
  referentiel_code: string
  score_calculation_id?: string | null
}

export const scoringApi: ScoringApi = {
  listSummaries(entityType, entityId) {
    const url = `${apiBase()}/me/scoring/${entityType}/${entityId}`
    return fetcher()<ScoreListOut>(url, { credentials: "include" })
  },
  getDetail(entityType, entityId, referentielCode) {
    const url = `${apiBase()}/me/scoring/${entityType}/${entityId}/${referentielCode}`
    return fetcher()<ScoreDetailOut>(url, { credentials: "include" })
  },
  recompute(entityType, entityId, referentielCode) {
    const url = `${apiBase()}/me/scoring/${entityType}/${entityId}/recompute`
    return fetcher()<ScoreDetailOut>(url, {
      method: "POST",
      query: { referentiel: referentielCode },
      credentials: "include",
      headers: csrfHeader(),
    })
  },
  getHistory(entityType, entityId, referentielCode, limit = 12) {
    const url = `${apiBase()}/me/scoring/${entityType}/${entityId}/${referentielCode}/history`
    return fetcher()<ScoreHistoryOut>(url, {
      query: { limit },
      credentials: "include",
    })
  },
  editIndicateurValue(indicateurCode, newValue, currentEntreprise = null) {
    const path: ScoringEditablePath | undefined =
      SCORING_INDICATEUR_TO_ENTREPRISE_PATH[indicateurCode]
    if (!path) {
      return Promise.reject(new Error("not_editable_here"))
    }
    const body: Record<string, unknown> = {}
    if (path.jsonPath) {
      // merge jsonPath into existing object value to ne pas écraser les autres clés.
      const existing =
        (currentEntreprise?.[path.field] as Record<string, unknown> | null) ??
        null
      body[path.field] = {
        ...(existing ?? {}),
        [path.jsonPath]: newValue,
      }
    } else {
      body[path.field] = newValue
    }
    const url = `${apiBase()}/me/entreprise`
    return fetcher()<unknown>(url, {
      method: "PATCH",
      body,
      credentials: "include",
      headers: csrfHeader(),
    })
  },
  exportPdf(payload) {
    const url = `${apiBase()}/me/rapports/scoring/export`
    return fetcher()<Blob>(url, {
      method: "POST",
      body: payload,
      credentials: "include",
      responseType: "blob",
      headers: csrfHeader(),
    })
  },
}
