// F45 T005 — Tests store actionPlan.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { createPinia, setActivePinia } from "pinia"
import { useActionPlanStore, PLAN_CACHE_TTL_MS } from "../actionPlan"
import type { ActionPlan, ActionStep } from "~/types/actionPlan"

declare global {
  // eslint-disable-next-line no-var
  var $fetch: unknown
  // eslint-disable-next-line no-var
  var useRuntimeConfig: unknown
}

function makeStep(o: Partial<ActionStep> = {}): ActionStep {
  return {
    id: "s1",
    plan_id: "p1",
    title: "t",
    description: null,
    category: "esg",
    priority: "moyenne",
    horizon_at: "2026-08-01",
    status: "todo",
    responsible_user_id: null,
    indicateur_id: null,
    source_id: null,
    created_at: "2026-05-01T00:00:00Z",
    updated_at: "2026-05-01T00:00:00Z",
    ...o,
  }
}

function makePlan(steps: ActionStep[] = [makeStep()]): ActionPlan {
  return {
    id: "p1",
    account_id: "a",
    horizon_months: 24,
    version: 1,
    score_calculation_id: null,
    generated_at: "2026-05-01T00:00:00Z",
    generated_by_user_id: null,
    steps,
  }
}

describe("useActionPlanStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    globalThis.useRuntimeConfig = () => ({ public: { apiBase: "http://api" } })
  })
  afterEach(() => {
    delete (globalThis as Record<string, unknown>).$fetch
  })

  it("fetchPlan met à jour state.plan et lastFetchedAt", async () => {
    const plan = makePlan()
    globalThis.$fetch = vi.fn().mockResolvedValue(plan)
    const store = useActionPlanStore()
    await store.fetchPlan()
    expect(store.plan).toEqual(plan)
    expect(store.lastFetchedAt).not.toBeNull()
  })

  it("respecte le cache 60 s sauf force=true", async () => {
    const fetch = vi.fn().mockResolvedValue(makePlan())
    globalThis.$fetch = fetch
    const store = useActionPlanStore()
    await store.fetchPlan()
    await store.fetchPlan()
    expect(fetch).toHaveBeenCalledTimes(1)
    await store.fetchPlan(true)
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it("expire le cache après PLAN_CACHE_TTL_MS", async () => {
    const fetch = vi.fn().mockResolvedValue(makePlan())
    globalThis.$fetch = fetch
    const store = useActionPlanStore()
    await store.fetchPlan()
    store.lastFetchedAt = Date.now() - PLAN_CACHE_TTL_MS - 100
    await store.fetchPlan()
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it("dédupe les fetches concurrents", async () => {
    let resolveFn: ((p: ActionPlan) => void) | null = null
    const fetch = vi.fn(
      () => new Promise<ActionPlan>((resolve) => (resolveFn = resolve)),
    )
    globalThis.$fetch = fetch
    const store = useActionPlanStore()
    const p1 = store.fetchPlan()
    const p2 = store.fetchPlan()
    resolveFn!(makePlan())
    await Promise.all([p1, p2])
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it("applyOptimisticPatch applique l'overlay puis remplace par la réponse 200", async () => {
    globalThis.$fetch = vi
      .fn()
      .mockResolvedValueOnce(makePlan()) // GET
      .mockResolvedValueOnce(makeStep({ id: "s1", status: "done" })) // PATCH
    const store = useActionPlanStore()
    await store.fetchPlan()
    await store.applyOptimisticPatch("s1", { status: "done" })
    expect(store.plan?.steps[0]?.status).toBe("done")
    expect(store.stepStates["s1"]?.optimisticOverlay).toBeNull()
  })

  it("rollback complet sur erreur 500", async () => {
    globalThis.$fetch = vi
      .fn()
      .mockResolvedValueOnce(makePlan()) // GET
      .mockRejectedValueOnce(new Error("boom"))
    const store = useActionPlanStore()
    await store.fetchPlan()
    await expect(store.applyOptimisticPatch("s1", { status: "done" })).rejects.toThrow("boom")
    expect(store.plan?.steps[0]?.status).toBe("todo")
    expect(store.stepStates["s1"]?.error).toBe("boom")
  })

  it("setFilters / setHorizonView mettent à jour le state", () => {
    const store = useActionPlanStore()
    store.setFilters({ priority: ["haute"] })
    expect(store.filters.priority).toEqual(["haute"])
    store.setHorizonView(6)
    expect(store.horizonView).toBe(6)
  })

  it("regenerate pose et lève regenerating et remplace le plan", async () => {
    const v2 = { ...makePlan(), version: 2 }
    let observed = false
    const fetch = vi.fn().mockImplementationOnce(async () => {
      observed = true
      return v2
    })
    globalThis.$fetch = fetch
    const store = useActionPlanStore()
    const p = store.regenerate(12)
    expect(store.regenerating).toBe(true)
    await p
    expect(observed).toBe(true)
    expect(store.regenerating).toBe(false)
    expect(store.plan?.version).toBe(2)
  })

  it("regenerate ignore les double-clics", async () => {
    const fetch = vi.fn().mockResolvedValue(makePlan())
    globalThis.$fetch = fetch
    const store = useActionPlanStore()
    const a = store.regenerate(12)
    const b = store.regenerate(12)
    await Promise.all([a, b])
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it("invalidateStep re-fetch et remplace uniquement la step ciblée", async () => {
    const initial = makePlan([
      makeStep({ id: "s1", status: "todo" }),
      makeStep({ id: "s2", status: "todo" }),
    ])
    const fresh = makePlan([
      makeStep({ id: "s1", status: "done" }),
      makeStep({ id: "s2", status: "todo" }),
    ])
    globalThis.$fetch = vi.fn().mockResolvedValueOnce(initial).mockResolvedValueOnce(fresh)
    const store = useActionPlanStore()
    await store.fetchPlan()
    const s2Ref = store.plan?.steps.find((s) => s.id === "s2")
    await store.invalidateStep("s1")
    expect(store.plan?.steps.find((s) => s.id === "s1")?.status).toBe("done")
    expect(store.plan?.steps.find((s) => s.id === "s2")).toBe(s2Ref)
  })
})
