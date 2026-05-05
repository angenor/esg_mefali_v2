// F45 T072 — Tests ExportPlanButton.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { mount, flushPromises } from "@vue/test-utils"
import ExportPlanButton from "~/components/plan-action/ExportPlanButton.vue"

interface GlobalShape {
  useRuntimeConfig?: () => { public: { apiBase?: string; featurePlanExportPdf?: string } }
  $fetch?: <T>(u: string, o?: Record<string, unknown>) => Promise<T>
}
const g = globalThis as unknown as GlobalShape

beforeEach(() => {
  delete g.useRuntimeConfig
  delete g.$fetch
})
afterEach(() => {
  delete g.useRuntimeConfig
  delete g.$fetch
})

describe("ExportPlanButton", () => {
  it("flag off → bouton disabled + libellé Bientôt disponible", () => {
    g.useRuntimeConfig = () => ({
      public: { apiBase: "http://x", featurePlanExportPdf: "false" },
    })
    const w = mount(ExportPlanButton)
    const btn = w.find('[data-testid="pa-export-pdf"]')
    expect(btn.attributes("disabled")).toBeDefined()
    expect(btn.text().toLowerCase()).toContain("bientôt")
  })

  it("flag on → bouton actif déclenche $fetch et nomme le fichier plan-action-{date}.pdf", async () => {
    g.useRuntimeConfig = () => ({
      public: { apiBase: "http://x", featurePlanExportPdf: "true" },
    })
    const fakeBlob = new Blob(["pdf"], { type: "application/pdf" })
    const calls: { url: string; opts?: Record<string, unknown> }[] = []
    g.$fetch = (async (url: string, opts?: Record<string, unknown>) => {
      calls.push({ url, opts })
      return fakeBlob
    }) as GlobalShape["$fetch"]

    const createSpy = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:fake")
    const revokeSpy = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {})
    const clickSpy = vi.fn()
    const origCreate = document.createElement.bind(document)
    vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
      const el = origCreate(tag) as HTMLAnchorElement
      if (tag === "a") {
        el.click = clickSpy
      }
      return el
    })

    const w = mount(ExportPlanButton)
    const btn = w.find('[data-testid="pa-export-pdf"]')
    expect(btn.attributes("disabled")).toBeUndefined()
    await btn.trigger("click")
    await flushPromises()

    expect(calls).toHaveLength(1)
    expect(calls[0]!.url).toContain("/me/action-plan/export.pdf")
    expect(clickSpy).toHaveBeenCalled()

    createSpy.mockRestore()
    revokeSpy.mockRestore()
  })
})
