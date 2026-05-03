// F45 T008 — Tests useActionPlanCompletion.
import { beforeEach, describe, expect, it } from "vitest"
import { createPinia, setActivePinia } from "pinia"
import { useActionPlanStore } from "~/stores/actionPlan"
import { useActionPlanCompletion } from "../useActionPlanCompletion"
import type { ActionPlan, ActionStep } from "~/types/actionPlan"

function step(o: Partial<ActionStep>): ActionStep {
  return {
    id: o.id ?? "s",
    plan_id: "p",
    title: "t",
    description: null,
    category: "esg",
    priority: "moyenne",
    horizon_at: o.horizon_at ?? "2026-08-01",
    status: o.status ?? "todo",
    responsible_user_id: null,
    indicateur_id: null,
    source_id: null,
    created_at: "2026-05-01T00:00:00Z",
    updated_at: "2026-05-01T00:00:00Z",
    ...o,
  }
}

function plan(steps: ActionStep[]): ActionPlan {
  return {
    id: "p",
    account_id: "a",
    horizon_months: 24,
    version: 1,
    score_calculation_id: null,
    generated_at: "2026-05-01T00:00:00Z",
    generated_by_user_id: null,
    steps,
  }
}

describe("useActionPlanCompletion", () => {
  beforeEach(() => setActivePinia(createPinia()))

  it("calcule done/total/percent", () => {
    const store = useActionPlanStore()
    store.plan = plan(
      Array.from({ length: 10 }, (_, i) =>
        step({ id: `s${i}`, status: i < 3 ? "done" : "todo" }),
      ),
    )
    const c = useActionPlanCompletion()
    expect(c.value).toEqual({ totalVisible: 10, doneVisible: 3, percent: 30, hasData: true })
  })

  it("plan vide → hasData false, percent 0", () => {
    const store = useActionPlanStore()
    store.plan = plan([])
    const c = useActionPlanCompletion()
    expect(c.value.hasData).toBe(false)
    expect(c.value.percent).toBe(0)
  })

  it("filtre horizon=6 réduit le total", () => {
    const store = useActionPlanStore()
    store.plan = plan([
      step({ id: "a", horizon_at: "2026-06-01", status: "done" }), // ~1m
      step({ id: "b", horizon_at: "2026-12-01", status: "todo" }), // ~7m
    ])
    store.setHorizonView(6)
    const c = useActionPlanCompletion()
    expect(c.value.totalVisible).toBe(1)
    expect(c.value.doneVisible).toBe(1)
    expect(c.value.percent).toBe(100)
  })

  it("overlay optimiste 'done' compte dans le KPI", () => {
    const store = useActionPlanStore()
    store.plan = plan([step({ id: "a", status: "todo" })])
    store.stepStates = {
      a: { loading: true, error: null, optimisticOverlay: { status: "done" } },
    }
    const c = useActionPlanCompletion()
    expect(c.value.doneVisible).toBe(1)
  })
})
