// F44 T020 — Tests CardCarbon.
import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import CardCarbon from "~/components/dashboard/CardCarbon.vue"

const STUBS = {
  NuxtLink: { props: ["to"], template: '<a :href="to"><slot/></a>' },
  ClientOnly: { template: "<div><slot/></div>" },
  VizKPICard: {
    props: ["label", "value", "unit", "size"],
    template: '<div class="kpi" :data-value="value" :data-unit="unit"/>',
  },
  VizLineChart: { props: ["series", "size"], template: '<div class="line"/>' },
}

setActivePinia(createPinia())

describe("CardCarbon", () => {
  it("filled avec trend → affiche line-chart", () => {
    const wrapper = mount(CardCarbon, {
      props: {
        vm: {
          kind: "filled",
          data: {
            totalAnnualTco2e: "120.4",
            year: 2025,
            trend: [
              { quarter: "Q1", tco2e: "30" },
              { quarter: "Q2", tco2e: "30" },
            ],
            computedAt: new Date(),
            href: "/carbone",
          },
        },
      },
      global: { stubs: STUBS },
    })
    expect(wrapper.find(".kpi").attributes("data-value")).toBe("120.4")
    expect(wrapper.find(".line").exists()).toBe(true)
  })

  it("filled sans trend → KPI seul", () => {
    const wrapper = mount(CardCarbon, {
      props: {
        vm: {
          kind: "filled",
          data: {
            totalAnnualTco2e: "100",
            year: 2025,
            trend: [],
            computedAt: new Date(),
            href: "/carbone",
          },
        },
      },
      global: { stubs: STUBS },
    })
    expect(wrapper.find(".line").exists()).toBe(false)
  })

  it("empty → CTA", () => {
    const wrapper = mount(CardCarbon, {
      props: {
        vm: { kind: "empty", cta: { label: "X", href: "/carbone" }, message: "M" },
      },
      global: { stubs: STUBS },
    })
    expect(wrapper.find('a[href="/carbone"]').exists()).toBe(true)
  })

  // F44 T053 [US6] — Source pin présent quand sourceCount > 0, ouvre popover.
  it("filled avec sourceCount > 0 → DashboardSourceList rendu et cliquable", async () => {
    setActivePinia(createPinia())
    const wrapper = mount(CardCarbon, {
      props: {
        vm: {
          kind: "filled",
          data: {
            totalAnnualTco2e: "12.5",
            year: 2026,
            trend: [],
            computedAt: new Date(),
            href: "/carbone",
            sourceCount: 3,
          },
        },
      },
      global: { stubs: STUBS },
    })
    const pin = wrapper.find('[data-testid="source-pin"]')
    expect(pin.exists()).toBe(true)
    await pin.trigger("click")
    expect(wrapper.find('[data-testid="source-list-pop"]').exists()).toBe(true)
  })
})
