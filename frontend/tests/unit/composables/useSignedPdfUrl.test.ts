// F49 T060 — useSignedPdfUrl : invalidation à expires_at + re-fetch.

import { beforeEach, describe, expect, it, vi } from "vitest"
import { effectScope, ref } from "vue"
import { createPinia, setActivePinia } from "pinia"

const fetchMock = vi.fn()
;(globalThis as { $fetch?: unknown }).$fetch = fetchMock
;(globalThis as { useRuntimeConfig?: unknown }).useRuntimeConfig = () => ({
  public: { apiBase: "http://api" },
})

import { useSignedPdfUrl } from "../../../app/composables/useSignedPdfUrl"

describe("useSignedPdfUrl (F49 T060)", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    fetchMock.mockReset()
  })

  it("expose url tant que expires_at n'est pas atteinte, puis null", async () => {
    const future = new Date(Date.now() + 60_000).toISOString()
    fetchMock.mockResolvedValue({
      url: "https://signed.example/pdf?t=1",
      expires_at: future,
    })

    const scope = effectScope()
    const r = scope.run(() => useSignedPdfUrl(ref("rap-1")))!
    await r.refresh()
    // attendre la micro-tâche du watchEffect interne
    await Promise.resolve()
    await Promise.resolve()
    expect(r.url.value).toContain("signed.example/pdf")
    expect(r.isExpired.value).toBe(false)
    scope.stop()
  })

  it("force l'expiration → url devient null + refresh re-fetch", async () => {
    const past = new Date(Date.now() - 10_000).toISOString()
    fetchMock.mockResolvedValue({
      url: "https://signed.example/pdf?t=stale",
      expires_at: past,
    })
    const scope = effectScope()
    const r = scope.run(() => useSignedPdfUrl(ref("rap-2")))!
    await r.refresh()
    expect(r.isExpired.value).toBe(true)
    expect(r.url.value).toBeNull()

    const future = new Date(Date.now() + 60_000).toISOString()
    fetchMock.mockResolvedValueOnce({
      url: "https://signed.example/pdf?t=fresh",
      expires_at: future,
    })
    await r.refresh()
    expect(r.isExpired.value).toBe(false)
    expect(r.url.value).toContain("t=fresh")
    scope.stop()
  })
})
