// F44 T017 — Tests EmptyCardCTA (CTA focusable + lien correct).
import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import EmptyCardCTA from "~/components/dashboard/EmptyCardCTA.vue"

const NuxtLinkStub = {
  props: ["to"],
  template: '<a :href="to" class="empty-cta__btn"><slot/></a>',
}

describe("EmptyCardCTA", () => {
  it("rend message + lien CTA", () => {
    const wrapper = mount(EmptyCardCTA, {
      props: {
        cta: { label: "Lancer", href: "/scoring" },
        message: "Aucune donnée pour le moment.",
      },
      global: { stubs: { NuxtLink: NuxtLinkStub } },
    })
    expect(wrapper.text()).toContain("Aucune donnée pour le moment.")
    const link = wrapper.find("a")
    expect(link.attributes("href")).toBe("/scoring")
    expect(link.text()).toBe("Lancer")
  })

  it("ne rend jamais '0' ni '—'", () => {
    const wrapper = mount(EmptyCardCTA, {
      props: { cta: { label: "Aller", href: "/x" } },
      global: { stubs: { NuxtLink: NuxtLinkStub } },
    })
    expect(wrapper.text()).not.toMatch(/^0$/)
    expect(wrapper.text()).not.toMatch(/^—$/)
  })
})
