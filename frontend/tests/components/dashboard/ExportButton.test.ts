// F44 T043 — Tests ExportButton (état disabled, événement exported, intégration toast).
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import ExportButton from "~/components/dashboard/ExportButton.vue"

declare global {
  // eslint-disable-next-line no-var
  var $fetch: unknown
  // eslint-disable-next-line no-var
  var useRuntimeConfig: unknown
}

describe("ExportButton", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    globalThis.useRuntimeConfig = () => ({ public: { apiBase: "http://api" } })
    // @ts-expect-error happy-dom
    global.URL.createObjectURL = vi.fn(() => "blob:fake")
    // @ts-expect-error happy-dom
    global.URL.revokeObjectURL = vi.fn()
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined)
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it("clic → émet `exported` et déclenche download", async () => {
    globalThis.$fetch = vi.fn().mockResolvedValue({ entreprise: {} })
    const wrapper = mount(ExportButton)
    await wrapper.find('[data-testid="export-button"]').trigger("click")
    await flushPromises()
    expect(wrapper.emitted("exported")).toBeTruthy()
    expect(globalThis.$fetch).toHaveBeenCalledTimes(1)
  })

  it("disabled pendant download (aria-busy)", async () => {
    let resolve: (v?: unknown) => void = () => undefined
    globalThis.$fetch = vi.fn().mockImplementation(
      () => new Promise((r) => { resolve = r }),
    )
    const wrapper = mount(ExportButton)
    const btn = wrapper.find('[data-testid="export-button"]')
    void btn.trigger("click")
    await flushPromises()
    expect(btn.attributes("disabled")).toBeDefined()
    expect(btn.attributes("aria-busy")).toBe("true")
    resolve({})
    await flushPromises()
  })

  it("double-clic rapide → un seul fetch", async () => {
    globalThis.$fetch = vi.fn().mockResolvedValue({})
    const wrapper = mount(ExportButton)
    const btn = wrapper.find('[data-testid="export-button"]')
    await btn.trigger("click")
    await btn.trigger("click")
    await flushPromises()
    expect(globalThis.$fetch).toHaveBeenCalledTimes(1)
  })
})
