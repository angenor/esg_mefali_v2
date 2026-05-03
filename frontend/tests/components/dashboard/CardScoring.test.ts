// F44 T019 — Tests CardScoring (loading/empty/filled/error).
import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import CardScoring from "~/components/dashboard/CardScoring.vue"

const STUBS = {
  NuxtLink: { props: ["to"], template: '<a :href="to"><slot/></a>' },
  ClientOnly: { template: "<div><slot/></div>" },
  VizKPICard: { props: ["label", "value", "size"], template: '<div class="kpi" :data-value="value">{{label}}: {{value}}</div>' },
  VizRadarChart: { props: ["series", "size"], template: '<div class="radar" />' },
}

function withPinia() {
  setActivePinia(createPinia())
}

describe("CardScoring", () => {
  it("loading → affiche le squelette", () => {
    withPinia()
    const wrapper = mount(CardScoring, {
      props: { vm: { kind: "loading" } },
      global: { stubs: STUBS },
    })
    expect(wrapper.find('[data-testid="card-skeleton"]').exists()).toBe(true)
  })

  it("empty → affiche le CTA d'invitation", () => {
    withPinia()
    const wrapper = mount(CardScoring, {
      props: {
        vm: { kind: "empty", cta: { label: "Lancer", href: "/scoring" }, message: "Pas de données." },
      },
      global: { stubs: STUBS },
    })
    expect(wrapper.text()).toContain("Lancer")
    expect(wrapper.find('a[href="/scoring"]').exists()).toBe(true)
  })

  it("filled → affiche KPI, radar, source count", () => {
    withPinia()
    const wrapper = mount(CardScoring, {
      props: {
        vm: {
          kind: "filled",
          data: {
            scoreGlobal: 62,
            byAxis: { e: 60, s: 65, g: 70 },
            referentielCode: "GCF",
            referentielVersion: 2,
            computedAt: new Date(),
            sourceCount: 4,
            href: "/scoring",
          },
        },
      },
      global: { stubs: STUBS },
    })
    expect(wrapper.find(".kpi").attributes("data-value")).toBe("62")
    expect(wrapper.find(".radar").exists()).toBe(true)
    expect(wrapper.find('[data-testid="source-count"]').text()).toContain("4")
  })

  it("error → affiche message + bouton retry", async () => {
    withPinia()
    let retried = false
    const wrapper = mount(CardScoring, {
      props: {
        vm: { kind: "error", message: "Boum", retry: () => { retried = true } },
      },
      global: { stubs: STUBS },
    })
    expect(wrapper.text()).toContain("Boum")
    await wrapper.find("button").trigger("click")
    expect(retried).toBe(true)
  })
})
