// F46 T015 — Tests store useScoringStore.
//
// Cf. specs/046-scoring-esg-ui/data-model.md §3.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { createPinia, setActivePinia } from "pinia"
import {
  useScoringStore,
  SCORING_CACHE_TTL_MS,
} from "../scoring"

declare global {
  // eslint-disable-next-line no-var
  var $fetch: unknown
  // eslint-disable-next-line no-var
  var useRuntimeConfig: unknown
}

// Mock du module services/api/scoring — appels contrôlés.
vi.mock("~/services/api/scoring", () => {
  return {
    scoringApi: {
      listSummaries: vi.fn(),
      getDetail: vi.fn(),
      recompute: vi.fn(),
      getHistory: vi.fn(),
    },
  }
})

import { scoringApi } from "~/services/api/scoring"

const ENT_ID = "11111111-1111-1111-1111-111111111111"
const REF_BOAD = "BOAD"
const REF_CDP = "CDP"

function summaryOut(over: Record<string, unknown> = {}): unknown {
  return {
    referentiel_code: REF_BOAD,
    referentiel_id: "ref-1",
    referentiel_version: 1,
    score_global: 60,
    scores_by_pillar: { E: 60, S: 70, G: 50 },
    coverage_ratio: 0.5,
    computed_at: "2026-05-04T12:00:00Z",
    ...over,
  }
}

function detailOut(over: Record<string, unknown> = {}): unknown {
  return {
    ...(summaryOut() as Record<string, unknown>),
    indicateurs_couverts: [
      {
        indicateur_id: "i1",
        indicateur_code: "EFFECTIFS_TOTAL",
        pillar: "S",
        value: 80,
        normalized_value: 80,
        weight: 1,
        contribution: 30,
        source_id: "s1",
      },
    ],
    indicateurs_manquants: [
      {
        indicateur_id: "i2",
        indicateur_code: "OTHER",
        pillar: "E",
        reason: "value_absent",
      },
    ],
    sources_used: ["s1"],
    ...over,
  }
}

function historyOut(): unknown {
  return {
    entity_type: "entreprise",
    entity_id: ENT_ID,
    referentiel_code: REF_BOAD,
    entries: [
      {
        score_calculation_id: "calc-1",
        computed_at: "2026-05-04T12:00:00Z",
        score_global: 60,
        referentiel_version: 1,
      },
    ],
  }
}

describe("useScoringStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    globalThis.useRuntimeConfig = () => ({ public: { apiBase: "http://api" } })
    vi.mocked(scoringApi.listSummaries).mockReset()
    vi.mocked(scoringApi.getDetail).mockReset()
    vi.mocked(scoringApi.recompute).mockReset()
    vi.mocked(scoringApi.getHistory).mockReset()
  })
  afterEach(() => {
    delete (globalThis as Record<string, unknown>).$fetch
  })

  it("(a) setEntity initialise l'état", () => {
    const s = useScoringStore()
    s.setEntity("entreprise", ENT_ID)
    expect(s.entityType).toBe("entreprise")
    expect(s.entityId).toBe(ENT_ID)
  })

  it("(b) loadSummaries appelle l'API et remplit summariesByRef", async () => {
    vi.mocked(scoringApi.listSummaries).mockResolvedValue({
      entity_type: "entreprise",
      entity_id: ENT_ID,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      scores: [summaryOut() as any, summaryOut({ referentiel_code: REF_CDP }) as any],
    })
    const s = useScoringStore()
    s.setEntity("entreprise", ENT_ID)
    await s.loadSummaries()
    expect(s.summariesByRef[REF_BOAD]).toBeDefined()
    expect(s.summariesByRef[REF_CDP]).toBeDefined()
    expect(s.availableReferentiels).toContain(REF_BOAD)
  })

  it("(c) loadDetail cache 60 s — second appel ne refait pas l'API", async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(scoringApi.getDetail).mockResolvedValue(detailOut() as any)
    const s = useScoringStore()
    s.setEntity("entreprise", ENT_ID)
    await s.loadDetail(REF_BOAD)
    await s.loadDetail(REF_BOAD)
    expect(scoringApi.getDetail).toHaveBeenCalledTimes(1)
    // expire cache → re-fetch
    s.detailsCacheByRef[REF_BOAD]!.fetchedAt = Date.now() - SCORING_CACHE_TTL_MS - 100
    await s.loadDetail(REF_BOAD)
    expect(scoringApi.getDetail).toHaveBeenCalledTimes(2)
  })

  it("(d) loadHistory met à jour historyByRef", async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(scoringApi.getHistory).mockResolvedValue(historyOut() as any)
    const s = useScoringStore()
    s.setEntity("entreprise", ENT_ID)
    await s.loadHistory(REF_BOAD)
    expect(s.historyByRef[REF_BOAD]).toHaveLength(1)
    expect(s.historyByRef[REF_BOAD]![0]!.scoreCalculationId).toBe("calc-1")
  })

  it("(e) setCurrentReferentiel lazy-charge detail+history si manquants", async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(scoringApi.getDetail).mockResolvedValue(detailOut({ referentiel_code: REF_CDP }) as any)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(scoringApi.getHistory).mockResolvedValue(historyOut() as any)
    const s = useScoringStore()
    s.setEntity("entreprise", ENT_ID)
    await s.setCurrentReferentiel(REF_CDP)
    expect(s.currentReferentielCode).toBe(REF_CDP)
    expect(scoringApi.getDetail).toHaveBeenCalledTimes(1)
    expect(scoringApi.getHistory).toHaveBeenCalledTimes(1)
  })

  it("(f) recompute rejette si déjà en cours", async () => {
    const s = useScoringStore()
    s.setEntity("entreprise", ENT_ID)
    s.recomputingByRef[REF_BOAD] = true
    await expect(s.recompute(REF_BOAD)).rejects.toThrow(/already_recomputing/)
  })

  it("(g) editIndicateur rejette en mode snapshot", async () => {
    const s = useScoringStore()
    s.setEntity("entreprise", ENT_ID)
    s.snapshot = {
      active: true,
      frozenCalculationId: "x",
      frozenSummary: null,
      frozenAt: null,
    }
    await expect(
      s.editIndicateur({
        indicateurId: "i1",
        indicateurCode: "EFFECTIFS_TOTAL",
        newValue: 200,
        refCode: REF_BOAD,
      }),
    ).rejects.toThrow(/snapshot_active/)
  })

  it("(h) enterSnapshot charge le summary historique correspondant", async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(scoringApi.listSummaries).mockResolvedValue({
      entity_type: "entreprise",
      entity_id: ENT_ID,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      scores: [summaryOut() as any],
    })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(scoringApi.getHistory).mockResolvedValue(historyOut() as any)
    const s = useScoringStore()
    s.setEntity("entreprise", ENT_ID)
    await s.loadSummaries()
    s.currentReferentielCode = REF_BOAD
    await s.loadHistory(REF_BOAD)
    await s.enterSnapshot("calc-1")
    expect(s.snapshot.active).toBe(true)
    expect(s.snapshot.frozenCalculationId).toBe("calc-1")
    expect(s.snapshot.frozenSummary).not.toBeNull()
    expect(s.isSnapshot).toBe(true)
  })

  it("(i) exitSnapshot repasse en live", () => {
    const s = useScoringStore()
    s.snapshot = {
      active: true,
      frozenCalculationId: "calc-1",
      frozenSummary: null,
      frozenAt: "2026-05-04T12:00:00Z",
    }
    s.exitSnapshot()
    expect(s.snapshot.active).toBe(false)
    expect(s.snapshot.frozenCalculationId).toBeNull()
  })

  it("(j) onChatEntityUpdated{indicateur, meta:{indicateur_code}} invalide caches", async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(scoringApi.getDetail).mockResolvedValue(detailOut() as any)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(scoringApi.getHistory).mockResolvedValue(historyOut() as any)
    const s = useScoringStore()
    s.setEntity("entreprise", ENT_ID)
    s.currentReferentielCode = REF_BOAD
    await s.loadDetail(REF_BOAD)
    await s.loadHistory(REF_BOAD)
    expect(s.detailsCacheByRef[REF_BOAD]).toBeDefined()
    s.onChatEntityUpdated({
      entityType: "indicateur",
      entityId: "i1",
      source: "tool",
      meta: { indicateur_code: "EFFECTIFS_TOTAL" },
    })
    expect(s.detailsCacheByRef[REF_BOAD]).toBeUndefined()
    expect(s.historyCacheByRef[REF_BOAD]).toBeUndefined()
  })

  it("(k) onChatEntityUpdated{score_calculation} invalide detail+history seulement", async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(scoringApi.getDetail).mockResolvedValue(detailOut() as any)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(scoringApi.getHistory).mockResolvedValue(historyOut() as any)
    const s = useScoringStore()
    s.setEntity("entreprise", ENT_ID)
    s.currentReferentielCode = REF_BOAD
    await s.loadDetail(REF_BOAD)
    await s.loadHistory(REF_BOAD)
    s.summariesByRef[REF_BOAD] = s.detailsByRef[REF_BOAD]!
    s.onChatEntityUpdated({
      entityType: "score_calculation",
      entityId: "calc-2",
      source: "tool",
    })
    expect(s.detailsCacheByRef[REF_BOAD]).toBeUndefined()
    expect(s.historyCacheByRef[REF_BOAD]).toBeUndefined()
    // summariesByRef inchangé.
    expect(s.summariesByRef[REF_BOAD]).toBeDefined()
  })

  it("anti-loop : event manual émis localement dans la fenêtre est ignoré", async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(scoringApi.getDetail).mockResolvedValue(detailOut() as any)
    const s = useScoringStore()
    s.setEntity("entreprise", ENT_ID)
    s.currentReferentielCode = REF_BOAD
    await s.loadDetail(REF_BOAD)
    s.trackLocalEmission("score_calculation", "calc-99")
    s.onChatEntityUpdated({
      entityType: "score_calculation",
      entityId: "calc-99",
      source: "manual",
    })
    expect(s.detailsCacheByRef[REF_BOAD]).toBeDefined()
  })
})
