// F49 T040 — Tests composant RevokeAttestationModal.

import { beforeEach, describe, expect, it, vi } from "vitest"
import { mount, flushPromises } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"

const fetchMock = vi.fn()
;(globalThis as { $fetch?: unknown }).$fetch = fetchMock
;(globalThis as { useRuntimeConfig?: unknown }).useRuntimeConfig = () => ({
  public: { apiBase: "http://api", appUrl: "https://app.example.com" },
})

import RevokeAttestationModal from "../../app/components/rapports/RevokeAttestationModal.vue"

const fakeAttestation = {
  id: "att-1",
  public_id: "pub-1",
  type: "conformite_esg" as const,
  status: "active" as const,
  issued_at: "2026-04-01T00:00:00Z",
  expires_at: "2027-04-01T00:00:00Z",
  revoked_at: null,
  revoke_reason: null,
  verify_url: "https://app.example.com/verify/pub-1",
}

const revokedRow = {
  id: "att-1",
  public_id: "pub-1",
  status: "revoked" as const,
  generated_at: "2026-04-01T00:00:00Z",
  valid_until: "2027-04-01T00:00:00Z",
  revoked_at: "2026-05-04T00:00:00Z",
  scores_inclus: {},
  referentiels_versions: {},
  signature_ed25519: "sig",
  pubkey_fingerprint: "fp",
  hash_document: "hash",
  download_url: "https://app.example.com/x",
  verify_url: "https://app.example.com/verify/pub-1",
}

describe("<RevokeAttestationModal>", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    fetchMock.mockReset()
  })

  function $(sel: string): HTMLElement | null {
    return document.body.querySelector(sel) as HTMLElement | null
  }

  it("le bouton de confirmation est désactivé tant qu'aucun motif n'est choisi", async () => {
    mount(RevokeAttestationModal, {
      props: { open: true, attestation: fakeAttestation },
    })
    await flushPromises()
    const btn = $('[data-testid="confirm-revoke"]') as HTMLButtonElement | null
    expect(btn?.disabled).toBe(true)
  })

  it("appelle l'API quand un motif est choisi et confirme", async () => {
    fetchMock.mockResolvedValueOnce(revokedRow)
    const wrapper = mount(RevokeAttestationModal, {
      props: { open: true, attestation: fakeAttestation },
    })
    await flushPromises()
    const radio = $(
      '[data-testid="reason-erreur_emission"]',
    ) as HTMLInputElement | null
    if (radio) {
      radio.checked = true
      radio.dispatchEvent(new Event("change", { bubbles: true }))
    }
    await wrapper.vm.$nextTick()
    const btn = $('[data-testid="confirm-revoke"]') as HTMLButtonElement | null
    btn?.click()
    await flushPromises()
    expect(fetchMock).toHaveBeenCalled()
    const [url, opts] = fetchMock.mock.calls[0]!
    expect(String(url)).toContain("/me/attestations/att-1/revoke")
    expect(
      (opts as { body?: { reason?: string } } | undefined)?.body?.reason,
    ).toBe("erreur_emission")
  })
})
