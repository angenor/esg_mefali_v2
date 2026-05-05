// F52 US4 — Tests du wrapper chrome.runtime.sendMessage.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { onIncoming, sendToBackground } from "../lib/messaging"

interface ChromeStub {
  runtime: {
    sendMessage: ReturnType<typeof vi.fn>
    onMessage: {
      addListener: ReturnType<typeof vi.fn>
      removeListener: ReturnType<typeof vi.fn>
    }
  }
}

describe("sidepanel/lib/messaging", () => {
  let chromeStub: ChromeStub

  beforeEach(() => {
    chromeStub = {
      runtime: {
        sendMessage: vi.fn().mockResolvedValue({ ok: true }),
        onMessage: {
          addListener: vi.fn(),
          removeListener: vi.fn(),
        },
      },
    }
    ;(globalThis as unknown as { chrome: ChromeStub }).chrome = chromeStub
  })

  afterEach(() => {
    delete (globalThis as unknown as { chrome?: unknown }).chrome
    vi.restoreAllMocks()
  })

  it("sendToBackground envoie le message via chrome.runtime", async () => {
    const result = await sendToBackground({
      type: "OPEN_CANDIDATURE",
      payload: { id: "abc" },
    })
    expect(result).toEqual({ ok: true })
    expect(chromeStub.runtime.sendMessage).toHaveBeenCalledWith({
      type: "OPEN_CANDIDATURE",
      payload: { id: "abc" },
    })
  })

  it("onIncoming ne déclenche que les types attendus", () => {
    const handler = vi.fn()
    onIncoming(handler)
    const cb = chromeStub.runtime.onMessage.addListener.mock.calls[0][0]
    cb(
      {
        type: "CONTEXT_READY",
        payload: {
          matched_offer_ids: [],
          active_candidatures: [],
          recommended_offers: [],
        },
      },
      undefined,
      () => undefined
    )
    cb({ type: "UNKNOWN" }, undefined, () => undefined)
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it("onIncoming retourne un cleanup qui retire le listener", () => {
    const cleanup = onIncoming(vi.fn())
    cleanup()
    expect(chromeStub.runtime.onMessage.removeListener).toHaveBeenCalled()
  })
})
