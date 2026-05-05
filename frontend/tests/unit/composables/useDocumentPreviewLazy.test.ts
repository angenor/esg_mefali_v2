// F50 (T045) — Tests useDocumentPreviewLazy.
//
// pdfjs-dist n'est pas physiquement installé en environnement de test (chunk
// async + 700 ko, hors scope unit). On stubbe le composable via un mock
// remappant l'import dynamique vers un module en mémoire.

import { describe, expect, it, vi } from "vitest"

// Stub via ``vi.mock`` virtuel. Vitest gère les modules virtuels pour les
// imports dynamiques quand on déclare la factory.
vi.mock("pdfjs-dist", () => ({
  getDocument: vi.fn(() => ({ promise: Promise.resolve({ numPages: 0 }) })),
  GlobalWorkerOptions: { workerSrc: "" },
}))
vi.mock("pdfjs-dist/build/pdf.worker.min.mjs?url", () => ({
  default: "/_worker/pdf.worker.mjs",
}))

describe("useDocumentPreviewLazy (F50)", () => {
  it("load() retourne un module pdfjs avec workerSrc configuré", async () => {
    const { useDocumentPreviewLazy } = await import(
      "../../../app/composables/useDocumentPreviewLazy"
    )
    const { load } = useDocumentPreviewLazy()
    const mod = await load()
    expect(mod).toBeDefined()
    expect(typeof mod.getDocument).toBe("function")
    expect(mod.GlobalWorkerOptions.workerSrc).toBe("/_worker/pdf.worker.mjs")
  })

  it("met en cache la promise (deuxième appel = même résultat)", async () => {
    const { useDocumentPreviewLazy } = await import(
      "../../../app/composables/useDocumentPreviewLazy"
    )
    const { load } = useDocumentPreviewLazy()
    const a = await load()
    const b = await load()
    expect(a).toBe(b)
  })
})
