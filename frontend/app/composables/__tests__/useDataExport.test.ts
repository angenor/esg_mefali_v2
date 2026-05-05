// F44 T012 — Tests vitest useDataExport (anti double-clic + nom fichier).
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { mount } from "@vue/test-utils"
import { useDataExport } from "../useDataExport"

declare global {
  // eslint-disable-next-line no-var
  var $fetch: unknown
  // eslint-disable-next-line no-var
  var useRuntimeConfig: unknown
}

interface Harness {
  isDownloading: boolean
  download: () => Promise<void>
}

function mountHarness(): { exposed: Harness; unmount: () => void } {
  const Comp = defineComponent({
    setup(_, { expose }) {
      const api = useDataExport()
      expose({ get isDownloading() { return api.isDownloading.value }, download: api.download })
      return () => h("div")
    },
  })
  const wrapper = mount(Comp)
  return { exposed: wrapper.vm as unknown as Harness, unmount: () => wrapper.unmount() }
}

describe("useDataExport", () => {
  let clickSpy: ReturnType<typeof vi.fn>

  beforeEach(() => {
    setActivePinia()
    globalThis.useRuntimeConfig = () => ({ public: { apiBase: "http://api" } })
    // Stub URL.createObjectURL / revokeObjectURL.
    // @ts-expect-error happy-dom doesn't provide it.
    global.URL.createObjectURL = vi.fn(() => "blob:fake")
    // @ts-expect-error happy-dom doesn't provide it.
    global.URL.revokeObjectURL = vi.fn()
    // Spy sur a.click.
    clickSpy = vi.fn()
    const origCreate = document.createElement.bind(document)
    vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
      const el = origCreate(tag) as HTMLElement
      if (tag === "a") {
        Object.defineProperty(el, "click", { value: clickSpy, configurable: true })
      }
      return el as never
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it("download() déclenche un seul download et nomme le fichier 'esg-mefali-export-YYYY-MM-DD.json'", async () => {
    globalThis.$fetch = vi.fn().mockResolvedValue({ entreprise: {}, candidatures: [] })
    const { exposed, unmount } = mountHarness()
    await exposed.download()
    expect(clickSpy).toHaveBeenCalledTimes(1)
    expect(globalThis.$fetch).toHaveBeenCalledTimes(1)
    unmount()
  })

  it("double-clic rapide → un seul download", async () => {
    globalThis.$fetch = vi.fn().mockResolvedValue({})
    const { exposed, unmount } = mountHarness()
    const p1 = exposed.download()
    const p2 = exposed.download()
    await Promise.all([p1, p2])
    expect(clickSpy).toHaveBeenCalledTimes(1)
    unmount()
  })

  it("erreur 5xx → pas de crash, isDownloading revient à true (cooldown) puis false", async () => {
    vi.useFakeTimers()
    globalThis.$fetch = vi.fn().mockRejectedValue(new Error("server error"))
    const { exposed, unmount } = mountHarness()
    await exposed.download()
    // Cooldown actif immédiatement après échec.
    expect(exposed.isDownloading).toBe(true)
    vi.advanceTimersByTime(2100)
    expect(exposed.isDownloading).toBe(false)
    unmount()
  })
})

// Helper minimal pour activer Pinia (utilisé par useToast indirectement si besoin).
import { setActivePinia as _set, createPinia } from "pinia"
function setActivePinia(): void {
  _set(createPinia())
}
