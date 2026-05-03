// F44 T034 — Tests vitest useActionStepToggle.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { useActionStepToggle } from "../useActionStepToggle"
import { useDashboardBus, __resetDashboardBus, isLocalMutation } from "../useDashboardBus"
import { useDashboardStore } from "~/stores/dashboard"

declare global {
  // eslint-disable-next-line no-var
  var $fetch: unknown
  // eslint-disable-next-line no-var
  var useRuntimeConfig: unknown
}

interface Harness {
  pendingId: string | null
  complete: (id: string) => Promise<void>
}

function mountHarness(): { exposed: Harness; unmount: () => void } {
  const Comp = defineComponent({
    setup(_, { expose }) {
      const api = useActionStepToggle()
      expose({ get pendingId() { return api.pendingId.value }, complete: api.complete })
      return () => h("div")
    },
  })
  const wrapper = mount(Comp)
  return { exposed: wrapper.vm as unknown as Harness, unmount: () => wrapper.unmount() }
}

describe("useActionStepToggle", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    __resetDashboardBus()
    globalThis.useRuntimeConfig = () => ({ public: { apiBase: "http://api" } })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("complete() appelle PATCH /me/action-plan/steps/{id} avec body { status: 'done' }", async () => {
    const fetchMock = vi.fn().mockResolvedValue({})
    globalThis.$fetch = fetchMock
    const { exposed, unmount } = mountHarness()
    await exposed.complete("step-123")
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api/me/action-plan/steps/step-123",
      expect.objectContaining({
        method: "PATCH",
        body: { status: "done" },
        credentials: "include",
      }),
    )
    unmount()
  })

  it("traque l'id 5 s pour anti-loop (registre bus)", async () => {
    globalThis.$fetch = vi.fn().mockResolvedValue({})
    const { exposed, unmount } = mountHarness()
    await exposed.complete("step-abc")
    expect(isLocalMutation("step-abc")).toBe(true)
    unmount()
  })

  it("émet `action_step:completed` sur le bus avec source: 'dashboard'", async () => {
    globalThis.$fetch = vi.fn().mockResolvedValue({})
    const bus = useDashboardBus()
    const handler = vi.fn()
    bus.on("action_step:completed", handler)
    const { exposed, unmount } = mountHarness()
    await exposed.complete("step-xyz")
    expect(handler).toHaveBeenCalledWith(
      expect.objectContaining({ id: "step-xyz", source: "dashboard" }),
    )
    unmount()
  })

  it("invalide + refetch le bloc next_actions", async () => {
    globalThis.$fetch = vi.fn().mockResolvedValue({})
    const store = useDashboardStore()
    const invalidateSpy = vi.spyOn(store, "invalidate")
    const fetchSpy = vi.spyOn(store, "fetchSummary")
    const { exposed, unmount } = mountHarness()
    await exposed.complete("step-1")
    expect(invalidateSpy).toHaveBeenCalledWith("next_actions")
    expect(fetchSpy).toHaveBeenCalledWith({ scope: ["next_actions"] })
    unmount()
  })

  it("erreur 5xx → ne crash pas (rejette pour permettre revert) et reset pendingId", async () => {
    globalThis.$fetch = vi.fn().mockRejectedValue(new Error("500"))
    const { exposed, unmount } = mountHarness()
    await expect(exposed.complete("step-err")).rejects.toThrow()
    expect(exposed.pendingId).toBeNull()
    unmount()
  })

  it("appel concurrent sur même id → no-op (un seul PATCH)", async () => {
    const fetchMock = vi.fn().mockImplementation(
      (url: string) =>
        new Promise((r) => setTimeout(() => r(url.includes("/dashboard/summary") ? {} : {}), 20)),
    )
    globalThis.$fetch = fetchMock
    const { exposed, unmount } = mountHarness()
    const p1 = exposed.complete("step-dupe")
    const p2 = exposed.complete("step-dupe")
    await Promise.all([p1, p2])
    const patchCalls = fetchMock.mock.calls.filter(([url]) =>
      String(url).includes("/action-plan/steps/"),
    )
    expect(patchCalls.length).toBe(1)
    unmount()
  })
})
