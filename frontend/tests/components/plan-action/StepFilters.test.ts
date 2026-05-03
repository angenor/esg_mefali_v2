// F45 T026 — Tests StepFilters.
import { describe, expect, it } from "vitest"
import { mount } from "@vue/test-utils"
import StepFilters from "~/components/plan-action/StepFilters.vue"
import type { PlanFilters } from "~/types/actionPlan"

const EMPTY: PlanFilters = {
  priority: [],
  status: [],
  horizon: null,
  responsibleUserId: null,
}

describe("StepFilters", () => {
  it("toggle priorité émet change avec le delta", async () => {
    const w = mount(StepFilters, {
      props: { filters: EMPTY, responsibleOptions: [], hasActive: false },
    })
    await w.findAll(".pa-filters__chip")[0]!.trigger("click") // haute
    expect(w.emitted("change")?.[0]).toEqual([{ priority: ["haute"] }])
  })

  it("affiche le bouton Réinitialiser si hasActive", () => {
    const w = mount(StepFilters, {
      props: { filters: EMPTY, responsibleOptions: [], hasActive: true },
    })
    expect(w.find(".pa-filters__reset").exists()).toBe(true)
  })

  it("clic sur Réinitialiser émet reset", async () => {
    const w = mount(StepFilters, {
      props: { filters: EMPTY, responsibleOptions: [], hasActive: true },
    })
    await w.find(".pa-filters__reset").trigger("click")
    expect(w.emitted("reset")).toBeTruthy()
  })

  it("rend les options responsable", () => {
    const w = mount(StepFilters, {
      props: {
        filters: EMPTY,
        responsibleOptions: [{ id: "u1", label: "Alice" }],
        hasActive: false,
      },
    })
    expect(w.find("select").exists()).toBe(true)
    expect(w.findAll("option")).toHaveLength(2) // — + Alice
  })

  it("a11y : role=group et labels associés", () => {
    const w = mount(StepFilters, {
      props: { filters: EMPTY, responsibleOptions: [], hasActive: false },
    })
    expect(w.attributes("role")).toBe("group")
    expect(w.findAll('[role="group"]').length).toBeGreaterThanOrEqual(3)
  })
})
