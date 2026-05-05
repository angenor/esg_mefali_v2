// F52 US4 — Tests Vitest du client REST sidepanel.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import {
  ApiError,
  fetchExtensionStatus,
  fetchSidepanelContext,
  postPing,
} from "../lib/api"

describe("sidepanel/lib/api", () => {
  const fetchMock = vi.fn()
  beforeEach(() => {
    fetchMock.mockReset()
    globalThis.fetch = fetchMock as unknown as typeof fetch
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("fetchSidepanelContext appelle /me/extension/sidepanel-context avec credentials", async () => {
    const payload = {
      matched_offer_ids: [],
      active_candidatures: [],
      recommended_offers: [],
    }
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    )
    const out = await fetchSidepanelContext("boad.org", "/x")
    expect(out).toEqual(payload)
    const callArgs = fetchMock.mock.calls[0]
    expect(callArgs[0]).toContain("/me/extension/sidepanel-context")
    expect(callArgs[1]).toMatchObject({ credentials: "include", method: "GET" })
  })

  it("fetchSidepanelContext jette ApiError sur 401", async () => {
    fetchMock.mockResolvedValue(new Response("", { status: 401 }))
    await expect(fetchSidepanelContext("x", "/")).rejects.toBeInstanceOf(
      ApiError
    )
  })

  it("fetchExtensionStatus retourne le payload détecté", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          detected: true,
          extension_version: "0.4.2",
          last_ping_at: "2026-05-05T12:00:00Z",
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }
      )
    )
    const out = await fetchExtensionStatus()
    expect(out.detected).toBe(true)
    expect(out.extension_version).toBe("0.4.2")
  })

  it("postPing envoie un body JSON et retourne null sur 204", async () => {
    fetchMock.mockResolvedValue(new Response("", { status: 204 }))
    await expect(
      postPing({ extension_version: "1.0.0", user_agent_summary: "Chrome" })
    ).resolves.toBeUndefined()
    const init = fetchMock.mock.calls[0][1] as RequestInit
    expect(init.method).toBe("POST")
    expect(init.credentials).toBe("include")
    expect(typeof init.body).toBe("string")
    expect(JSON.parse(init.body as string)).toMatchObject({
      extension_version: "1.0.0",
    })
  })
})
