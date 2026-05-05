// F46 T077 [US7] — Tests HistoryChart.
import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import HistoryChart from "~/components/scoring/HistoryChart.vue"
import type { ScoreHistoryEntryVM } from "~/types/scoring"

const STUBS = {
  VizLineChart: {
    props: ["series", "loading", "empty", "size", "title"],
    template:
      '<div class="stub-line" :data-points="series[0]?.points?.length ?? 0" :data-loading="String(loading)" />',
  },
}

function buildEntry(id: string, days: number, score: number, version = 1): ScoreHistoryEntryVM {
  const d = new Date()
  d.setUTCDate(d.getUTCDate() - days)
  return {
    scoreCalculationId: id,
    computedAt: d.toISOString(),
    scoreGlobal: score,
    referentielVersion: version,
  }
}

describe("HistoryChart", () => {
  it("(a) entries=[] + loading=false → message 'Pas encore d'historique'", () => {
    const w = mount(HistoryChart, {
      props: { entries: [], loading: false },
      global: { stubs: STUBS },
    })
    expect(w.find('[data-testid="history-chart-empty"]').exists()).toBe(true)
    expect(w.text()).toContain("Pas encore d'historique")
  })

  it("(b) entries.length=1 → un point", () => {
    const w = mount(HistoryChart, {
      props: { entries: [buildEntry("c1", 1, 50)], loading: false },
      global: { stubs: STUBS },
    })
    expect(w.find(".stub-line").attributes("data-points")).toBe("1")
  })

  it("(c) entries.length=12 → 12 points", () => {
    const entries = Array.from({ length: 12 }, (_, i) =>
      buildEntry(`c${i}`, i, 50 + i),
    )
    const w = mount(HistoryChart, {
      props: { entries, loading: false },
      global: { stubs: STUBS },
    })
    expect(w.find(".stub-line").attributes("data-points")).toBe("12")
  })

  it("(d) entrées listées en sr-only avec format date/score/version", () => {
    const e = buildEntry("c1", 0, 75, 3)
    const w = mount(HistoryChart, {
      props: { entries: [e], loading: false },
      global: { stubs: STUBS },
    })
    expect(w.find(".sr-only").exists()).toBe(true)
    expect(w.text()).toMatch(/75 pts/)
    expect(w.text()).toMatch(/v\.3/)
  })

  it("(e) clic sur un point sr-only émet 'select(entry)'", async () => {
    const e = buildEntry("c1", 0, 75)
    const w = mount(HistoryChart, {
      props: { entries: [e], loading: false },
      global: { stubs: STUBS },
    })
    await w.find("button").trigger("click")
    const emitted = w.emitted("select")
    expect(emitted).toBeTruthy()
    expect((emitted![0]![0] as ScoreHistoryEntryVM).scoreCalculationId).toBe("c1")
  })
})
