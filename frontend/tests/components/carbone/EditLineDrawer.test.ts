// F47 T049 [US3] — Tests EditLineDrawer (composant orchestrateur sans UI propre).
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import EditLineDrawer from "~/components/carbone/EditLineDrawer.vue"

const openDrawer = vi.fn().mockResolvedValue(undefined)
const submit = vi.fn().mockResolvedValue(null)

vi.mock("~/composables/useCarbonEdit", () => ({
  useCarbonEdit: () => ({
    isOpen: { value: false },
    isSubmitting: { value: false },
    openDrawer,
    submit,
    cancel: vi.fn(),
  }),
}))

describe("EditLineDrawer", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    openDrawer.mockClear()
    submit.mockClear()
  })
  afterEach(() => vi.restoreAllMocks())

  it("(a) écoute window 'carbon:edit-line:open' et délègue", async () => {
    const w = mount(EditLineDrawer)
    window.dispatchEvent(
      new CustomEvent("carbon:edit-line:open", {
        detail: { year: 2026, line: null, posteCode: "electricite" },
      }),
    )
    await new Promise((r) => setTimeout(r, 0))
    expect(openDrawer).toHaveBeenCalledWith({
      year: 2026,
      line: null,
      posteCode: "electricite",
    })
    w.unmount()
  })

  it("(b) écoute 'carbon:edit-line:submit' et délègue", async () => {
    const w = mount(EditLineDrawer)
    window.dispatchEvent(
      new CustomEvent("carbon:edit-line:submit", {
        detail: {
          year: 2026,
          posteCode: "electricite",
          quantity: "45000",
          sourceId: "11111111-1111-1111-1111-111111111111",
        },
      }),
    )
    await new Promise((r) => setTimeout(r, 0))
    expect(submit).toHaveBeenCalled()
    w.unmount()
  })

  it("(c) cleanup retire les listeners après unmount", () => {
    const w = mount(EditLineDrawer)
    w.unmount()
    window.dispatchEvent(
      new CustomEvent("carbon:edit-line:open", {
        detail: { year: 2026, line: null, posteCode: "electricite" },
      }),
    )
    expect(openDrawer).not.toHaveBeenCalled()
  })
})
