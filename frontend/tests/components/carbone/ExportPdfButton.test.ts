// F47 T088 [US9] — Tests ExportPdfButton.
import { describe, expect, it, vi } from "vitest"
import { mount } from "@vue/test-utils"
import ExportPdfButton from "~/components/carbone/ExportPdfButton.vue"

vi.mock("~/composables/useT", () => ({
  useT: () => ({ t: (k: string) => k }),
}))

vi.mock("~/composables/useReducedMotion", () => ({
  useReducedMotion: () => ({ value: true }),
}))

vi.mock("~/composables/useFocusTrap", () => ({
  useFocusTrap: () => ({ activate: () => {}, deactivate: () => {} }),
}))

describe("ExportPdfButton", () => {
  it("(a) bouton rendu avec libellé i18n", () => {
    const w = mount(ExportPdfButton, { props: { year: 2026 } })
    expect(w.text()).toContain("carbon.export.button")
  })

  it("(b) clic ouvre la modale placeholder quand ready=false", async () => {
    const w = mount(ExportPdfButton, {
      props: { year: 2026, ready: false },
      attachTo: document.body,
    })
    await w.find("button").trigger("click")
    // Modal teleportée dans body
    const modalText = document.body.textContent ?? ""
    expect(modalText).toContain("carbon.export.placeholderTitle")
    expect(modalText).toContain("carbon.export.placeholderDescription")
    w.unmount()
  })

  it("(c) ready=true → pas de modale au clic (délégation F51)", async () => {
    const w = mount(ExportPdfButton, {
      props: { year: 2026, ready: true },
      attachTo: document.body,
    })
    await w.find("button").trigger("click")
    const modalText = document.body.textContent ?? ""
    expect(modalText).not.toContain("carbon.export.placeholderTitle")
    w.unmount()
  })
})
