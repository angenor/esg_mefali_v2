// F45 T010 — Tests bucketing horizon plan d'action.
import { describe, it, expect } from "vitest"
import {
  bucketOf,
  groupStepsByBucket,
  mapPlanToTimelineBuckets,
  TIMELINE_BUCKET_ORDER,
} from "../mapPlanToTimelineBuckets"
import type { ActionPlan, ActionStep } from "~/types/actionPlan"

const BASE = "2026-05-01T00:00:00Z"

function step(overrides: Partial<ActionStep>): ActionStep {
  return {
    id: overrides.id ?? "s",
    plan_id: "p",
    title: "t",
    description: null,
    category: "esg",
    priority: "moyenne",
    horizon_at: overrides.horizon_at ?? "2026-06-01",
    status: "todo",
    responsible_user_id: null,
    indicateur_id: null,
    source_id: null,
    created_at: BASE,
    updated_at: BASE,
    ...overrides,
  }
}

function plan(steps: ActionStep[]): ActionPlan {
  return {
    id: "p",
    account_id: "a",
    horizon_months: 24,
    version: 1,
    score_calculation_id: null,
    generated_at: BASE,
    generated_by_user_id: null,
    steps,
  }
}

describe("bucketOf", () => {
  it("≤3 mois → lt3m", () => {
    expect(bucketOf(step({ horizon_at: "2026-06-01" }), BASE)).toBe("lt3m") // ~30j
  })
  it("entre 3 et 6 mois → 3to6m", () => {
    expect(bucketOf(step({ horizon_at: "2026-10-01" }), BASE)).toBe("3to6m") // ~5 mois
  })
  it("entre 6 et 12 mois → 6to12m", () => {
    expect(bucketOf(step({ horizon_at: "2027-03-01" }), BASE)).toBe("6to12m") // ~10 mois
  })
  it("entre 12 et 24 mois → 12to24m", () => {
    expect(bucketOf(step({ horizon_at: "2027-11-01" }), BASE)).toBe("12to24m") // ~18 mois
  })
  it(">24 mois → cap 12to24m", () => {
    expect(bucketOf(step({ horizon_at: "2028-11-01" }), BASE)).toBe("12to24m")
  })
  it("horizon_at vide / invalide → unscheduled", () => {
    expect(bucketOf(step({ horizon_at: "" as unknown as string }), BASE)).toBe("unscheduled")
  })
})

describe("mapPlanToTimelineBuckets", () => {
  it("retourne 5 buckets dans l'ordre stable", () => {
    const vm = mapPlanToTimelineBuckets(plan([]))
    expect(vm.buckets.map((b) => b.bucket)).toEqual(TIMELINE_BUCKET_ORDER)
  })
  it("rangeStart / rangeEnd cohérents avec generated_at", () => {
    const vm = mapPlanToTimelineBuckets(plan([]))
    const lt3 = vm.buckets.find((b) => b.bucket === "lt3m")!
    expect(lt3.rangeStart).toBe("2026-05-01")
    expect(lt3.rangeEnd?.startsWith("2026-08")).toBe(true)
    const unsch = vm.buckets.find((b) => b.bucket === "unscheduled")!
    expect(unsch.rangeStart).toBeNull()
    expect(unsch.rangeEnd).toBeNull()
  })
  it("horizonMonths et generatedAt remontent du plan", () => {
    const vm = mapPlanToTimelineBuckets(plan([]))
    expect(vm.horizonMonths).toBe(24)
    expect(vm.generatedAt).toBe(BASE)
  })
})

describe("groupStepsByBucket", () => {
  it("répartit selon la règle de bucketing", () => {
    const groups = groupStepsByBucket(
      plan([
        step({ id: "a", horizon_at: "2026-06-01" }), // lt3m
        step({ id: "b", horizon_at: "2026-10-01" }), // 3to6m
        step({ id: "c", horizon_at: "2027-03-01" }), // 6to12m
        step({ id: "d", horizon_at: "2027-11-01" }), // 12to24m
        step({ id: "e", horizon_at: "" as unknown as string }), // unscheduled
      ]),
    )
    expect(groups.lt3m.map((s) => s.id)).toEqual(["a"])
    expect(groups["3to6m"].map((s) => s.id)).toEqual(["b"])
    expect(groups["6to12m"].map((s) => s.id)).toEqual(["c"])
    expect(groups["12to24m"].map((s) => s.id)).toEqual(["d"])
    expect(groups.unscheduled.map((s) => s.id)).toEqual(["e"])
  })
})
