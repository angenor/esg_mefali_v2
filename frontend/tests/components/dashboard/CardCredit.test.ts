// F44 T021 — Tests CardCredit.
import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import CardCredit from "~/components/dashboard/CardCredit.vue"

const STUBS = {
  NuxtLink: { props: ["to"], template: '<a :href="to"><slot/></a>' },
  ClientOnly: { template: "<div><slot/></div>" },
  VizGaugeChart: { props: ["value", "min", "max", "size"], template: '<div class="gauge" :data-value="value"/>' },
  UiBadge: { props: ["severity"], template: '<span class="badge" :data-severity="severity"><slot/></span>' },
}

setActivePinia(createPinia())

describe("CardCredit", () => {
  it("filled → gauge + badges éligibilité", () => {
    const wrapper = mount(CardCredit, {
      props: {
        vm: {
          kind: "filled",
          data: {
            combineScore: 72,
            solvabilite: 75,
            impactVert: 70,
            eligibilityBadges: ["BOAD"],
            coherenceWarning: false,
            computedAt: new Date(),
            href: "/credit-score",
          },
        },
      },
      global: { stubs: STUBS },
    })
    expect(wrapper.find(".gauge").attributes("data-value")).toBe("72")
    const badges = wrapper.findAll('[data-testid="eligibility-badge"]')
    expect(badges.length).toBe(1)
    expect(badges[0]?.text()).toBe("BOAD")
  })

  it("coherenceWarning=true → badge orange visible", () => {
    const wrapper = mount(CardCredit, {
      props: {
        vm: {
          kind: "filled",
          data: {
            combineScore: 50,
            solvabilite: 50,
            impactVert: 50,
            eligibilityBadges: [],
            coherenceWarning: true,
            computedAt: new Date(),
            href: "/credit-score",
          },
        },
      },
      global: { stubs: STUBS },
    })
    expect(wrapper.find('[data-testid="coherence-warning"]').exists()).toBe(true)
  })

  it("empty → CTA", () => {
    const wrapper = mount(CardCredit, {
      props: { vm: { kind: "empty", cta: { label: "C", href: "/credit-score" }, message: "M" } },
      global: { stubs: STUBS },
    })
    expect(wrapper.find('a[href="/credit-score"]').exists()).toBe(true)
  })
})
