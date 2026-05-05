// F45 T006 — Tests useActionPlan + abonnement EventBus.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { useActionPlan } from "../useActionPlan"
import { useActionPlanStore } from "~/stores/actionPlan"
import { useChatEventBus, __resetChatEventBus } from "../useChatEventBus"

declare global {
  // eslint-disable-next-line no-var
  var $fetch: unknown
  // eslint-disable-next-line no-var
  var useRuntimeConfig: unknown
}

function makePlan(): import("~/types/actionPlan").ActionPlan {
  return {
    id: "p",
    account_id: "a",
    horizon_months: 24,
    version: 1,
    score_calculation_id: null,
    generated_at: "2026-05-01T00:00:00Z",
    generated_by_user_id: null,
    steps: [],
  }
}

function mountHarness(): { unmount: () => void; api: ReturnType<typeof useActionPlan> } {
  let api: ReturnType<typeof useActionPlan> | null = null
  const Comp = defineComponent({
    setup() {
      api = useActionPlan()
      return () => h("div")
    },
  })
  const w = mount(Comp)
  return { unmount: () => w.unmount(), api: api! }
}

describe("useActionPlan", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    __resetChatEventBus()
    globalThis.useRuntimeConfig = () => ({ public: { apiBase: "http://api" } })
    globalThis.$fetch = vi.fn().mockResolvedValue(makePlan())
  })
  afterEach(() => {
    delete (globalThis as Record<string, unknown>).$fetch
    delete (globalThis as Record<string, unknown>).useRuntimeConfig
  })

  it("fetchPlan appelé une fois au mount", async () => {
    const { unmount } = mountHarness()
    await Promise.resolve()
    await Promise.resolve()
    expect(globalThis.$fetch).toHaveBeenCalledTimes(1)
    unmount()
  })

  it("entity_updated{action_step} → invalidateStep", async () => {
    const { unmount } = mountHarness()
    const store = useActionPlanStore()
    await Promise.resolve()
    const spy = vi.spyOn(store, "invalidateStep").mockResolvedValue()
    useChatEventBus().emit("entity_updated", {
      eventType: "entity_updated",
      entityType: "action_step",
      entityId: "step-id",
      source: "llm",
      ts: new Date().toISOString(),
    })
    expect(spy).toHaveBeenCalledWith("step-id")
    unmount()
  })

  it("entity_updated{action_plan} → fetchPlan(force=true)", async () => {
    const { unmount } = mountHarness()
    const store = useActionPlanStore()
    await Promise.resolve()
    const spy = vi.spyOn(store, "fetchPlan").mockResolvedValue()
    useChatEventBus().emit("entity_updated", {
      eventType: "entity_updated",
      entityType: "action_plan",
      entityId: "plan-id",
      source: "llm",
      ts: new Date().toISOString(),
    })
    expect(spy).toHaveBeenCalledWith(true)
    unmount()
  })

  it("garde anti-boucle 500 ms", async () => {
    const { unmount } = mountHarness()
    const store = useActionPlanStore()
    await Promise.resolve()
    store.trackLocalEmit("step-id")
    const spy = vi.spyOn(store, "invalidateStep").mockResolvedValue()
    useChatEventBus().emit("entity_updated", {
      eventType: "entity_updated",
      entityType: "action_step",
      entityId: "step-id",
      source: "manual",
      ts: new Date().toISOString(),
    })
    expect(spy).not.toHaveBeenCalled()
    unmount()
  })

  it("désouscrit au unmount", async () => {
    const { unmount } = mountHarness()
    const store = useActionPlanStore()
    await Promise.resolve()
    unmount()
    const spy = vi.spyOn(store, "invalidateStep").mockResolvedValue()
    useChatEventBus().emit("entity_updated", {
      eventType: "entity_updated",
      entityType: "action_step",
      entityId: "x",
      source: "llm",
      ts: new Date().toISOString(),
    })
    expect(spy).not.toHaveBeenCalled()
  })
})
