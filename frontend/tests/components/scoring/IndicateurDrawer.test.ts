// F46 T047 [US3] — Tests IndicateurDrawer.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import IndicateurDrawer from "~/components/scoring/IndicateurDrawer.vue"
import type { PillarRowVM } from "~/types/scoring"

vi.mock("~/composables/useToast", () => ({
  useToast: () => ({ push: vi.fn() }),
}))

vi.mock("~/composables/useScoringHistory", () => ({
  useScoringHistory: () => ({
    entries: { value: [] },
    loading: { value: false },
    error: { value: null },
    load: vi.fn(),
  }),
}))

const STUBS = {
  VizLineChart: {
    props: ["series", "title", "size", "loading", "empty"],
    template:
      '<div class="stub-line-chart" :data-loading="String(loading)" :data-empty="String(empty)" />',
  },
  RevokedSourceBadge: {
    props: ["sourceId"],
    template: '<span class="stub-revoked-badge" />',
  },
  VizSourcePin: {
    props: ["source_id"],
    template: '<span class="stub-source-pin" :data-source="source_id" />',
  },
}

function buildRow(overrides: Partial<PillarRowVM> = {}): PillarRowVM {
  return {
    indicateurId: "ind-1",
    indicateurCode: "EFFECTIFS_TOTAL",
    pillar: "S",
    status: "covered",
    scoreContribution: 12.34,
    weight: 0.2,
    normalizedValue: 0.6,
    rawValue: 150,
    sourceId: "src-1",
    isSourceRevoked: false,
    isEditable: true,
    reason: null,
    ...overrides,
  }
}

describe("IndicateurDrawer", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    ;(globalThis as unknown as { useRuntimeConfig: () => unknown }).useRuntimeConfig = () => ({
      public: { apiBase: "http://api" },
    })
  })
  afterEach(() => vi.restoreAllMocks())

  it("(a) open=false ne monte pas le contenu", () => {
    const w = mount(IndicateurDrawer, {
      props: { row: buildRow(), referentielCode: "BOAD", open: false },
      global: { stubs: STUBS },
    })
    expect(w.find('[data-testid="indicateur-drawer"]').exists()).toBe(false)
  })

  it("(b) open=true rend nom, valeur, sources", () => {
    const w = mount(IndicateurDrawer, {
      props: { row: buildRow(), referentielCode: "BOAD", open: true },
      global: { stubs: STUBS },
    })
    expect(w.find('[data-testid="indicateur-drawer"]').exists()).toBe(true)
    expect(w.text()).toContain("EFFECTIFS_TOTAL")
    expect(w.text()).toContain("150")
  })

  it("(c) <VizLineChart> créé uniquement si open=true (perf R9)", async () => {
    const w = mount(IndicateurDrawer, {
      props: { row: buildRow(), referentielCode: "BOAD", open: false },
      global: { stubs: STUBS },
    })
    expect(w.find(".stub-line-chart").exists()).toBe(false)
    await w.setProps({ open: true })
    expect(w.find(".stub-line-chart").exists()).toBe(true)
  })

  it("(d) bouton Modifier désactivé si disableEdit ou !row.isEditable", () => {
    const w1 = mount(IndicateurDrawer, {
      props: {
        row: buildRow({ isEditable: true }),
        referentielCode: "BOAD",
        open: true,
        disableEdit: true,
      },
      global: { stubs: STUBS },
    })
    expect(
      w1.find('[data-testid="indicateur-drawer-edit"]').attributes("disabled"),
    ).toBeDefined()

    const w2 = mount(IndicateurDrawer, {
      props: {
        row: buildRow({ isEditable: false }),
        referentielCode: "BOAD",
        open: true,
      },
      global: { stubs: STUBS },
    })
    expect(
      w2.find('[data-testid="indicateur-drawer-edit"]').attributes("disabled"),
    ).toBeDefined()
  })

  it("(e) clic Modifier émet edit(row)", async () => {
    const r = buildRow()
    const w = mount(IndicateurDrawer, {
      props: { row: r, referentielCode: "BOAD", open: true },
      global: { stubs: STUBS },
    })
    await w.find('[data-testid="indicateur-drawer-edit"]').trigger("click")
    expect(w.emitted("edit")).toBeTruthy()
    expect(w.emitted("edit")![0]![0]).toEqual(r)
  })

  it("(f) Escape ferme + émet close", async () => {
    const w = mount(IndicateurDrawer, {
      props: { row: buildRow(), referentielCode: "BOAD", open: true },
      attachTo: document.body,
      global: { stubs: STUBS },
    })
    await w
      .find('[data-testid="indicateur-drawer"]')
      .trigger("keydown", { key: "Escape" })
    expect(w.emitted("close")).toBeTruthy()
    w.unmount()
  })
})
