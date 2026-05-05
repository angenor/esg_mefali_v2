// F44 T022 — Tests CardCandidatures.
import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import CardCandidatures from "~/components/dashboard/CardCandidatures.vue"

const STUBS = {
  NuxtLink: { props: ["to"], template: '<a :href="to"><slot/></a>' },
  UiBadge: { props: ["severity"], template: '<span class="badge"><slot/></span>' },
}

setActivePinia(createPinia())

describe("CardCandidatures", () => {
  it("filled → 3 récentes max + pills statut", () => {
    const wrapper = mount(CardCandidatures, {
      props: {
        vm: {
          kind: "filled",
          data: {
            countersByStatut: { en_cours: 2, soumise: 1 },
            total: 3,
            recent: [
              { id: "c1", projetLabel: "P1", offreLabel: "O1", statut: "en_cours", statutLabel: "En cours", soumissionAt: null },
              { id: "c2", projetLabel: "P2", offreLabel: "O2", statut: "soumise", statutLabel: "Soumise", soumissionAt: new Date("2026-04-01") },
            ],
            href: "/candidatures",
          },
        },
      },
      global: { stubs: STUBS },
    })
    expect(wrapper.findAll('[data-testid="counter-pill"]').length).toBe(2)
    expect(wrapper.findAll('[data-testid="candidature-recent"]').length).toBe(2)
    expect(wrapper.text()).toContain("P1")
    expect(wrapper.text()).toContain("En cours")
  })

  it("empty → CTA", () => {
    const wrapper = mount(CardCandidatures, {
      props: { vm: { kind: "empty", cta: { label: "X", href: "/candidatures" }, message: "M" } },
      global: { stubs: STUBS },
    })
    expect(wrapper.find('a[href="/candidatures"]').exists()).toBe(true)
  })
})
