// F47 T065 [US5] — Tests RecalcStrip.
import { describe, expect, it, vi } from "vitest"
import { mount } from "@vue/test-utils"
import RecalcStrip from "~/components/carbone/RecalcStrip.vue"

vi.mock("~/composables/useT", () => ({
  useT: () => ({ t: (k: string, p?: Record<string, unknown>) => (p ? `${k}|${JSON.stringify(p)}` : k) }),
}))

vi.mock("~/composables/useReducedMotion", () => ({
  useReducedMotion: () => ({ value: false }),
}))

describe("RecalcStrip", () => {
  it("(a) affiche lastComputedAt formaté", () => {
    const w = mount(RecalcStrip, {
      props: {
        year: 2026,
        lastComputedAt: "2026-05-01T10:00:00Z",
        loading: false,
      },
    })
    expect(w.text()).toContain("carbon.recalc.lastComputed")
  })

  it("(b) lastComputedAt=null → tiret", () => {
    const w = mount(RecalcStrip, {
      props: { year: 2026, lastComputedAt: null, loading: false },
    })
    expect(w.text()).toContain("—")
  })

  it("(c) loading=true → bouton désactivé + spinner + texte 'running'", () => {
    const w = mount(RecalcStrip, {
      props: { year: 2026, lastComputedAt: null, loading: true },
    })
    const btn = w.find("button")
    expect(btn.attributes("aria-disabled")).toBe("true")
    expect(w.text()).toContain("carbon.recalc.running")
  })

  it("(d) clic émet 'recompute'", async () => {
    const w = mount(RecalcStrip, {
      props: { year: 2026, lastComputedAt: null, loading: false },
    })
    await w.find("button").trigger("click")
    expect(w.emitted("recompute")).toBeTruthy()
  })

  it("(e) clic ignoré quand loading=true", async () => {
    const w = mount(RecalcStrip, {
      props: { year: 2026, lastComputedAt: null, loading: true },
    })
    await w.find("button").trigger("click")
    expect(w.emitted("recompute")).toBeFalsy()
  })
})
