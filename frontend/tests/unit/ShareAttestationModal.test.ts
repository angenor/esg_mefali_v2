// F49 T039 — Tests composant ShareAttestationModal.

import { beforeEach, describe, expect, it, vi } from "vitest"
import { mount, flushPromises } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"

const fetchMock = vi.fn()
;(globalThis as { $fetch?: unknown }).$fetch = fetchMock
;(globalThis as { useRuntimeConfig?: unknown }).useRuntimeConfig = () => ({
  public: { apiBase: "http://api", appUrl: "https://app.example.com" },
})

vi.mock("qrcode", () => ({
  default: {
    toDataURL: vi.fn(async () => "data:image/png;base64,FAKE"),
  },
  toDataURL: vi.fn(async () => "data:image/png;base64,FAKE"),
}))

const writeTextMock = vi.fn(async () => undefined)
Object.defineProperty(globalThis, "navigator", {
  value: { clipboard: { writeText: writeTextMock } },
  configurable: true,
})

// Stub URL.createObjectURL utilisé dans la modale pour le bouton de téléchargement.
;(globalThis as unknown as { URL: typeof URL }).URL.createObjectURL =
  vi.fn(() => "blob:fake")
;(globalThis as unknown as { URL: typeof URL }).URL.revokeObjectURL = vi.fn()

// `qrcode` est aussi importé via le store. fetch(dataUrl) -> Blob.
const fakeFetch = vi.fn(async () => ({
  blob: async () => new Blob(["x"], { type: "image/png" }),
})) as unknown as typeof fetch
;(globalThis as unknown as { fetch: typeof fetch }).fetch = fakeFetch

import ShareAttestationModal from "../../app/components/rapports/ShareAttestationModal.vue"

const fakeAttestation = {
  id: "id-1",
  public_id: "pub-1234567890",
  type: "conformite_esg" as const,
  status: "active" as const,
  issued_at: "2026-04-01T00:00:00Z",
  expires_at: "2027-04-01T00:00:00Z",
  revoked_at: null,
  revoke_reason: null,
  verify_url: "https://app.example.com/verify/pub-1234567890",
}

describe("<ShareAttestationModal>", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    writeTextMock.mockClear()
  })

  function $(sel: string): HTMLElement | null {
    return document.body.querySelector(sel) as HTMLElement | null
  }

  it("ne s'affiche pas si open=false", () => {
    mount(ShareAttestationModal, {
      props: { open: false, attestation: fakeAttestation },
    })
    expect($('[data-testid="share-modal"]')).toBeNull()
  })

  it("affiche l'URL publique correcte", async () => {
    mount(ShareAttestationModal, {
      props: { open: true, attestation: fakeAttestation },
    })
    await flushPromises()
    const input = $('[data-testid="share-url"]') as HTMLInputElement | null
    expect(input).not.toBeNull()
    expect(input?.value).toContain("/verify/pub-1234567890")
  })

  it("génère le QR PNG", async () => {
    mount(ShareAttestationModal, {
      props: { open: true, attestation: fakeAttestation },
    })
    await flushPromises()
    await flushPromises()
    expect($('[data-testid="qr-image"]')).not.toBeNull()
  })

  it("le bouton copier appelle navigator.clipboard", async () => {
    mount(ShareAttestationModal, {
      props: { open: true, attestation: fakeAttestation },
    })
    await flushPromises()
    const btn = $('[data-testid="copy-btn"]') as HTMLButtonElement | null
    btn?.click()
    await flushPromises()
    expect(writeTextMock).toHaveBeenCalledWith(
      expect.stringContaining("/verify/pub-1234567890"),
    )
  })
})
