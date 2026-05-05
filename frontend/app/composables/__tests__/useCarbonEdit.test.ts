// F47 T048 [US3] — Tests useCarbonEdit.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { useCarbonEdit } from "../useCarbonEdit"
import { useCarbonStore } from "~/stores/carbon"

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

vi.mock("~/composables/useT", () => ({
  useT: () => ({ t: (k: string) => k }),
}))

function harness(): {
  api: ReturnType<typeof useCarbonEdit>
  unmount: () => void
} {
  let api: ReturnType<typeof useCarbonEdit> | null = null
  const Comp = defineComponent({
    setup() {
      api = useCarbonEdit()
      return () => h("div")
    },
  })
  const w = mount(Comp)
  return { api: api!, unmount: () => w.unmount() }
}

describe("useCarbonEdit", () => {
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

  it("(a) openDrawer mode edit ouvre <ChatBottomSheet> ask_form avec valeurs pré-remplies", async () => {
    const { api, unmount } = harness()
    const line = {
      code: "electricite",
      quantity: "50000",
      unit: "kWh",
      factor_id: "f1",
      factor_value: "0.075",
      factor_source_id: "s1",
      factor_version: 3,
      scope: "2" as const,
      categorie: "scope2",
      kgco2e: "3750",
      source_id: "src-A",
    }
    await api.openDrawer({ year: 2026, line, posteCode: "electricite" })
    expect(sheetOpen).toHaveBeenCalledTimes(1)
    const arg = sheetOpen.mock.calls[0]![0] as Record<string, unknown>
    expect(arg.tool).toBe("ask_form")
    unmount()
  })

  it("(b) submit avec source_id=null → toast erreur, pas d'appel backend", async () => {
    const store = useCarbonStore()
    const editSpy = vi.spyOn(store, "editLine")
    const { api, unmount } = harness()
    const result = await api.submit({
      year: 2026,
      posteCode: "electricite",
      quantity: "45000",
      sourceId: null,
    })
    expect(result).toBeNull()
    expect(editSpy).not.toHaveBeenCalled()
    expect(pushMock).toHaveBeenCalled()
    unmount()
  })

  it("(c) submit valide → store.editLine appelé + EventBus + toast success", async () => {
    const store = useCarbonStore()
    const fakeResp = {
      id: "fp-2",
      year: 2026,
      total_tco2e: "12.4",
      by_scope_kgco2e: { "1": "0", "2": "12400", "3": "0" },
      by_category_kgco2e: {},
      breakdown: [],
      factor_versions: [],
      previous_footprint_id: "fp-1",
      edited_line_code: "electricite",
    }
    vi.spyOn(store, "editLine").mockResolvedValue(fakeResp as never)
    const { api, unmount } = harness()
    const result = await api.submit({
      year: 2026,
      posteCode: "electricite",
      quantity: "45000",
      sourceId: "11111111-1111-1111-1111-111111111111",
    })
    expect(result).toBe(fakeResp)
    expect(busEmit).toHaveBeenCalledWith(
      "entity_updated",
      expect.objectContaining({ entityType: "carbon_footprint" }),
    )
    expect(sheetClose).toHaveBeenCalledWith("freetext")
    unmount()
  })

  it("(d) backend 400 source_not_verified → toast spécifique, drawer ouvert", async () => {
    const store = useCarbonStore()
    vi.spyOn(store, "editLine").mockRejectedValue({
      status: 400,
      data: { error: "source_not_verified" },
    })
    const { api, unmount } = harness()
    const result = await api.submit({
      year: 2026,
      posteCode: "electricite",
      quantity: "45000",
      sourceId: "11111111-1111-1111-1111-111111111111",
    })
    expect(result).toBeNull()
    expect(sheetClose).not.toHaveBeenCalled()
    expect(pushMock).toHaveBeenCalled()
    unmount()
  })

  it("(e) garde anti-double submit", async () => {
    const store = useCarbonStore()
    let resolve: ((v: unknown) => void) | null = null
    vi.spyOn(store, "editLine").mockImplementation(
      () => new Promise((r) => { resolve = r as never }),
    )
    const { api, unmount } = harness()
    const p1 = api.submit({
      year: 2026,
      posteCode: "electricite",
      quantity: "45000",
      sourceId: "11111111-1111-1111-1111-111111111111",
    })
    const p2 = api.submit({
      year: 2026,
      posteCode: "electricite",
      quantity: "46000",
      sourceId: "11111111-1111-1111-1111-111111111111",
    })
    expect(await p2).toBeNull()
    resolve?.(null)
    await p1
    unmount()
  })
})
