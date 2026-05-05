// F50 T005/T024 — Service API documents (encapsule $fetch + apiBase + JWT/CSRF).
//
// Toutes les requêtes documents F50 passent par ce module ; pas de $fetch direct.
// Cf. specs/050-documents-ocr-ui/contracts/documents_api_extensions.md.

import type {
  DocumentDetail,
  DocumentListItem,
  FingerprintLookupOut,
  ValidateExtractionIn,
  ValidateExtractionOut,
} from "~/types/documents"

interface RuntimeConfigShape {
  public?: { apiBase?: string }
}

function apiBase(): string {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const g = globalThis as any
  const cfg =
    (g.useRuntimeConfig?.() as RuntimeConfigShape | undefined) ??
    (g.useNuxtApp?.()?.$config as RuntimeConfigShape | undefined)
  return String(cfg?.public?.apiBase ?? "").replace(/\/$/, "")
}

type FetchFn = <T>(u: string, o?: Record<string, unknown>) => Promise<T>

function fetcher(): FetchFn {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const f = (globalThis as any).$fetch as FetchFn | undefined
  if (!f) throw new Error("$fetch unavailable")
  return f
}

function csrfHeader(): Record<string, string> {
  if (typeof document === "undefined") return {}
  const m = document.cookie.match(/(?:^|;\s*)mefali_csrf=([^;]+)/)
  return m ? { "X-CSRF-Token": decodeURIComponent(m[1]!) } : {}
}

export interface UploadOpts {
  type: string
  name?: string
  clientSha256?: string | null
  linkProjetId?: string | null
  onProgress?: (percent: number) => void
  signal?: AbortSignal
}

export interface DocumentsApi {
  getByFingerprint(sha256: string): Promise<FingerprintLookupOut | null>
  uploadDocument(file: File, opts: UploadOpts): Promise<DocumentDetail>
  getDocument(id: string): Promise<DocumentDetail>
  listEntrepriseDocuments(): Promise<DocumentListItem[]>
  listProjetDocuments(projetId: string): Promise<DocumentListItem[]>
  validateExtraction(
    docId: string,
    payload: ValidateExtractionIn,
  ): Promise<ValidateExtractionOut>
  relaunchOcr(docId: string, invalidateValidation: boolean): Promise<void>
  linkProjet(docId: string, projetId: string): Promise<void>
  unlinkProjet(docId: string, projetId: string): Promise<void>
  softDelete(docId: string): Promise<void>
  updateTags(docId: string, tags: string[]): Promise<DocumentDetail>
}

function uploadXhr(
  url: string,
  formData: FormData,
  opts: UploadOpts,
): Promise<DocumentDetail> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open("POST", url, true)
    xhr.withCredentials = true
    const headers = csrfHeader()
    for (const [k, v] of Object.entries(headers)) {
      xhr.setRequestHeader(k, v)
    }
    xhr.upload.onprogress = (e) => {
      if (!e.lengthComputable) return
      const pct = Math.min(100, Math.round((e.loaded / e.total) * 100))
      opts.onProgress?.(pct)
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as DocumentDetail)
        } catch (e) {
          reject(e)
        }
      } else {
        let detail: unknown = null
        try {
          detail = JSON.parse(xhr.responseText)
        } catch {
          /* noop */
        }
        const err = new Error(`upload_failed_${xhr.status}`)
        ;(err as Error & { detail?: unknown; status?: number }).detail = detail
        ;(err as Error & { status?: number }).status = xhr.status
        reject(err)
      }
    }
    xhr.onerror = () => reject(new Error("network_error"))
    if (opts.signal) {
      opts.signal.addEventListener("abort", () => xhr.abort(), { once: true })
    }
    xhr.send(formData)
  })
}

export const documentsApi: DocumentsApi = {
  async getByFingerprint(sha256) {
    const url = `${apiBase()}/me/documents/by-fingerprint`
    try {
      return await fetcher()<FingerprintLookupOut>(url, {
        query: { sha256 },
        credentials: "include",
      })
    } catch (e) {
      const status = (e as { status?: number; statusCode?: number }).status
        ?? (e as { statusCode?: number }).statusCode
      if (status === 404) return null
      throw e
    }
  },

  uploadDocument(file, opts) {
    const fd = new FormData()
    fd.append("file", file)
    fd.append("type", opts.type)
    if (opts.name) fd.append("name", opts.name)
    if (opts.clientSha256) fd.append("client_sha256", opts.clientSha256)
    if (opts.linkProjetId) fd.append("link_projet_id", opts.linkProjetId)
    const url = `${apiBase()}/me/entreprise/documents`
    return uploadXhr(url, fd, opts)
  },

  getDocument(id) {
    const url = `${apiBase()}/me/entreprise/documents/${id}`
    return fetcher()<DocumentDetail>(url, { credentials: "include" })
  },

  listEntrepriseDocuments() {
    const url = `${apiBase()}/me/entreprise/documents`
    return fetcher()<{ items: DocumentListItem[] }>(url, {
      credentials: "include",
    }).then((r) => r.items)
  },

  listProjetDocuments(projetId) {
    const url = `${apiBase()}/me/projets/${projetId}/documents`
    return fetcher()<{ items: DocumentListItem[] }>(url, {
      credentials: "include",
    }).then((r) => r.items)
  },

  validateExtraction(docId, payload) {
    const url = `${apiBase()}/me/entreprise/documents/${docId}/validate`
    return fetcher()<ValidateExtractionOut>(url, {
      method: "POST",
      body: payload,
      credentials: "include",
      headers: csrfHeader(),
    })
  },

  relaunchOcr(docId, invalidateValidation) {
    const url = `${apiBase()}/me/entreprise/documents/${docId}/relaunch-ocr`
    return fetcher()<void>(url, {
      method: "POST",
      body: { invalidate_existing_validation: invalidateValidation },
      credentials: "include",
      headers: csrfHeader(),
    })
  },

  linkProjet(docId, projetId) {
    const url = `${apiBase()}/me/entreprise/documents/${docId}/link-projet`
    return fetcher()<void>(url, {
      method: "POST",
      body: { projet_id: projetId },
      credentials: "include",
      headers: csrfHeader(),
    })
  },

  unlinkProjet(docId, projetId) {
    const url = `${apiBase()}/me/entreprise/documents/${docId}/link-projet/${projetId}`
    return fetcher()<void>(url, {
      method: "DELETE",
      credentials: "include",
      headers: csrfHeader(),
    })
  },

  softDelete(docId) {
    const url = `${apiBase()}/me/entreprise/documents/${docId}`
    return fetcher()<void>(url, {
      method: "DELETE",
      credentials: "include",
      headers: csrfHeader(),
    })
  },

  updateTags(docId, tags) {
    const url = `${apiBase()}/me/entreprise/documents/${docId}/tags`
    return fetcher()<DocumentDetail>(url, {
      method: "PATCH",
      body: { tags },
      credentials: "include",
      headers: csrfHeader(),
    })
  },
}
