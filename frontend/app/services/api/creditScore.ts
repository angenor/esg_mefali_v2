/**
 * F48 — Service API credit-score (encapsule $fetch + apiBase + JWT cookie).
 *
 * Pattern miroir de F47 services/api/carbon.ts. Aucun $fetch direct ailleurs
 * dans la feature credit-score.
 */

import type {
  CreditDeclarativePayload,
  CreditRecommendationsDTO,
  CreditScoreOut,
  EligibilityListDTO,
  ScoreHistoryOutDTO,
} from '~/types/creditScore'

interface RuntimeConfigShape {
  public?: { apiBase?: string }
}

function apiBase(): string {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const g = globalThis as any
  const cfg
    = (g.useRuntimeConfig?.() as RuntimeConfigShape | undefined)
    ?? (g.useNuxtApp?.()?.$config as RuntimeConfigShape | undefined)
  return String(cfg?.public?.apiBase ?? '').replace(/\/$/, '')
}

type FetchFn = <T>(u: string, o?: Record<string, unknown>) => Promise<T>

function fetcher(): FetchFn {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const f = (globalThis as any).$fetch as FetchFn | undefined
  if (!f) throw new Error('$fetch unavailable')
  return f
}

function csrfHeader(): Record<string, string> {
  if (typeof document === 'undefined') return {}
  const m = document.cookie.match(/(?:^|;\s*)mefali_csrf=([^;]+)/)
  return m ? { 'X-CSRF-Token': decodeURIComponent(m[1]!) } : {}
}

export interface CreditScoreApi {
  fetchScore(): Promise<CreditScoreOut>
  fetchHistory(opts?: { limit?: number }): Promise<ScoreHistoryOutDTO>
  fetchEligibility(): Promise<EligibilityListDTO>
  fetchRecommendations(opts?: { limit?: number }): Promise<CreditRecommendationsDTO>
  submitDeclarative(payload: CreditDeclarativePayload): Promise<unknown>
  recompute(): Promise<CreditScoreOut>
}

export const creditScoreApi: CreditScoreApi = {
  fetchScore() {
    const url = `${apiBase()}/me/credit-score`
    return fetcher()<CreditScoreOut>(url, { credentials: 'include' })
  },
  fetchHistory(opts) {
    const url = `${apiBase()}/me/credit-score/history`
    return fetcher()<ScoreHistoryOutDTO>(url, {
      credentials: 'include',
      query: opts?.limit ? { limit: opts.limit } : undefined,
    })
  },
  fetchEligibility() {
    const url = `${apiBase()}/me/credit-score/eligibility`
    return fetcher()<EligibilityListDTO>(url, { credentials: 'include' })
  },
  fetchRecommendations(opts) {
    const url = `${apiBase()}/me/credit-score/recommendations`
    return fetcher()<CreditRecommendationsDTO>(url, {
      credentials: 'include',
      query: opts?.limit ? { limit: opts.limit } : undefined,
    })
  },
  submitDeclarative(payload) {
    const url = `${apiBase()}/me/credit-data`
    return fetcher()<unknown>(url, {
      method: 'POST',
      credentials: 'include',
      headers: { ...csrfHeader(), 'Content-Type': 'application/json' },
      body: { kind: 'declaratif', payload },
    })
  },
  recompute() {
    const url = `${apiBase()}/me/credit-score/recompute`
    return fetcher()<CreditScoreOut>(url, {
      method: 'POST',
      credentials: 'include',
      headers: csrfHeader(),
    })
  },
}
