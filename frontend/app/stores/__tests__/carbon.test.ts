// F47 T023 — Tests useCarbonStore (cas critiques).

import { setActivePinia, createPinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { useCarbonStore } from "~/stores/carbon"
import type { CarbonFootprint } from "~/types/carbon"

vi.mock("~/services/api/carbon", () => ({
  carbonApi: {
    fetchIndex: vi.fn().mockResolvedValue([]),
    fetchFootprint: vi.fn(),
    recompute: vi.fn(),
    editLine: vi.fn(),
    computeInitial: vi.fn(),
  },
}))

import { carbonApi } from "~/services/api/carbon"

function fpFixture(overrides: Partial<CarbonFootprint> = {}): CarbonFootprint {
  return {
    id: "fp-1",
    year: 2026,
    total_tco2e: "12.4",
    by_scope_kgco2e: { "1": "1000", "2": "5000", "3": "6400" },
    by_category_kgco2e: {},
    breakdown: [],
    factor_versions: [],
    computed_at: "2026-05-04T12:00:00Z",
    version: 1,
    ...overrides,
  }
}

describe("useCarbonStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it("loadIndex appelle carbonApi.fetchIndex et stocke", async () => {
    const entries = [
      {
        footprint_id: "fp-1",
        year: 2026,
        total_tco2e: "12.4",
        computed_at: "2026-05-04T12:00:00Z",
        version: 1,
      },
    ]
    ;(carbonApi.fetchIndex as ReturnType<typeof vi.fn>).mockResolvedValueOnce(entries)
    const store = useCarbonStore()
    await store.loadIndex()
    expect(carbonApi.fetchIndex).toHaveBeenCalledTimes(1)
    expect(store.index).toEqual(entries)
    expect(store.indexLoadedAt).not.toBeNull()
  })

  it("loadIndex respecte le cache TTL 60s sans force", async () => {
    const store = useCarbonStore()
    ;(carbonApi.fetchIndex as ReturnType<typeof vi.fn>).mockResolvedValue([])
    await store.loadIndex()
    await store.loadIndex()
    expect(carbonApi.fetchIndex).toHaveBeenCalledTimes(1)
  })

  it("loadFootprint 404 met footprints[year] = null", async () => {
    ;(carbonApi.fetchFootprint as ReturnType<typeof vi.fn>).mockRejectedValueOnce({
      status: 404,
    })
    const store = useCarbonStore()
    await store.loadFootprint(2026)
    expect(store.footprints[2026]).toBeNull()
    expect(store.errorByYear[2026]).toBeNull()
  })

  it("applyFootprint met à jour footprints et index", () => {
    const store = useCarbonStore()
    store.index = []
    const fp = fpFixture()
    store.applyFootprint(2026, fp)
    expect(store.footprints[2026]).toEqual(fp)
    expect(store.index).toHaveLength(1)
    expect(store.index?.[0]?.year).toBe(2026)
  })

  it("recompute évite les double-clics (loading guard)", async () => {
    const store = useCarbonStore()
    store.loadingRecompute = { 2026: true }
    const result = await store.recompute(2026)
    expect(result).toBeNull()
    expect(carbonApi.recompute).not.toHaveBeenCalled()
  })

  it("editLine évite les double-clics (loading guard)", async () => {
    const store = useCarbonStore()
    store.loadingEditLine = { 2026: true }
    const result = await store.editLine(2026, {
      code: "x",
      quantity: "1",
      source_id: "sid",
    })
    expect(result).toBeNull()
    expect(carbonApi.editLine).not.toHaveBeenCalled()
  })

  it("invalidateYear supprime l'année du cache", () => {
    const store = useCarbonStore()
    store.footprints = { 2026: fpFixture() }
    store.invalidateYear(2026)
    expect(store.footprints[2026]).toBeUndefined()
  })

  it("getters currentFootprint et previousYearFootprint", () => {
    const store = useCarbonStore()
    store.selectedYear = 2026
    store.footprints = { 2026: fpFixture(), 2025: fpFixture({ year: 2025, id: "fp-0" }) }
    expect(store.currentFootprint?.id).toBe("fp-1")
    expect(store.previousYearFootprint?.id).toBe("fp-0")
  })
})
