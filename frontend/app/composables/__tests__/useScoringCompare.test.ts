// F46 T035 [US2] — Tests useScoringCompare.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, nextTick } from "vue"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { useScoringCompare } from "../useScoringCompare"
import { useScoringStore } from "~/stores/scoring"
import type { ScoreSummaryVM } from "~/types/scoring"

const pushMock = vi.fn()
vi.mock("~/composables/useToast", () => ({
  useToast: () => ({ push: pushMock }),
}))

function buildSummary(code: string, pillars: Record<string, number | null>): ScoreSummaryVM {
  return {
    referentielCode: code,
    referentielId: `id-${code}`,
    referentielVersion: 1,
    scoreGlobal: 60,
    scoresByPillar: pillars,
    coverageRatio: 0.8,
    computedAt: "2026-04-15T10:30:00Z",
  }
}

function mountHarness(): { api: ReturnType<typeof useScoringCompare>; unmount: () => void } {
  let api: ReturnType<typeof useScoringCompare> | null = null
  const Comp = defineComponent({
    setup() {
      api = useScoringCompare()
      return () => h("div")
    },
  })
  const w = mount(Comp)
  return { api: api!, unmount: () => w.unmount() }
}

describe("useScoringCompare", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    pushMock.mockClear()
    ;(globalThis as unknown as { useRuntimeConfig: () => unknown }).useRuntimeConfig = () => ({ public: { apiBase: "http://api" } })
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("(a) selectedRefs initialisé à [currentRef]", () => {
    const store = useScoringStore()
    store.summariesByRef = {
      BOAD: buildSummary("BOAD", { E: 60, S: 70, G: 65 }),
      CDP: buildSummary("CDP", { E: 50 }),
    }
    store.currentReferentielCode = "BOAD"
    const { api, unmount } = mountHarness()
    expect(api.selectedRefs.value).toEqual(["BOAD"])
    unmount()
  })

  it("(b) select('CDP') ajoute", async () => {
    const store = useScoringStore()
    store.summariesByRef = {
      BOAD: buildSummary("BOAD", { E: 60, S: 70, G: 65 }),
      CDP: buildSummary("CDP", { E: 50 }),
    }
    store.currentReferentielCode = "BOAD"
    const { api, unmount } = mountHarness()
    api.select("CDP")
    await nextTick()
    expect(api.selectedRefs.value).toEqual(["BOAD", "CDP"])
    unmount()
  })

  it("(c) unselect('BOAD') retire", async () => {
    const store = useScoringStore()
    store.summariesByRef = {
      BOAD: buildSummary("BOAD", { E: 60 }),
      CDP: buildSummary("CDP", { E: 50 }),
    }
    store.currentReferentielCode = "BOAD"
    const { api, unmount } = mountHarness()
    api.select("CDP")
    api.unselect("BOAD")
    await nextTick()
    expect(api.selectedRefs.value).toEqual(["CDP"])
    unmount()
  })

  it("(d) max 5 sélections — 6e refusée + toast", async () => {
    const store = useScoringStore()
    store.summariesByRef = {
      A: buildSummary("A", { E: 1 }),
      B: buildSummary("B", { E: 2 }),
      C: buildSummary("C", { E: 3 }),
      D: buildSummary("D", { E: 4 }),
      E: buildSummary("E", { E: 5 }),
      F: buildSummary("F", { E: 6 }),
    }
    store.currentReferentielCode = "A"
    const { api, unmount } = mountHarness()
    api.select("B")
    api.select("C")
    api.select("D")
    api.select("E")
    expect(api.selectedRefs.value.length).toBe(5)
    api.select("F")
    expect(api.selectedRefs.value.length).toBe(5)
    expect(api.selectedRefs.value).not.toContain("F")
    expect(pushMock).toHaveBeenCalled()
    unmount()
  })

  it("(e) dataset calcule l'union ordonnée des piliers", () => {
    const store = useScoringStore()
    store.summariesByRef = {
      BOAD: buildSummary("BOAD", { E: 60, S: 70, G: 65 }),
      CDP: buildSummary("CDP", { E: 50, P1: 40 }),
    }
    store.currentReferentielCode = "BOAD"
    const { api, unmount } = mountHarness()
    api.select("CDP")
    const ds = api.dataset.value
    expect(ds.referentiels.length).toBe(2)
    expect(ds.pillars).toEqual(["E", "S", "G", "P1"])
    unmount()
  })
})
