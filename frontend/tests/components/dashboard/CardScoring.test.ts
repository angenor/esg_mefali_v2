// F44 T019 — Tests CardScoring (loading/empty/filled/error).
// F46 T019 — assertions additionnelles : NuxtLink to="/scoring" + aucun $fetch direct.
import { readFileSync } from "node:fs"
import { resolve } from "node:path"
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
    expect(wrapper.find('[data-testid="dashboard-source-list"]').text()).toContain("4")
  })

  // F44 T052 [US6] — VizSourcePin / DashboardSourceList cliquable ouvre popover.
  it("filled → source pin cliquable ouvre un popover listant l'accès aux sources", async () => {
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
    const pin = wrapper.find('[data-testid="source-pin"]')
    expect(pin.exists()).toBe(true)
    await pin.trigger("click")
    expect(wrapper.find('[data-testid="source-list-pop"]').exists()).toBe(true)
  })

  // F46 T019 — assertions additionnelles.
  it("F46 — filled → expose un lien 'Voir le scoring complet' vers /scoring", () => {
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
    const cta = wrapper.find('[data-testid="card-scoring-cta"]')
    expect(cta.exists()).toBe(true)
    expect(cta.attributes("href")).toBe("/scoring")
  })

  it("F46 — fichier source ne contient aucun $fetch direct", () => {
    const path = resolve(
      __dirname,
      "../../../app/components/dashboard/CardScoring.vue",
    )
    const content = readFileSync(path, "utf-8")
    expect(content).not.toMatch(/\$fetch\b/)
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
