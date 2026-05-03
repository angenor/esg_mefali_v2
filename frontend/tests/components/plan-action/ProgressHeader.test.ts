// F45 T038 — Tests ProgressHeader.
import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import ProgressHeader from "~/components/plan-action/ProgressHeader.vue"
import type { CompletionStats } from "~/types/actionPlan"

function stats(o: Partial<CompletionStats> = {}): CompletionStats {
  return { totalVisible: 10, doneVisible: 3, percent: 30, hasData: true, ...o }
}

describe("ProgressHeader", () => {
  it("affiche le KPI X / Y et le pourcentage", () => {
    const w = mount(ProgressHeader, { props: { stats: stats(), version: 2 } })
    expect(w.text()).toContain("3")
    expect(w.text()).toContain("10")
    expect(w.text()).toContain("30")
    expect(w.text()).toContain("%")
  })

  it("affiche la version", () => {
    const w = mount(ProgressHeader, { props: { stats: stats(), version: 5 } })
    expect(w.text()).toContain("5")
  })

  it("hasData=false → affiche — au lieu d'un pourcentage", () => {
    const w = mount(ProgressHeader, {
      props: {
        stats: stats({ totalVisible: 0, doneVisible: 0, percent: 0, hasData: false }),
        version: 1,
      },
    })
    const percent = w.find(".pa-progress__percent")
    expect(percent.text().trim()).toBe("—")
  })

  it("a11y : role=progressbar avec aria-valuenow / max", () => {
    const w = mount(ProgressHeader, { props: { stats: stats(), version: 1 } })
    const bar = w.find('[role="progressbar"]')
    expect(bar.exists()).toBe(true)
    expect(bar.attributes("aria-valuenow")).toBe("30")
    expect(bar.attributes("aria-valuemax")).toBe("100")
  })

  it("largeur barre = percent %", () => {
    const w = mount(ProgressHeader, { props: { stats: stats({ percent: 45 }), version: 1 } })
    const fill = w.find(".pa-progress__bar-fill")
    expect(fill.attributes("style")).toContain("width: 45%")
  })
})
