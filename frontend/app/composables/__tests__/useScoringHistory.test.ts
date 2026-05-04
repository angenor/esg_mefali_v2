// F46 T048 [US3] — Tests useScoringHistory.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, nextTick } from "vue"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { useScoringHistory } from "../useScoringHistory"
import { useScoringStore } from "~/stores/scoring"
import type { ScoreHistoryOut } from "~/types/scoring"

const pushMock = vi.fn()
vi.mock("~/composables/useToast", () => ({
  useToast: () => ({ push: pushMock }),
}))

vi.mock("~/services/api/scoring", () => ({
  scoringApi: {
    listSummaries: vi.fn(),
    getDetail: vi.fn(),
    recompute: vi.fn(),
    getHistory: vi.fn(),
  },
}))

import { scoringApi } from "~/services/api/scoring"
const apiMock = scoringApi as unknown as {
  listSummaries: ReturnType<typeof vi.fn>
  getDetail: ReturnType<typeof vi.fn>
  recompute: ReturnType<typeof vi.fn>
  getHistory: ReturnType<typeof vi.fn>
}

function mountHarness(refCode: string): {
  api: ReturnType<typeof useScoringHistory>
  unmount: () => void
} {
  let api: ReturnType<typeof useScoringHistory> | null = null
  const Comp = defineComponent({
    setup() {
      api = useScoringHistory(refCode)
      return () => h("div")
    },
  })
  const w = mount(Comp)
  return { api: api!, unmount: () => w.unmount() }
}

function buildHistory(refCode: string, count: number): ScoreHistoryOut {
  // entries triées DESC (plus récent en premier).
  const now = Date.UTC(2026, 3, 30)
  return {
    entity_type: "entreprise",
    entity_id: "ent-1",
    referentiel_code: refCode,
    entries: Array.from({ length: count }, (_, i) => ({
      score_calculation_id: `calc-${i}`,
      computed_at: new Date(now - i * 86_400_000).toISOString(),
      score_global: 50 + i,
      referentiel_version: 1,
    })),
  }
}

describe("useScoringHistory", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    pushMock.mockClear()
    apiMock.listSummaries.mockReset()
    apiMock.getHistory.mockReset()
    ;(globalThis as unknown as { useRuntimeConfig: () => unknown }).useRuntimeConfig = () =>
      ({ public: { apiBase: "http://api" } })
    const store = useScoringStore()
    store.entityId = "ent-1"
    store.entityType = "entreprise"
  })
  afterEach(() => vi.restoreAllMocks())

  it("(a) load() appelle scoringApi.getHistory", async () => {
    apiMock.getHistory.mockResolvedValue(buildHistory("BOAD", 3))
    const { api, unmount } = mountHarness("BOAD")
    await api.load()
    expect(apiMock.getHistory).toHaveBeenCalledWith(
      "entreprise",
      "ent-1",
      "BOAD",
      12,
    )
    expect(api.entries.value.length).toBe(3)
    unmount()
  })

  it("(b) cache 60 s — second appel ne refait pas l'API", async () => {
    apiMock.getHistory.mockResolvedValue(buildHistory("BOAD", 2))
    const { api, unmount } = mountHarness("BOAD")
    await api.load()
    await api.load()
    expect(apiMock.getHistory).toHaveBeenCalledTimes(1)
    unmount()
  })

  it("(c) entries triées DESC", async () => {
    apiMock.getHistory.mockResolvedValue(buildHistory("BOAD", 3))
    const { api, unmount } = mountHarness("BOAD")
    await api.load()
    const dates = api.entries.value.map((e) => e.computedAt)
    const sorted = [...dates].sort().reverse()
    expect(dates).toEqual(sorted)
    unmount()
  })

  it("(d) erreur 404 → toast + entries=[]", async () => {
    apiMock.getHistory.mockRejectedValue(new Error("not_found"))
    const { api, unmount } = mountHarness("BOAD")
    await api.load()
    await nextTick()
    expect(api.entries.value).toEqual([])
    expect(pushMock).toHaveBeenCalled()
    unmount()
  })
})
