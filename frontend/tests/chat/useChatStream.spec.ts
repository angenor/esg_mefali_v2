/**
 * F41 / US1 (T024). useChatStream : SSE simulé, dedup, reconnect, abort.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useChatStream } from '~/composables/useChatStream'
import type { StreamFrame } from '~/types/chat'

function makeSseStream(frames: string[]): ReadableStream<Uint8Array> {
  const enc = new TextEncoder()
  return new ReadableStream({
    start(controller) {
      for (const f of frames) controller.enqueue(enc.encode(f))
      controller.close()
    },
  })
}

function frame(event: string, data: unknown, id?: number): string {
  const lines = [`event: ${event}`]
  if (id !== undefined) lines.push(`id: ${id}`)
  lines.push(`data: ${JSON.stringify(data)}`)
  lines.push('', '')
  return lines.join('\n')
}

describe('useChatStream', () => {
  let originalFetch: typeof fetch

  beforeEach(() => {
    originalFetch = globalThis.fetch
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
  })

  it('parse les frames token séquentielles', async () => {
    const stream = makeSseStream([
      frame('token', { content: 'Bon' }, 1),
      frame('token', { content: 'jour' }, 2),
      frame('message_done', { messageId: 'm1', content: 'Bonjour' }, 3),
    ])
    globalThis.fetch = vi.fn().mockResolvedValue(new Response(stream, { status: 200 })) as never

    const received: StreamFrame[] = []
    const ctrl = useChatStream(
      { apiBase: 'http://x', threadId: 't1', body: { content: 'hi' } },
      { onFrame: (f) => received.push(f) },
    )
    await ctrl.start()

    expect(received.map((r) => r.event)).toEqual(['token', 'token', 'message_done'])
  })

  it('déduplique par sequence_id', async () => {
    const stream = makeSseStream([
      frame('token', { content: 'A' }, 1),
      frame('token', { content: 'A' }, 1), // doublon
      frame('token', { content: 'B' }, 2),
    ])
    globalThis.fetch = vi.fn().mockResolvedValue(new Response(stream, { status: 200 })) as never

    const received: StreamFrame[] = []
    const ctrl = useChatStream(
      { apiBase: 'http://x', threadId: 't1', body: { content: 'hi' } },
      { onFrame: (f) => received.push(f) },
    )
    await ctrl.start()
    expect(received).toHaveLength(2)
  })

  it("propre arrêt sur abort", async () => {
    const ac = new AbortController()
    globalThis.fetch = vi.fn().mockImplementation(() => {
      ac.abort()
      return Promise.reject(new DOMException('aborted', 'AbortError'))
    }) as never

    let closed: string | null = null
    const ctrl = useChatStream(
      { apiBase: 'http://x', threadId: 't1', body: { content: 'hi' }, signal: ac.signal },
      { onFrame: () => {}, onClose: (reason) => { closed = reason } },
    )
    await ctrl.start()
    expect(closed === 'aborted' || closed === 'error').toBe(true)
  })

  it("émet une erreur sur HTTP 4xx hors 500", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(new Response('', { status: 403 })) as never
    const received: StreamFrame[] = []
    const ctrl = useChatStream(
      { apiBase: 'http://x', threadId: 't1', body: { content: 'hi' } },
      { onFrame: (f) => received.push(f) },
    )
    await ctrl.start()
    expect(received.find((f) => f.event === 'error')).toBeTruthy()
  })
})
