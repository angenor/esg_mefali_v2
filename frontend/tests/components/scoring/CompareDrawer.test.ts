// F46 T036 [US2] — Tests CompareDrawer.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import CompareDrawer from "~/components/scoring/CompareDrawer.vue"
import { useScoringStore } from "~/stores/scoring"
import type { ScoreSummaryVM } from "~/types/scoring"

vi.mock("~/composables/useToast", () => ({
  useToast: () => ({ push: vi.fn() }),
}))

const STUBS = {
  UiModal: {
    props: ["modelValue"],
    template:
      '<div v-if="modelValue" class="stub-modal"><slot name="header" /><slot /><slot name="footer" /></div>',
  },
  VizBarChart: {
    props: ["series", "title", "size"],
    template:
      '<div class="stub-bar" :data-labels="series.labels.length" :data-datasets="series.datasets.length" />',
  },
}

function buildSummary(code: string, version = 1): ScoreSummaryVM {
  return {
    referentielCode: code,
    referentielId: `id-${code}`,
    referentielVersion: version,
    scoreGlobal: 60,
    scoresByPillar: { E: 60, S: 70, G: 65 },
    coverageRatio: 0.8,
    computedAt: "2026-04-15T10:30:00Z",
  }
}

describe("CompareDrawer", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    ;(globalThis as unknown as { useRuntimeConfig: () => unknown }).useRuntimeConfig = () => ({ public: { apiBase: "http://api" } })
    const store = useScoringStore()
    store.summariesByRef = {
      BOAD: buildSummary("BOAD", 3),
      CDP: buildSummary("CDP", 2),
    }
    store.currentReferentielCode = "BOAD"
  })
  afterEach(() => vi.restoreAllMocks())

  it("(a) open=true rend modal", () => {
    const w = mount(CompareDrawer, {
      props: { availableSummaries: [buildSummary("BOAD"), buildSummary("CDP")], open: true },
      global: { stubs: STUBS },
    })
    expect(w.find(".stub-modal").exists()).toBe(true)
  })

  it("(b) checkboxes correspondent aux availableSummaries", () => {
    const w = mount(CompareDrawer, {
      props: { availableSummaries: [buildSummary("BOAD"), buildSummary("CDP")], open: true },
      global: { stubs: STUBS },
    })
    const checks = w.findAll('input[type="checkbox"]')
    expect(checks.length).toBe(2)
  })

  it("(c) VizBarChart reçoit dataset", () => {
    const w = mount(CompareDrawer, {
      props: {
        availableSummaries: [buildSummary("BOAD"), buildSummary("CDP")],
        defaultSelected: ["BOAD", "CDP"],
        open: true,
      },
      global: { stubs: STUBS },
    })
    const bar = w.find(".stub-bar")
    expect(bar.exists()).toBe(true)
    expect(bar.attributes("data-datasets")).toBe("2")
  })

  it("(d) légende affiche libellé + version", () => {
    const w = mount(CompareDrawer, {
      props: {
        availableSummaries: [buildSummary("BOAD", 3)],
        defaultSelected: ["BOAD"],
        open: true,
      },
      global: { stubs: STUBS },
    })
    const legend = w.find('[data-testid="compare-drawer-legend"]')
    expect(legend.exists()).toBe(true)
    expect(legend.text()).toContain("BOAD")
    expect(legend.text()).toContain("v.3")
  })

  it("(e) close émet 'close'", async () => {
    const w = mount(CompareDrawer, {
      props: { availableSummaries: [buildSummary("BOAD")], open: true },
      global: { stubs: STUBS },
    })
    await w.find('[data-testid="compare-drawer-close"]').trigger("click")
    expect(w.emitted("close")).toBeTruthy()
  })
})
