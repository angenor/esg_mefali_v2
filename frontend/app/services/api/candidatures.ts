// F51 T008 — Service API candidatures (wizard + soumission + suivi).
//
// Cf. specs/051-matching-candidatures-simulateur-ui/contracts/candidatures_api_extensions.md.

import type {
  CandidatureDetail,
  CandidatureRow,
  CandidatureStatut,
  WizardDraftOut,
  WizardDraftPatch,
  WizardSubmitIn,
  WizardSubmitOut,
} from "~/types/candidatures"

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

export interface CandidaturesApi {
  list(): Promise<CandidatureRow[]>
  create(projetId: string, offreId: string): Promise<{ id: string }>
  getDetail(candidatureId: string): Promise<CandidatureDetail>
  patchDraft(
    candidatureId: string,
    patch: WizardDraftPatch,
  ): Promise<WizardDraftOut>
  submit(
    candidatureId: string,
    body: WizardSubmitIn,
  ): Promise<WizardSubmitOut>
  updateStatus(
    candidatureId: string,
    statut: CandidatureStatut,
  ): Promise<unknown>
}

export const candidaturesApi: CandidaturesApi = {
  list() {
    const url = `${apiBase()}/me/candidatures`
    return fetcher()<CandidatureRow[]>(url, { credentials: "include" })
  },
  create(projetId, offreId) {
    const url = `${apiBase()}/me/projets/${encodeURIComponent(projetId)}/candidatures`
    return fetcher()<{ id: string }>(url, {
      method: "POST",
      body: { offre_id: offreId },
      credentials: "include",
      headers: csrfHeader(),
    })
  },
  getDetail(candidatureId) {
    const url = `${apiBase()}/me/candidatures/${encodeURIComponent(candidatureId)}`
    return fetcher()<CandidatureDetail>(url, { credentials: "include" })
  },
  patchDraft(candidatureId, patch) {
    const url = `${apiBase()}/me/candidatures/${encodeURIComponent(candidatureId)}/draft`
    return fetcher()<WizardDraftOut>(url, {
      method: "PATCH",
      body: patch,
      credentials: "include",
      headers: csrfHeader(),
    })
  },
  submit(candidatureId, body) {
    const url = `${apiBase()}/me/candidatures/${encodeURIComponent(candidatureId)}/submit`
    return fetcher()<WizardSubmitOut>(url, {
      method: "POST",
      body,
      credentials: "include",
      headers: csrfHeader(),
    })
  },
  updateStatus(candidatureId, statut) {
    const url = `${apiBase()}/me/candidatures/${encodeURIComponent(candidatureId)}/status`
    return fetcher()<unknown>(url, {
      method: "PATCH",
      body: { statut },
      credentials: "include",
      headers: csrfHeader(),
    })
  },
}
