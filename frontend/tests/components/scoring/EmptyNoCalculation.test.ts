// F46 T022 [US1] — Tests EmptyNoCalculation.
import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import EmptyNoCalculation from "~/components/scoring/EmptyNoCalculation.vue"

const STUBS = {
  UiEmptyState: {
    props: ["severity", "title", "description"],
    template:
      '<div class="stub-empty" role="status">' +
      '<h3>{{ title }}</h3>' +
      '<p>{{ description }}</p>' +
      '<slot name="action" />' +
      "</div>",
  },
}

describe("EmptyNoCalculation", () => {
  it("(a) rend UiEmptyState avec titre et CTA", () => {
    const w = mount(EmptyNoCalculation, {
      props: { referentielCode: "BOAD" },
      global: { stubs: STUBS },
    })
    expect(w.find(".stub-empty").exists()).toBe(true)
    expect(w.text()).toContain("Lancez votre premier diagnostic")
    expect(w.text()).toContain("Aucun calcul")
    const cta = w.find('[data-testid="scoring-empty-no-calc-cta"]')
    expect(cta.exists()).toBe(true)
  })

  it("(b) clic CTA émet 'start'", async () => {
    const w = mount(EmptyNoCalculation, {
      props: { referentielCode: "BOAD" },
      global: { stubs: STUBS },
    })
    await w.find('[data-testid="scoring-empty-no-calc-cta"]').trigger("click")
    expect(w.emitted("start")).toBeTruthy()
    expect(w.emitted("start")!.length).toBe(1)
  })

  it("(c) bouton désactivé pendant loading=true", () => {
    const w = mount(EmptyNoCalculation, {
      props: { referentielCode: "BOAD", loading: true },
      global: { stubs: STUBS },
    })
    const cta = w.find('[data-testid="scoring-empty-no-calc-cta"]')
    expect((cta.element as HTMLButtonElement).disabled).toBe(true)
    expect(cta.attributes("aria-busy")).toBe("true")
  })
})
