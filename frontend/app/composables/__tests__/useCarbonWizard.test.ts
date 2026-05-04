// F47 T071 [US6] — Tests useCarbonWizard.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { useCarbonWizard } from "../useCarbonWizard"
import { useCarbonStore } from "~/stores/carbon"

const sheetClose = vi.fn().mockResolvedValue(undefined)
vi.mock("~/composables/useChatBottomSheet", () => ({
  useChatBottomSheet: () => ({
    open: vi.fn().mockResolvedValue(undefined),
    close: sheetClose,
    current: { value: null },
    isOpen: { value: false },
    rebuildFromThread: vi.fn(),
  }),
}))

const pushMock = vi.fn()
vi.mock("~/composables/useToast", () => ({
  useToast: () => ({ push: pushMock }),
}))

const busEmit = vi.fn()
vi.mock("~/composables/useChatEventBus", () => ({
  useChatEventBus: () => ({
    on: vi.fn(() => () => {}),
    off: vi.fn(),
    emit: busEmit,
  }),
  __resetChatEventBus: vi.fn(),
}))

vi.mock("~/composables/useT", () => ({
  useT: () => ({ t: (k: string) => k }),
}))

const computeInitialMock = vi.fn()
vi.mock("~/services/api/carbon", () => ({
  carbonApi: {
    fetchIndex: vi.fn().mockResolvedValue([]),
    fetchFootprint: vi.fn(),
    recompute: vi.fn(),
    editLine: vi.fn(),
    computeInitial: (year: number, data: unknown) =>
      computeInitialMock(year, data),
  },
}))

function harness(): {
  api: ReturnType<typeof useCarbonWizard>
  unmount: () => void
} {
  let api: ReturnType<typeof useCarbonWizard> | null = null
  const Comp = defineComponent({
    setup() {
      api = useCarbonWizard()
      return () => h("div")
    },
  })
  const w = mount(Comp)
  return { api: api!, unmount: () => w.unmount() }
}

const VALID_UUID = "11111111-1111-1111-1111-111111111111"

describe("useCarbonWizard", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    sheetClose.mockClear()
    pushMock.mockClear()
    busEmit.mockClear()
    computeInitialMock.mockReset()
    if (typeof window !== "undefined") {
      window.localStorage.clear()
    }
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("(a) start initialise un draft", () => {
    const { api, unmount } = harness()
    api.start(2026, null)
    expect(api.draft.value?.step).toBe(1)
    expect(api.draft.value?.year).toBe(2026)
    unmount()
  })

  it("(b) setAnswer + nextStep avance", () => {
    const { api, unmount } = harness()
    api.start(2026, null)
    api.setAnswer("energy", { quantity: "12000", unit: "kWh", source_id: VALID_UUID })
    expect(api.nextStep()).toBe(true)
    expect(api.step.value).toBe(2)
    unmount()
  })

  it("(c) nextStep refuse si la step n'est pas valide (source_id absent)", () => {
    const { api, unmount } = harness()
    api.start(2026, null)
    api.setAnswer("energy", { quantity: "12000", unit: "kWh", source_id: "not-uuid" } as never)
    expect(api.nextStep()).toBe(false)
    unmount()
  })

  it("(d) submit complet → computeInitial appelé + draft purgé + EventBus", async () => {
    const fakeFp = {
      id: "fp-1",
      year: 2026,
      total_tco2e: "1.0",
      by_scope_kgco2e: { "1": "0", "2": "1000", "3": "0" },
      by_category_kgco2e: {},
      breakdown: [],
      factor_versions: [],
    }
    computeInitialMock.mockResolvedValue(fakeFp)
    const { api, unmount } = harness()
    api.start(2026, null)
    api.setAnswer("energy", { quantity: "12000", unit: "kWh", source_id: VALID_UUID })
    api.nextStep()
    api.setAnswer("mobility", { quantity: "8000", unit: "km", source_id: VALID_UUID })
    api.nextStep()
    api.setAnswer("purchases", { quantity: "1500", unit: "EUR", source_id: VALID_UUID })
    const result = await api.submit(null)
    expect(result).toBe(fakeFp)
    expect(computeInitialMock).toHaveBeenCalledWith(2026, expect.any(Array))
    expect(api.draft.value).toBeNull()
    expect(busEmit).toHaveBeenCalled()
    unmount()
  })

  it("(e) submit incomplet → null + toast", async () => {
    const { api, unmount } = harness()
    api.start(2026, null)
    api.setAnswer("energy", { quantity: "12000", unit: "kWh", source_id: VALID_UUID })
    const result = await api.submit(null)
    expect(result).toBeNull()
    expect(pushMock).toHaveBeenCalled()
    unmount()
  })

  it("(f) hydrate restaure depuis localStorage", () => {
    const accountId = null
    const draft = {
      step: 2,
      year: 2026,
      answers: {
        energy: { quantity: "12000", unit: "kWh", source_id: VALID_UUID },
      },
      saved_at: new Date().toISOString(),
    }
    window.localStorage.setItem(`carbon-wizard-anon-draft`, JSON.stringify(draft))
    const { api, unmount } = harness()
    api.hydrate(accountId)
    expect(api.draft.value?.step).toBe(2)
    expect(useCarbonStore().wizardDraft?.step).toBe(2)
    unmount()
  })

  it("(g) cancel purge le draft", () => {
    const { api, unmount } = harness()
    api.start(2026, null)
    expect(api.draft.value).not.toBeNull()
    api.cancel(null)
    expect(api.draft.value).toBeNull()
    unmount()
  })

  it("(h) freeText émet event window 'carbon:wizard:freetext'", async () => {
    const spy = vi.spyOn(window, "dispatchEvent")
    const { api, unmount } = harness()
    await api.freeText()
    expect(sheetClose).toHaveBeenCalledWith("freetext")
    const found = spy.mock.calls.find(
      (c) => (c[0] as Event).type === "carbon:wizard:freetext",
    )
    expect(found).toBeTruthy()
    unmount()
  })
})
