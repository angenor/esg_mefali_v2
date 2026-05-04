// F46 T083 [US8] — Tests SnapshotToggle.
import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import SnapshotToggle from "~/components/scoring/SnapshotToggle.vue"
import type { ScoreHistoryEntryVM } from "~/types/scoring"

function entry(id: string, day: string, score: number, v: number): ScoreHistoryEntryVM {
  return {
    scoreCalculationId: id,
    computedAt: `${day}T10:00:00Z`,
    scoreGlobal: score,
    referentielVersion: v,
  }
}

describe("SnapshotToggle", () => {
  const entries = [
    entry("c1", "2026-04-15", 60, 3),
    entry("c2", "2026-03-20", 55, 2),
  ]

  it("(a) switch reflète active=false", () => {
    const w = mount(SnapshotToggle, {
      props: { entries, active: false },
    })
    const sw = w.find('[data-testid="snapshot-switch"]')
      .element as HTMLInputElement
    expect(sw.checked).toBe(false)
  })

  it("(b) sélecteur date liste les entries formatées FR", () => {
    const w = mount(SnapshotToggle, {
      props: { entries, active: false },
    })
    const opts = w.findAll('[data-testid="snapshot-select"] option')
    // 1 placeholder + 2 entries
    expect(opts.length).toBe(3)
    expect(opts[1]!.text()).toContain("15/04/2026")
    expect(opts[1]!.text()).toContain("60 pts")
    expect(opts[1]!.text()).toContain("v.3")
  })

  it("(c) activation switch émet 'enter(calcId)'", async () => {
    const w = mount(SnapshotToggle, {
      props: { entries, active: false },
    })
    await w.find('[data-testid="snapshot-switch"]').setValue(true)
    const emitted = w.emitted("enter")
    expect(emitted).toBeTruthy()
    expect(emitted![0]![0]).toBe("c1")
  })

  it("(d) désactivation émet 'exit'", async () => {
    const w = mount(SnapshotToggle, {
      props: { entries, active: true, frozenCalculationId: "c1" },
    })
    await w.find('[data-testid="snapshot-switch"]').setValue(false)
    expect(w.emitted("exit")).toBeTruthy()
  })

  it("(e) bandeau visible quand active + frozen valide", () => {
    const w = mount(SnapshotToggle, {
      props: { entries, active: true, frozenCalculationId: "c1" },
    })
    const banner = w.find('[data-testid="snapshot-banner"]')
    expect(banner.exists()).toBe(true)
    expect(banner.text()).toContain("15/04/2026")
    expect(banner.text()).toContain("v.3")
  })

  it("(f) bandeau non dismissible (pas de bouton de fermeture)", () => {
    const w = mount(SnapshotToggle, {
      props: { entries, active: true, frozenCalculationId: "c1" },
    })
    const banner = w.find('[data-testid="snapshot-banner"]')
    expect(banner.find("button").exists()).toBe(false)
  })
})
