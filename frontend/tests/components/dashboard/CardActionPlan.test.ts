// F44 T033 — Tests CardActionPlan (US2 toggle).
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import CardActionPlan from "~/components/dashboard/CardActionPlan.vue"
import { __resetDashboardBus } from "~/composables/useDashboardBus"

declare global {
  // eslint-disable-next-line no-var
  var $fetch: unknown
  // eslint-disable-next-line no-var
  var useRuntimeConfig: unknown
}

const STUBS = {
  NuxtLink: { props: ["to"], template: '<a :href="to" :data-href="to"><slot/></a>' },
  UiCard: { template: "<section><slot name='header'/><slot/></section>" },
  UiBadge: { props: ["severity"], template: '<span class="badge"><slot/></span>' },
}

function makeFilledVm(steps: Array<{ id: string; title: string; priority?: "haute" | "moyenne" | "basse"; horizonAt?: Date }>) {
  return {
    kind: "filled" as const,
    data: {
      steps: steps.map((s) => ({
        id: s.id,
        title: s.title,
        category: "energie",
        priority: s.priority ?? "haute",
        horizonAt: s.horizonAt ?? new Date("2026-12-31"),
      })),
      href: "/plan-action",
    },
  }
}

describe("CardActionPlan", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    __resetDashboardBus()
    globalThis.useRuntimeConfig = () => ({ public: { apiBase: "http://api" } })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("filled → max 3 étapes, ordre tri (priorité haute d'abord puis horizon ASC)", () => {
    // L'adapter (mapSummaryToCardViewModels) trie déjà ; le composant respecte l'ordre VM.
    const vm = makeFilledVm([
      { id: "a", title: "A", priority: "haute", horizonAt: new Date("2027-01-01") },
      { id: "b", title: "B", priority: "haute", horizonAt: new Date("2026-06-01") },
      { id: "c", title: "C", priority: "moyenne" },
    ])
    const wrapper = mount(CardActionPlan, { props: { vm }, global: { stubs: STUBS } })
    const titles = wrapper.findAll('[data-testid="action-step"]').map((li) => li.text())
    expect(titles.length).toBe(3)
    expect(titles[0]).toContain("A")
    expect(titles[1]).toContain("B")
    expect(titles[2]).toContain("C")
  })

  it("checkbox cliquable → optimistic update (case grisée + spinner) + appel PATCH", async () => {
    let resolvePatch: (v?: unknown) => void = () => undefined
    const fetchMock = vi.fn().mockImplementation(
      () => new Promise((r) => { resolvePatch = r }),
    )
    globalThis.$fetch = fetchMock

    const vm = makeFilledVm([{ id: "step-1", title: "Audit énergétique" }])
    const wrapper = mount(CardActionPlan, { props: { vm }, global: { stubs: STUBS } })

    const cb = wrapper.find('[data-testid="action-step-check"]')
    await cb.trigger("change")
    await flushPromises()

    // Spinner visible pendant la requête.
    expect(wrapper.find('[data-testid="action-step-spinner"]').exists()).toBe(true)
    // Étape grisée (classe `is-completing`).
    expect(wrapper.find('li.is-completing').exists()).toBe(true)

    resolvePatch({})
    await flushPromises()
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api/me/action-plan/steps/step-1",
      expect.objectContaining({ method: "PATCH", body: { status: "done" } }),
    )
  })

  it("erreur 5xx → revert visuel (case redevient cliquable)", async () => {
    globalThis.$fetch = vi.fn().mockRejectedValue(new Error("500"))
    const vm = makeFilledVm([{ id: "step-err", title: "Étape" }])
    const wrapper = mount(CardActionPlan, { props: { vm }, global: { stubs: STUBS } })
    await wrapper.find('[data-testid="action-step-check"]').trigger("change")
    await flushPromises()
    // Après erreur, la classe is-completing doit avoir été retirée (revert).
    expect(wrapper.find('li.is-completing').exists()).toBe(false)
  })

  it("empty → CTA rendu", () => {
    const wrapper = mount(CardActionPlan, {
      props: {
        vm: { kind: "empty", cta: { label: "Construire", href: "/plan-action" }, message: "" },
      },
      global: { stubs: STUBS },
    })
    expect(wrapper.find('a[href="/plan-action"]').exists()).toBe(true)
  })
})
