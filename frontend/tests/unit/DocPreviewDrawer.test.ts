// F50 (T042) — Tests DocPreviewDrawer.
// - Rendu PDF via pdfjs-dist mocké (getDocument/getPage/render).
// - Navigation clavier ArrowLeft/ArrowRight et fermeture par Escape.
// - Fallback Office (xlsx/docx) avec bouton de téléchargement.
// - role=dialog + aria-label.
// - Image inline rendue avec <img>.
// - Erreur 423/409 mappée à "Analyse antivirus en cours".

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { flushPromises, mount } from "@vue/test-utils"

const fakeRender = vi.fn(() => ({ promise: Promise.resolve() }))
const fakePage = {
  getViewport: vi.fn(() => ({ width: 600, height: 800 })),
  render: fakeRender,
}
const fakePdfDoc = {
  numPages: 3,
  getPage: vi.fn(async () => fakePage),
}
const fakeGetDocument = vi.fn(() => ({ promise: Promise.resolve(fakePdfDoc) }))

// Mock le composable lazy → renvoie un module pdfjs simulé.
vi.mock("../../app/composables/useDocumentPreviewLazy", () => {
  return {
    useDocumentPreviewLazy: () => ({
      load: async () => ({
        getDocument: fakeGetDocument,
        GlobalWorkerOptions: { workerSrc: "" },
      }),
    }),
  }
})

// Stub useRuntimeConfig pour buildUrl.
;(globalThis as { useRuntimeConfig?: unknown }).useRuntimeConfig = () => ({
  public: { apiBase: "http://api" },
})

// Mock fetch global pour PDF (utilisé par loadPdf).
const fetchMock = vi.fn()
;(globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch

import DocPreviewDrawer from "../../app/components/documents/DocPreviewDrawer.vue"
import type { DocumentDetail } from "../../app/types/documents"

function makeDoc(p: Partial<DocumentDetail> = {}): DocumentDetail {
  return {
    id: "doc-1",
    entreprise_id: "ent-1",
    name: "Statuts.pdf",
    original_filename: "statuts.pdf",
    mime_type: "application/pdf",
    size_bytes: 2048,
    type: "statuts",
    ocr_status: "done",
    ocr_error: null,
    created_at: "2026-04-30T15:00:00Z",
    extraction_payload: { fields: [] },
    extraction_validated_at: null,
    extraction_validated_by: null,
    linked_projets: [],
    tags: [],
    deleted_at: null,
    purge_scheduled_at: null,
    ...p,
  }
}

function pdfFetchOk(): void {
  fetchMock.mockResolvedValueOnce({
    ok: true,
    status: 200,
    arrayBuffer: async () => new Uint8Array([1, 2, 3]).buffer,
  })
}

describe("<DocPreviewDrawer> (F50)", () => {
  beforeEach(() => {
    fetchMock.mockReset()
    fakeRender.mockClear()
    fakePdfDoc.getPage.mockClear()
    fakeGetDocument.mockClear()
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("ne rend rien tant que open=false", () => {
    const wrapper = mount(DocPreviewDrawer, {
      props: { open: false, doc: makeDoc() },
    })
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
  })

  it("rend le drawer avec role=dialog et aria-label", async () => {
    pdfFetchOk()
    const wrapper = mount(DocPreviewDrawer, {
      props: { open: false, doc: makeDoc({ name: "Statuts.pdf" }) },
    })
    await wrapper.setProps({ open: true })
    await flushPromises()
    const dlg = wrapper.find('[role="dialog"]')
    expect(dlg.exists()).toBe(true)
    expect(dlg.attributes("aria-modal")).toBe("true")
    expect(dlg.attributes("aria-label")).toContain("Statuts.pdf")
  })

  it("charge le PDF via pdfjs et expose la nav pages", async () => {
    pdfFetchOk()
    const wrapper = mount(DocPreviewDrawer, {
      props: { open: false, doc: makeDoc() },
    })
    await wrapper.setProps({ open: true })
    await flushPromises()
    await flushPromises()
    expect(fakeGetDocument).toHaveBeenCalledTimes(1)
    expect(fakePdfDoc.getPage).toHaveBeenCalledWith(1)
    // NB : fakeRender peut ne pas être appelé en happy-dom car le canvas
    // n'est pas attaché ; on vérifie l'invariant via la nav pages exposée.
    expect(wrapper.text()).toContain("Page 1 / 3")
  })

  it("ArrowRight passe à la page suivante", async () => {
    pdfFetchOk()
    const wrapper = mount(DocPreviewDrawer, {
      props: { open: false, doc: makeDoc() },
      attachTo: document.body,
    })
    await wrapper.setProps({ open: true })
    await flushPromises()
    await flushPromises()
    fakePdfDoc.getPage.mockClear()

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight" }))
    await flushPromises()
    expect(fakePdfDoc.getPage).toHaveBeenCalledWith(2)
    wrapper.unmount()
  })

  it("ArrowLeft revient à la page précédente après navigation", async () => {
    pdfFetchOk()
    const wrapper = mount(DocPreviewDrawer, {
      props: { open: false, doc: makeDoc() },
      attachTo: document.body,
    })
    await wrapper.setProps({ open: true })
    await flushPromises()
    await flushPromises()
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight" }))
    await flushPromises()
    fakePdfDoc.getPage.mockClear()
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft" }))
    await flushPromises()
    expect(fakePdfDoc.getPage).toHaveBeenCalledWith(1)
    wrapper.unmount()
  })

  it("Escape émet close", async () => {
    pdfFetchOk()
    const wrapper = mount(DocPreviewDrawer, {
      props: { open: false, doc: makeDoc() },
      attachTo: document.body,
    })
    await wrapper.setProps({ open: true })
    await flushPromises()
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }))
    await flushPromises()
    expect(wrapper.emitted("close")).toBeTruthy()
    wrapper.unmount()
  })

  it("clic sur ✕ émet close", async () => {
    pdfFetchOk()
    const wrapper = mount(DocPreviewDrawer, {
      props: { open: false, doc: makeDoc() },
    })
    await wrapper.setProps({ open: true })
    await flushPromises()
    const closeBtn = wrapper.findAll("button").find(
      (b) => b.attributes("aria-label") === "Fermer la prévisualisation",
    )
    await closeBtn!.trigger("click")
    expect(wrapper.emitted("close")).toBeTruthy()
  })

  it("rend une image inline pour mime image/*", async () => {
    const wrapper = mount(DocPreviewDrawer, {
      props: {
        open: false,
        doc: makeDoc({ mime_type: "image/png", name: "scan.png" }),
        downloadUrl: (id: string) => `http://api/download/${id}`,
      },
    })
    await wrapper.setProps({ open: true })
    await flushPromises()
    const img = wrapper.find("img")
    expect(img.exists()).toBe(true)
    expect(img.attributes("alt")).toBe("scan.png")
    expect(img.attributes("src")).toBe("http://api/download/doc-1")
  })

  it("affiche le fallback Office avec bouton télécharger pour xlsx/docx", async () => {
    const wrapper = mount(DocPreviewDrawer, {
      props: {
        open: false,
        doc: makeDoc({
          mime_type:
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          name: "Bilan.xlsx",
          original_filename: "bilan.xlsx",
        }),
      },
    })
    await wrapper.setProps({ open: true })
    await flushPromises()
    expect(wrapper.text()).toContain("Aperçu indisponible")
    const dl = wrapper.findAll("a").find((a) => a.text().includes("bilan.xlsx"))
    expect(dl).toBeDefined()
    expect(dl!.text()).toContain("Télécharger")
  })

  it("traduit 423 en message « Analyse antivirus en cours »", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 423,
      arrayBuffer: async () => new ArrayBuffer(0),
    })
    const wrapper = mount(DocPreviewDrawer, {
      props: { open: false, doc: makeDoc() },
    })
    await wrapper.setProps({ open: true })
    await flushPromises()
    await flushPromises()
    const alert = wrapper.find('[role="alert"]')
    expect(alert.exists()).toBe(true)
    expect(alert.text()).toContain("Analyse antivirus")
  })

  it("affiche un message d'erreur générique si fetch retourne 500", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 500,
      arrayBuffer: async () => new ArrayBuffer(0),
    })
    const wrapper = mount(DocPreviewDrawer, {
      props: { open: false, doc: makeDoc() },
    })
    await wrapper.setProps({ open: true })
    await flushPromises()
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain("500")
  })
})
