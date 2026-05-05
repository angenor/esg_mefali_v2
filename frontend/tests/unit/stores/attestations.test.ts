// F49 T021 — Tests Pinia useAttestationsStore.

import { beforeEach, describe, expect, it, vi } from "vitest"
import { createPinia, setActivePinia } from "pinia"

const fetchMock = vi.fn()
;(globalThis as { $fetch?: unknown }).$fetch = fetchMock
;(globalThis as { useRuntimeConfig?: unknown }).useRuntimeConfig = () => ({
  public: { apiBase: "http://api", appUrl: "https://app.example.com" },
})

import { useAttestationsStore } from "../../../app/stores/attestations"

const fakeAttestation = {
  id: "11111111-1111-1111-1111-111111111111",
  public_id: "22222222-2222-2222-2222-222222222222",
  status: "active" as const,
  generated_at: "2026-04-01T00:00:00Z",
  valid_until: "2027-04-01T00:00:00Z",
  revoked_at: null,
  scores_inclus: {},
  referentiels_versions: {},
  signature_ed25519: "sig",
  pubkey_fingerprint: "fp",
  hash_document: "hash",
  download_url: "https://app.example.com/me/attestations/.../download",
  verify_url: "https://app.example.com/verify/...",
}

describe("useAttestationsStore (F49)", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    fetchMock.mockReset()
  })

  it("fetchAll peuple la liste", async () => {
    fetchMock.mockResolvedValueOnce([fakeAttestation])
    const s = useAttestationsStore()
    await s.fetchAll()
    expect(s.attestations).toHaveLength(1)
    expect(s.attestations[0].public_id).toBe(fakeAttestation.public_id)
    expect(s.attestations[0].status).toBe("active")
  })

  it("revoke met à jour le statut en local", async () => {
    fetchMock.mockResolvedValueOnce([fakeAttestation])
    const s = useAttestationsStore()
    await s.fetchAll()
    fetchMock.mockResolvedValueOnce({
      ...fakeAttestation,
      status: "revoked",
      revoked_at: "2026-05-04T00:00:00Z",
    })
    await s.revoke(fakeAttestation.id, "erreur_emission")
    expect(s.attestations[0].status).toBe("revoked")
    expect(s.attestations[0].revoke_reason).toBe("erreur_emission")
  })

  it("buildVerifyUrl construit l'URL absolue", () => {
    const s = useAttestationsStore()
    expect(s.buildVerifyUrl("abc")).toBe("https://app.example.com/verify/abc")
  })

  it("buildQrPng retourne un Blob non vide", async () => {
    const s = useAttestationsStore()
    const blob = await s.buildQrPng("abc")
    expect(blob).toBeInstanceOf(Blob)
    expect(blob.size).toBeGreaterThan(0)
  })
})
