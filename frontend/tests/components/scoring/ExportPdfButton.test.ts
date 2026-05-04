// F46 T092 [US9] — Tests ExportPdfButton.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import ExportPdfButton from "~/components/scoring/ExportPdfButton.vue"
import { useScoringStore } from "~/stores/scoring"
import { scoringApi } from "~/services/api/scoring"

vi.mock("~/composables/useToast", () => ({
  useToast: () => ({ push: vi.fn() }),
}))

declare global {
  // eslint-disable-next-line no-var
  var useRuntimeConfig: unknown
}

describe("ExportPdfButton", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    const store = useScoringStore()
    store.setEntity("entreprise", "ent-1")
  })
  afterEach(() => {
    delete (globalThis as Record<string, unknown>).useRuntimeConfig
    vi.restoreAllMocks()
  })

  it("(a) flag off → bouton disabled + tooltip Disponible bientôt", () => {
    globalThis.useRuntimeConfig = () => ({
      public: { featureFlags: { f51_pdf_export: false } },
    })
    const w = mount(ExportPdfButton, { props: { referentielCode: "BOAD" } })
    const btn = w.find('[data-testid="export-pdf-button"]')
      .element as HTMLButtonElement
    expect(btn.disabled).toBe(true)
    expect(btn.title).toContain("Disponible bientôt")
  })

  it("(b) flag on → clic appelle scoringApi.exportPdf avec payload", async () => {
    globalThis.useRuntimeConfig = () => ({
      public: { featureFlags: { f51_pdf_export: true } },
    })
    const exportSpy = vi
      .spyOn(scoringApi, "exportPdf")
      .mockResolvedValue(new Blob(["%PDF-1.4"], { type: "application/pdf" }))
    const w = mount(ExportPdfButton, { props: { referentielCode: "BOAD" } })
    await w.find('[data-testid="export-pdf-button"]').trigger("click")
    await new Promise((r) => setTimeout(r, 0))
    expect(exportSpy).toHaveBeenCalledWith({
      entity_type: "entreprise",
      entity_id: "ent-1",
      referentiel_code: "BOAD",
      score_calculation_id: null,
    })
  })

  it("(c) snapshot actif → payload inclut score_calculation_id", async () => {
    globalThis.useRuntimeConfig = () => ({
      public: { featureFlags: { f51_pdf_export: true } },
    })
    const exportSpy = vi
      .spyOn(scoringApi, "exportPdf")
      .mockResolvedValue(new Blob(["%PDF-1.4"], { type: "application/pdf" }))
    const w = mount(ExportPdfButton, {
      props: { referentielCode: "BOAD", frozenCalculationId: "calc-42" },
    })
    await w.find('[data-testid="export-pdf-button"]').trigger("click")
    await new Promise((r) => setTimeout(r, 0))
    expect(exportSpy.mock.calls[0]![0].score_calculation_id).toBe("calc-42")
  })
})
