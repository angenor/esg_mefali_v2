// F45 T051 — Tests EmptyNoScoring.
import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import EmptyNoScoring from "~/components/plan-action/EmptyNoScoring.vue"

const NuxtLinkStub = {
  name: "NuxtLink",
  props: { to: { type: [String, Object], default: "/" } },
  template: '<a :href="typeof to === \'string\' ? to : \'\'" data-testid="pa-empty-no-scoring-cta"><slot /></a>',
}

describe("EmptyNoScoring", () => {
  it("affiche titre, description et CTA i18n", () => {
    const w = mount(EmptyNoScoring, {
      global: { stubs: { NuxtLink: NuxtLinkStub } },
    })
    expect(w.text()).toContain("Aucun scoring")
    expect(w.text()).toContain("Démarrer mon scoring")
  })

  it("CTA pointe vers /scoring", () => {
    const w = mount(EmptyNoScoring, {
      global: { stubs: { NuxtLink: NuxtLinkStub } },
    })
    const cta = w.find('[data-testid="pa-empty-no-scoring-cta"]')
    expect(cta.exists()).toBe(true)
    expect(cta.attributes("href")).toBe("/scoring")
  })

  it("UiEmptyState rendu (role=status)", () => {
    const w = mount(EmptyNoScoring, {
      global: { stubs: { NuxtLink: NuxtLinkStub } },
    })
    expect(w.find('[role="status"]').exists()).toBe(true)
  })
})
