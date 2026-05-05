// F50 T045 — Lazy-load pdfjs-dist (chunk async, worker via ?worker).
//
// Évite d'embarquer pdfjs (~700 ko) dans le bundle initial.
// Cf. specs/050-documents-ocr-ui/contracts/documents_ui_contracts.md §6.

interface PdfPage {
  getViewport: (opts: { scale: number }) => { width: number; height: number }
  render: (ctx: { canvasContext: CanvasRenderingContext2D; viewport: unknown }) => {
    promise: Promise<void>
  }
}

export interface PdfDocument {
  numPages: number
  getPage: (n: number) => Promise<PdfPage>
}

export interface PdfjsModule {
  getDocument: (src: { data: Uint8Array | ArrayBuffer } | string) => {
    promise: Promise<PdfDocument>
  }
  GlobalWorkerOptions: { workerSrc: string }
}

let cached: Promise<PdfjsModule> | null = null

export function useDocumentPreviewLazy(): {
  load: () => Promise<PdfjsModule>
} {
  function load(): Promise<PdfjsModule> {
    if (cached) return cached
    cached = (async () => {
      // Import dynamique : pdfjs-dist est code-splitté.
      const mod = (await import("pdfjs-dist")) as unknown as PdfjsModule & {
        version?: string
      }
      // Worker: utilise le worker bundlé par Vite (?worker&url retourne une URL).
      try {
        const workerUrl = (await import("pdfjs-dist/build/pdf.worker.min.mjs?url")) as {
          default: string
        }
        mod.GlobalWorkerOptions.workerSrc = workerUrl.default
      } catch {
        // Fallback : laisse pdfjs charger via CDN par défaut (NOOP).
      }
      return mod
    })()
    return cached
  }
  return { load }
}
