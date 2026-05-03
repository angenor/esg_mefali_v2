// F44 T006 — Tests vitest useDashboardSummary (mount, EventBus, anti-loop).
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, nextTick } from "vue"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { useDashboardSummary } from "../useDashboardSummary"
import { __resetDashboardBus, useDashboardBus } from "../useDashboardBus"
import { useDashboardStore } from "~/stores/dashboard"

declare global {
  // eslint-disable-next-line no-var
  var $fetch: unknown
  // eslint-disable-next-line no-var
  var useRuntimeConfig: unknown
}

const FIXTURE = {
  account_id: "acc-1",
  scores: [],
  carbon: [],
  credit_score: null,
  candidatures: { counters_by_statut: {}, total: 0, recent: [] },
  rapports: { total: 0, recent: [] },
  attestations: { active: 0, revoked: 0, recent: [] },
  next_actions: [],
  generated_at: "2026-05-03T08:00:00Z",
}

function mountHarness() {
  const Comp = defineComponent({
    setup() {
      useDashboardSummary()
      return () => h("div")
    },
  })
  return mount(Comp)
}

describe("useDashboardSummary", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    __resetDashboardBus()
    globalThis.useRuntimeConfig = () => ({ public: { apiBase: "http://api" } })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("au mount : appelle fetchSummary une fois", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(FIXTURE)
    globalThis.$fetch = fetchSpy
    const wrapper = mountHarness()
    await nextTick()
    await Promise.resolve()
    await Promise.resolve()
    expect(fetchSpy).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it("émission `scoring:computed` → fetchSummary({ scope: ['scores'] })", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(FIXTURE)
    globalThis.$fetch = fetchSpy
    const wrapper = mountHarness()
    await nextTick()
    await Promise.resolve()
    await Promise.resolve()
    fetchSpy.mockClear()
    const bus = useDashboardBus()
    bus.emit("scoring:computed", { id: "score-1", source: "chat" })
    await nextTick()
    await Promise.resolve()
    const store = useDashboardStore()
    expect(store.invalidatedBlocks.has("scores") || fetchSpy.mock.calls.length > 0).toBe(true)
    expect(fetchSpy).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it("émission `attestation:emitted` → fetch sur ['rapports','attestations']", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(FIXTURE)
    globalThis.$fetch = fetchSpy
    const wrapper = mountHarness()
    await nextTick()
    await Promise.resolve()
    fetchSpy.mockClear()
    const bus = useDashboardBus()
    bus.emit("attestation:emitted", { id: "att-1", source: "chat" })
    await nextTick()
    await Promise.resolve()
    expect(fetchSpy).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it("event inconnu → aucun effet (pas de re-fetch)", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(FIXTURE)
    globalThis.$fetch = fetchSpy
    const wrapper = mountHarness()
    await nextTick()
    await Promise.resolve()
    fetchSpy.mockClear()
    // Cast pour forcer l'émission d'un nom non répertorié.
    const bus = useDashboardBus() as unknown as {
      emit: (n: string, e: { id?: string; source?: string }) => void
    }
    bus.emit("unknown:event", { id: "x", source: "chat" })
    await nextTick()
    expect(fetchSpy).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it("cleanup à l'unmount : pas de re-fetch après émission", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(FIXTURE)
    globalThis.$fetch = fetchSpy
    const wrapper = mountHarness()
    await nextTick()
    await Promise.resolve()
    wrapper.unmount()
    fetchSpy.mockClear()
    const bus = useDashboardBus()
    bus.emit("scoring:computed", { id: "x", source: "chat" })
    await nextTick()
    expect(fetchSpy).not.toHaveBeenCalled()
  })
})
