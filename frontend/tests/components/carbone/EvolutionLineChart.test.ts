// F47 T059 [US4] — Tests EvolutionLineChart.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import EvolutionLineChart from "~/components/carbone/EvolutionLineChart.vue"
import { useCarbonStore } from "~/stores/carbon"

vi.mock("~/composables/useT", () => ({
  useT: () => ({ t: (k: string) => k }),
}))

vi.mock("~/services/api/carbon", () => ({
  carbonApi: {
    fetchIndex: vi.fn().mockResolvedValue([]),
    fetchFootprint: vi.fn(),
    recompute: vi.fn(),
    editLine: vi.fn(),
    computeInitial: vi.fn(),
  },
}))

// VizLineChart utilise <ClientOnly> + chart.js — stub.
vi.mock("~/components/viz/VizLineChart.vue", () => ({
  default: { template: "<div class='viz-line-stub' />" },
}))
vi.mock("~/components/viz/VizEmptyState.vue", () => ({
  default: { template: "<div class='viz-empty-stub' />" },
}))

function seedIndex(years: number[]) {
  const store = useCarbonStore()
  store.index = years.map((y) => ({
    footprint_id: `fp-${y}`,
    year: y,
    total_tco2e: "10",
    computed_at: `${y}-01-01`,
    version: 1,
  }))
  store.indexLoadedAt = Date.now()
  store.footprints = Object.fromEntries(
    years.map((y) => [
      y,
      {
        id: `fp-${y}`,
        year: y,
        total_tco2e: "10",
        by_scope_kgco2e: { "1": "1000", "2": "5000", "3": "4000" },
        by_category_kgco2e: {},
        breakdown: [],
        factor_versions: [],
      },
    ]),
  ) as never
}

describe("EvolutionLineChart", () => {
  beforeEach(() => setActivePinia(createPinia()))
  afterEach(() => vi.restoreAllMocks())

  it("(a) état vide → VizEmptyState rendu", () => {
    const w = mount(EvolutionLineChart)
    expect(w.find(".viz-empty-stub").exists()).toBe(true)
  })

  it("(b) avec données → VizLineChart rendu + 4 boutons légende", () => {
    seedIndex([2024, 2025, 2026])
    const w = mount(EvolutionLineChart)
    expect(w.find(".viz-line-stub").exists()).toBe(true)
    const buttons = w.findAll("button")
    expect(buttons.length).toBe(4)
  })

  it("(c) clic légende toggle aria-pressed", async () => {
    seedIndex([2024, 2025, 2026])
    const w = mount(EvolutionLineChart)
    const btn = w.findAll("button").at(2)!
    expect(btn.attributes("aria-pressed")).toBe("true")
    await btn.trigger("click")
    expect(btn.attributes("aria-pressed")).toBe("false")
  })

  it("(d) tableau sr-only listant les années est rendu", () => {
    seedIndex([2025, 2026])
    const w = mount(EvolutionLineChart)
    const table = w.find("table")
    expect(table.exists()).toBe(true)
    expect(table.classes()).toContain("sr-only")
  })
})
