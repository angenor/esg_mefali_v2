// F44 T018 — Tests WelcomeStrip (salutation, date relative, lien chat).
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { mount } from "@vue/test-utils"
import WelcomeStrip from "~/components/dashboard/WelcomeStrip.vue"

const NuxtLinkStub = {
  props: ["to"],
  template: '<a :href="to" class="welcome-strip__cta"><slot/></a>',
}

describe("WelcomeStrip", () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it("affiche 'Bonjour' le matin", () => {
    vi.setSystemTime(new Date("2026-05-03T09:00:00"))
    const wrapper = mount(WelcomeStrip, {
      props: { raisonSociale: "ACME SARL", lastDiagnosticAt: null },
      global: { stubs: { NuxtLink: NuxtLinkStub } },
    })
    expect(wrapper.text()).toContain("Bonjour")
    expect(wrapper.text()).toContain("ACME SARL")
  })

  it("affiche 'Bonsoir' après 18h", () => {
    vi.setSystemTime(new Date("2026-05-03T20:00:00"))
    const wrapper = mount(WelcomeStrip, {
      props: { raisonSociale: "ACME", lastDiagnosticAt: null },
      global: { stubs: { NuxtLink: NuxtLinkStub } },
    })
    expect(wrapper.text()).toContain("Bonsoir")
  })

  it("rend 'Aucun diagnostic encore' si lastDiagnosticAt=null", () => {
    vi.setSystemTime(new Date("2026-05-03T10:00:00"))
    const wrapper = mount(WelcomeStrip, {
      props: { raisonSociale: "ACME", lastDiagnosticAt: null },
      global: { stubs: { NuxtLink: NuxtLinkStub } },
    })
    expect(wrapper.text()).toContain("Aucun diagnostic encore")
  })

  it("rend une date relative quand lastDiagnosticAt fourni", () => {
    vi.setSystemTime(new Date("2026-05-03T10:00:00"))
    const wrapper = mount(WelcomeStrip, {
      props: {
        raisonSociale: "ACME",
        lastDiagnosticAt: new Date("2026-05-01T10:00:00"),
      },
      global: { stubs: { NuxtLink: NuxtLinkStub } },
    })
    expect(wrapper.text()).toContain("Dernier diagnostic")
  })

  it("contient un lien /chat", () => {
    vi.setSystemTime(new Date("2026-05-03T10:00:00"))
    const wrapper = mount(WelcomeStrip, {
      props: { raisonSociale: "ACME", lastDiagnosticAt: null },
      global: { stubs: { NuxtLink: NuxtLinkStub } },
    })
    const cta = wrapper.find("a.welcome-strip__cta")
    expect(cta.exists()).toBe(true)
    expect(cta.attributes("href")).toBe("/chat")
  })
})
