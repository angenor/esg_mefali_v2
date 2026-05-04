// F46 T070 [US6] — Tests RecalcButton.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import RecalcButton from "~/components/scoring/RecalcButton.vue"
import { useScoringStore } from "~/stores/scoring"

const pushMock = vi.fn()
vi.mock("~/composables/useToast", () => ({
  useToast: () => ({ push: pushMock }),
}))

describe("RecalcButton", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    pushMock.mockClear()
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("(a) rendu bouton avec label", () => {
    const w = mount(RecalcButton, { props: { referentielCode: "BOAD" } })
    expect(w.find('[data-testid="recalc-button"]').exists()).toBe(true)
    expect(w.text()).toContain("Recalculer")
  })

  it("(b) disabled=true → click ignoré", async () => {
    const store = useScoringStore()
    const recompute = vi.spyOn(store, "recompute").mockResolvedValue()
    const w = mount(RecalcButton, {
      props: { referentielCode: "BOAD", disabled: true },
    })
    await w.find('[data-testid="recalc-button"]').trigger("click")
    expect(recompute).not.toHaveBeenCalled()
  })

  it("(c) clic appelle store.recompute", async () => {
    const store = useScoringStore()
    const recompute = vi.spyOn(store, "recompute").mockResolvedValue()
    const w = mount(RecalcButton, { props: { referentielCode: "BOAD" } })
    await w.find('[data-testid="recalc-button"]').trigger("click")
    expect(recompute).toHaveBeenCalledWith("BOAD")
  })

  it("(d) isRecomputing=true → spinner + bouton désactivé", async () => {
    const store = useScoringStore()
    store.recomputingByRef = { BOAD: true }
    const w = mount(RecalcButton, { props: { referentielCode: "BOAD" } })
    const btn = w.find('[data-testid="recalc-button"]')
    expect((btn.element as HTMLButtonElement).disabled).toBe(true)
    expect(btn.attributes("aria-busy")).toBe("true")
    expect(w.find(".recalc-btn__spinner").exists()).toBe(true)
  })

  it("(e) erreur backend → toast i18n recomputeFailed", async () => {
    const store = useScoringStore()
    vi.spyOn(store, "recompute").mockRejectedValue(new Error("boom"))
    const w = mount(RecalcButton, { props: { referentielCode: "BOAD" } })
    await w.find('[data-testid="recalc-button"]').trigger("click")
    await new Promise((r) => setTimeout(r, 0))
    expect(pushMock).toHaveBeenCalled()
    const arg = pushMock.mock.calls[0]![0]
    expect(arg.severity).toBe("error")
    expect(arg.message).toContain("Le recalcul a échoué")
  })
})
