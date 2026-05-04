// F46 T056 [US4] — Tests useIndicateurEdit.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { useIndicateurEdit } from "../useIndicateurEdit"
import { useScoringStore } from "~/stores/scoring"
import type { PillarRowVM } from "~/types/scoring"

const sheetOpen = vi.fn().mockResolvedValue(undefined)
const sheetClose = vi.fn().mockResolvedValue(undefined)
vi.mock("~/composables/useChatBottomSheet", () => ({
  useChatBottomSheet: () => ({
    open: sheetOpen,
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

function buildRow(overrides: Partial<PillarRowVM> = {}): PillarRowVM {
  return {
    indicateurId: "i1",
    indicateurCode: "EFFECTIFS_TOTAL",
    pillar: "S",
    status: "covered",
    scoreContribution: 10,
    weight: 0.2,
    normalizedValue: 0.5,
    rawValue: 100,
    sourceId: "src-1",
    isSourceRevoked: false,
    isEditable: true,
    reason: null,
    ...overrides,
  }
}

function mountHarness(): {
  api: ReturnType<typeof useIndicateurEdit>
  unmount: () => void
} {
  let api: ReturnType<typeof useIndicateurEdit> | null = null
  const Comp = defineComponent({
    setup() {
      api = useIndicateurEdit()
      return () => h("div")
    },
  })
  const w = mount(Comp)
  return { api: api!, unmount: () => w.unmount() }
}

describe("useIndicateurEdit", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    sheetOpen.mockClear()
    sheetClose.mockClear()
    pushMock.mockClear()
    busEmit.mockClear()
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("(a) row.isEditable=true → ouvre <ChatBottomSheet> ask_number avec valeur", async () => {
    const { api, unmount } = mountHarness()
    await api.openFor(buildRow(), "BOAD")
    expect(sheetOpen).toHaveBeenCalledTimes(1)
    const arg = sheetOpen.mock.calls[0]![0]
    expect(arg.tool).toBe("ask_number")
    expect(arg.payload.default).toBe(100)
    unmount()
  })

  it("(b) row.isEditable=false → toast + dispatch open_chat_for_indicateur, pas de sheet", async () => {
    const dispatchSpy = vi.spyOn(window, "dispatchEvent")
    const { api, unmount } = mountHarness()
    await api.openFor(buildRow({ isEditable: false }), "BOAD")
    expect(sheetOpen).not.toHaveBeenCalled()
    expect(pushMock).toHaveBeenCalled()
    expect(dispatchSpy).toHaveBeenCalled()
    const calledEvent = dispatchSpy.mock.calls.find(
      (c) => (c[0] as Event).type === "open_chat_for_indicateur",
    )
    expect(calledEvent).toBeTruthy()
    unmount()
  })

  it("(c) snapshot.active → toast + ne fait rien", async () => {
    const store = useScoringStore()
    store.snapshot = {
      active: true,
      frozenCalculationId: "c1",
      frozenSummary: null,
      frozenAt: "2026-04-15T10:00:00Z",
    }
    const { api, unmount } = mountHarness()
    await api.openFor(buildRow(), "BOAD")
    expect(sheetOpen).not.toHaveBeenCalled()
    expect(pushMock).toHaveBeenCalled()
    unmount()
  })

  it("(d) submit OK → store.editIndicateur appelé puis sheet fermé", async () => {
    const store = useScoringStore()
    const editSpy = vi.spyOn(store, "editIndicateur").mockResolvedValue()
    const { api, unmount } = mountHarness()
    const row = buildRow()
    await api.submit(150, row, "BOAD")
    expect(editSpy).toHaveBeenCalled()
    const args = editSpy.mock.calls[0]![0]
    expect(args.indicateurCode).toBe("EFFECTIFS_TOTAL")
    expect(args.newValue).toBe(150)
    expect(sheetClose).toHaveBeenCalledWith("freetext")
    unmount()
  })

  it("(e) submit KO → toast d'erreur, sheet pas fermé", async () => {
    const store = useScoringStore()
    vi.spyOn(store, "editIndicateur").mockRejectedValue(new Error("boom"))
    const { api, unmount } = mountHarness()
    const row = buildRow()
    await api.submit(150, row, "BOAD")
    expect(pushMock).toHaveBeenCalled()
    expect(pushMock.mock.calls.find((c) => c[0].severity === "error")).toBeTruthy()
    expect(sheetClose).not.toHaveBeenCalled()
    unmount()
  })
})
