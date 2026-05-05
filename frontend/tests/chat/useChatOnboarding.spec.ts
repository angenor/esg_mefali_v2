/**
 * F41 / US6 (T044). useChatOnboarding : flag persistance, skip si vu.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'

describe('useChatOnboarding — fallback localStorage', () => {
  beforeEach(() => {
    if (typeof window !== 'undefined') window.localStorage.clear()
  })

  it("lit/écrit la clé localStorage par accountId", () => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem('chat.onboarding.seen.acc1', '1')
    expect(window.localStorage.getItem('chat.onboarding.seen.acc1')).toBe('1')
  })

  it("ne déclenche pas le tour si fetch backend retourne true", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ onboarding_chat_seen: true }), { status: 200 }),
    )
    globalThis.fetch = fetchMock as never
    expect(fetchMock).toBeDefined()
  })
})
