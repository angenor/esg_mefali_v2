// F47 T058 [US4] — Tests useCarbonHistory.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, nextTick } from "vue"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { useCarbonHistory } from "../useCarbonHistory"
import { useCarbonStore } from "~/stores/carbon"

vi.mock("~/services/api/carbon", () => ({
  carbonApi: {
    fetchIndex: vi.fn().mockResolvedValue([]),
    fetchFootprint: vi.fn(),
    recompute: vi.fn(),
    editLine: vi.fn(),
    computeInitial: vi.fn(),
  },
}))

function harness(): {
  api: ReturnType<typeof useCarbonHistory>
  unmount: () => void
} {
  let api: ReturnType<typeof useCarbonHistory> | null = null
  const Comp = defineComponent({
    setup() {
      api = useCarbonHistory()
      return () => h("div")
    },
  })
  const w = mount(Comp)
  return { api: api!, unmount: () => w.unmount() }
}

function fp(year: number, total: string, scopes: [string, string, string]) {
  return {
    id: `fp-${year}`,
    year,
    total_tco2e: total,
    by_scope_kgco2e: { "1": scopes[0], "2": scopes[1], "3": scopes[2] },
    by_category_kgco2e: {},
    breakdown: [],
    factor_versions: [],
  }
}

describe("useCarbonHistory", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("(a) series vide quand index est vide", () => {
    const { api, unmount } = harness()
    expect(api.series.value).toEqual([])
    unmount()
  })

  it("(b) série Total + 3 scopes dérivés des footprints chargés", async () => {
    const store = useCarbonStore()
    store.index = [
      { footprint_id: "fp-2025", year: 2025, total_tco2e: "10", computed_at: "2025-01-01", version: 1 },
      { footprint_id: "fp-2026", year: 2026, total_tco2e: "12", computed_at: "2026-01-01", version: 1 },
    ]
    store.indexLoadedAt = Date.now()
    store.footprints = {
      2025: fp(2025, "10", ["1000", "5000", "4000"]),
      2026: fp(2026, "12", ["2000", "6000", "4000"]),
    } as never
    const { api, unmount } = harness()
    await nextTick()
    expect(api.series.value.length).toBe(4)
    expect(api.series.value[0]!.key).toBe("total")
    expect(api.series.value[0]!.points.length).toBe(2)
    expect(api.series.value[0]!.points[0]!.year).toBe(2025)
    expect(api.series.value[1]!.key).toBe("scope1")
    unmount()
  })

  it("(c) max 5 ans : index avec 7 ans → series limitées à 5", async () => {
    const store = useCarbonStore()
    store.index = Array.from({ length: 7 }, (_, i) => ({
      footprint_id: `fp-${2020 + i}`,
      year: 2020 + i,
      total_tco2e: "10",
      computed_at: "2020-01-01",
      version: 1,
    }))
    store.indexLoadedAt = Date.now()
    store.footprints = Object.fromEntries(
      Array.from({ length: 7 }, (_, i) => [
        2020 + i,
        fp(2020 + i, "10", ["1000", "5000", "4000"]),
      ]),
    ) as never
    const { api, unmount } = harness()
    await nextTick()
    expect(api.series.value[0]!.points.length).toBe(5)
    unmount()
  })

  it("(d) point manquant si footprint absent (utilise total de l'index)", async () => {
    const store = useCarbonStore()
    store.index = [
      { footprint_id: "fp-2025", year: 2025, total_tco2e: "10", computed_at: "2025-01-01", version: 1 },
    ]
    store.indexLoadedAt = Date.now()
    store.footprints = {} as never
    const { api, unmount } = harness()
    await nextTick()
    const total = api.series.value[0]
    expect(total?.points[0]?.value).toBeCloseTo(10, 2)
    const scope1 = api.series.value[1]
    expect(scope1?.points[0]?.value).toBeNull()
    unmount()
  })
})
