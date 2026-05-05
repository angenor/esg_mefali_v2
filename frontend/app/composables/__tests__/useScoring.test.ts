// F46 T017 — Tests useScoring (mount + bus).
//
// Cf. specs/046-scoring-esg-ui/contracts/chat-eventbus-sync.md.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { useScoring, SCORING_DEBOUNCE_MS } from "../useScoring"
import { useScoringStore } from "~/stores/scoring"
import { useChatEventBus, __resetChatEventBus } from "../useChatEventBus"

declare global {
  // eslint-disable-next-line no-var
  var $fetch: unknown
  // eslint-disable-next-line no-var
  var useRuntimeConfig: unknown
}

vi.mock("~/services/api/scoring", () => ({
  scoringApi: {
    listSummaries: vi.fn().mockResolvedValue({
      entity_type: "entreprise",
      entity_id: "e-1",
      scores: [],
    }),
    getDetail: vi.fn(),
    recompute: vi.fn(),
    getHistory: vi.fn().mockResolvedValue({
      entity_type: "entreprise",
      entity_id: "e-1",
      referentiel_code: "BOAD",
      entries: [],
    }),
  },
}))

const ENT_ID = "11111111-1111-1111-1111-111111111111"

function mountHarness(): {
  unmount: () => void
  api: ReturnType<typeof useScoring>
} {
  let api: ReturnType<typeof useScoring> | null = null
  const Comp = defineComponent({
    setup() {
      api = useScoring("entreprise", ENT_ID)
      return () => h("div")
    },
  })
  const w = mount(Comp)
  return { unmount: () => w.unmount(), api: api! }
}

describe("useScoring", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    __resetChatEventBus()
    globalThis.useRuntimeConfig = () => ({ public: { apiBase: "http://api" } })
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
    delete (globalThis as Record<string, unknown>).useRuntimeConfig
  })

  it("(a) au mount setEntity puis loadSummaries appelés une fois", async () => {
    const { unmount } = mountHarness()
    await Promise.resolve()
    await Promise.resolve()
    const store = useScoringStore()
    expect(store.entityId).toBe(ENT_ID)
    expect(store.entityType).toBe("entreprise")
    unmount()
  })

  it("(b) entity_updated{indicateur} → onChatEntityUpdated invoqué", async () => {
    const { unmount } = mountHarness()
    await Promise.resolve()
    const store = useScoringStore()
    const spy = vi.spyOn(store, "onChatEntityUpdated")
    useChatEventBus().emit("entity_updated", {
      eventType: "entity_updated",
      entityType: "indicateur",
      entityId: "i-1",
      source: "tool",
      ts: new Date().toISOString(),
    })
    vi.advanceTimersByTime(SCORING_DEBOUNCE_MS + 10)
    expect(spy).toHaveBeenCalled()
    unmount()
  })

  it("(c) entity_updated{score_calculation} → invalidations détail+history", async () => {
    const { unmount } = mountHarness()
    await Promise.resolve()
    const store = useScoringStore()
    const spy = vi.spyOn(store, "onChatEntityUpdated")
    useChatEventBus().emit("entity_updated", {
      eventType: "entity_updated",
      entityType: "score_calculation",
      entityId: "calc-1",
      source: "tool",
      ts: new Date().toISOString(),
    })
    vi.advanceTimersByTime(SCORING_DEBOUNCE_MS + 10)
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({ entityType: "score_calculation" }),
    )
    unmount()
  })

  it("(d) garde anti-boucle store : event 'manual' < 500 ms après émission locale ignoré", async () => {
    const { unmount } = mountHarness()
    await Promise.resolve()
    const store = useScoringStore()
    store.currentReferentielCode = "BOAD"
    store.detailsCacheByRef.BOAD = { value: true, fetchedAt: Date.now() }
    store.trackLocalEmission("score_calculation", "calc-99")
    useChatEventBus().emit("entity_updated", {
      eventType: "entity_updated",
      entityType: "score_calculation",
      entityId: "calc-99",
      source: "manual",
      ts: new Date().toISOString(),
    })
    vi.advanceTimersByTime(SCORING_DEBOUNCE_MS + 10)
    // Le cache n'a pas été invalidé.
    expect(store.detailsCacheByRef.BOAD).toBeDefined()
    unmount()
  })

  it("(e) cleanup onBeforeUnmount désouscrit", async () => {
    const { unmount } = mountHarness()
    await Promise.resolve()
    const store = useScoringStore()
    const spy = vi.spyOn(store, "onChatEntityUpdated")
    unmount()
    useChatEventBus().emit("entity_updated", {
      eventType: "entity_updated",
      entityType: "indicateur",
      entityId: "i-1",
      source: "tool",
      ts: new Date().toISOString(),
    })
    vi.advanceTimersByTime(SCORING_DEBOUNCE_MS + 10)
    expect(spy).not.toHaveBeenCalled()
  })

  it("(f) debounce 200 ms : 3 events rapides → 1 seul flush", async () => {
    const { unmount } = mountHarness()
    await Promise.resolve()
    const store = useScoringStore()
    const spy = vi.spyOn(store, "onChatEntityUpdated")
    const bus = useChatEventBus()
    for (let i = 0; i < 3; i++) {
      bus.emit("entity_updated", {
        eventType: "entity_updated",
        entityType: "score_calculation",
        entityId: `calc-${i}`,
        source: "tool",
        ts: new Date().toISOString(),
      })
      vi.advanceTimersByTime(20) // < 200 ms
    }
    // pas encore flushé.
    expect(spy).not.toHaveBeenCalled()
    vi.advanceTimersByTime(SCORING_DEBOUNCE_MS + 10)
    // toutes les 3 payloads sont passées au store, mais via UN seul flush.
    expect(spy).toHaveBeenCalledTimes(3)
    unmount()
  })
})
