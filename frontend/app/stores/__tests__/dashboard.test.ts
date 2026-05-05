// F44 T005 — Tests vitest store dashboard PME.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { createPinia, setActivePinia } from "pinia"
import { useDashboardStore, type DashboardSummaryOut } from "../dashboard"

declare global {
  // eslint-disable-next-line no-var
  var $fetch: unknown
  // eslint-disable-next-line no-var
  var useRuntimeConfig: unknown
}

const FIXTURE: DashboardSummaryOut = {
  account_id: "acc-1",
  scores: [
    {
      referentiel_code: "GCF",
      referentiel_version: 2,
      score_global: "62.50",
      coverage_ratio: "0.84",
      computed_at: "2026-05-01T10:00:00Z",
    },
  ],
  carbon: [{ year: 2025, total_tco2e: "120.4", computed_at: "2026-04-22T08:00:00Z" }],
  credit_score: {
    solvabilite: 70,
    impact_vert: 65,
    combine: 68,
    methodologie_version: 1,
    coherence_warning: false,
    computed_at: "2026-04-30T12:00:00Z",
  },
  candidatures: { counters_by_statut: { en_cours: 2 }, total: 2, recent: [] },
  rapports: { total: 0, recent: [] },
  attestations: { active: 0, revoked: 0, recent: [] },
  next_actions: [],
  generated_at: "2026-05-03T08:00:00Z",
}

describe("useDashboardStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    globalThis.useRuntimeConfig = () => ({ public: { apiBase: "http://api" } })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("fetchSummary() met à jour state.summary", async () => {
    globalThis.$fetch = vi.fn().mockResolvedValue(FIXTURE)
    const store = useDashboardStore()
    await store.fetchSummary()
    expect(store.summary?.account_id).toBe("acc-1")
    expect(store.generatedAt).toBe("2026-05-03T08:00:00Z")
    expect(store.loading).toBe(false)
    expect(store.blockErrors).toEqual({})
  })

  it("fetchSummary({ scope: ['scores'] }) n'écrit que la clé scores", async () => {
    const store = useDashboardStore()
    // Premier load complet.
    globalThis.$fetch = vi.fn().mockResolvedValue(FIXTURE)
    await store.fetchSummary()
    // Second appel scope = scores avec nouveau score.
    const updated: DashboardSummaryOut = {
      ...FIXTURE,
      scores: [
        {
          referentiel_code: "GCF",
          referentiel_version: 2,
          score_global: "75.00",
          coverage_ratio: "0.9",
          computed_at: "2026-05-02T10:00:00Z",
        },
      ],
      carbon: [], // doit être ignoré dans scope=scores
    }
    globalThis.$fetch = vi.fn().mockResolvedValue(updated)
    await store.fetchSummary({ scope: ["scores"] })
    expect(store.summary?.scores[0]?.score_global).toBe("75.00")
    // carbon n'a pas été écrasé.
    expect(store.summary?.carbon.length).toBe(1)
  })

  it("invalidate('carbon') ajoute la clé à invalidatedBlocks", () => {
    const store = useDashboardStore()
    store.invalidate("carbon")
    expect(store.invalidatedBlocks.has("carbon")).toBe(true)
  })

  it("deux fetchSummary() simultanés sont serialisés", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(FIXTURE)
    globalThis.$fetch = fetchSpy
    const store = useDashboardStore()
    const p1 = store.fetchSummary()
    const p2 = store.fetchSummary()
    await Promise.all([p1, p2])
    // Le second appel a attendu le premier ; on n'a fait qu'un seul HTTP.
    expect(fetchSpy).toHaveBeenCalledTimes(1)
  })

  it("reset() purge tout", async () => {
    globalThis.$fetch = vi.fn().mockResolvedValue(FIXTURE)
    const store = useDashboardStore()
    await store.fetchSummary()
    store.invalidate("scores")
    store.reset()
    expect(store.summary).toBeNull()
    expect(store.generatedAt).toBeNull()
    expect(store.invalidatedBlocks.size).toBe(0)
    expect(store.blockErrors).toEqual({})
  })

  it("erreur fetch → state.blockErrors['*'] renseigné", async () => {
    globalThis.$fetch = vi.fn().mockRejectedValue(new Error("boom"))
    const store = useDashboardStore()
    await store.fetchSummary()
    expect(store.blockErrors["*"]).toBe("boom")
    expect(store.loading).toBe(false)
  })

  it("erreur fetch sur scope ciblé → blockErrors[block] renseigné", async () => {
    globalThis.$fetch = vi.fn().mockRejectedValue(new Error("network"))
    const store = useDashboardStore()
    await store.fetchSummary({ scope: ["scores"] })
    expect(store.blockErrors.scores).toBe("network")
  })
})
