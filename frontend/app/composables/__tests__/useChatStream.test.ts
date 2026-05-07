/**
 * useChatStream — tests vitest pour le timeout idle SSE et les error frames.
 *
 * Couvre :
 * - timeout idle (45 s par défaut, override via ``idleTimeoutMs``) émet un
 *   error frame ``code='timeout'`` puis ``onClose('error')``.
 * - error frame backend ``error`` propagé tel quel à ``onFrame``.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useChatStream } from '../useChatStream'

type FetchMock = ReturnType<typeof vi.fn>

const ORIGINAL_FETCH = globalThis.fetch
let fetchMock: FetchMock

function makeSseResponse(body: ReadableStream<Uint8Array>): Response {
  return new Response(body, {
    status: 200,
    headers: { 'content-type': 'text/event-stream' },
  })
}

function streamFromEncoder(
  emit: (controller: ReadableStreamDefaultController<Uint8Array>) => Promise<void>,
): ReadableStream<Uint8Array> {
  return new ReadableStream<Uint8Array>({
    async start(controller) {
      try {
        await emit(controller)
      } catch (err) {
        controller.error(err)
      }
    },
  })
}

beforeEach(() => {
  fetchMock = vi.fn()
  globalThis.fetch = fetchMock as unknown as typeof fetch
})

afterEach(() => {
  globalThis.fetch = ORIGINAL_FETCH
  vi.useRealTimers()
})

describe('useChatStream — timeout idle', () => {
  it('emits error frame when no SSE event arrives within idleTimeoutMs', async () => {
    // Stream qui n'émet rien et reste pendu (real timers, idleTimeoutMs court).
    let pendingResolve: (() => void) | null = null
    const body = streamFromEncoder(async (_controller) => {
      await new Promise<void>((resolve) => {
        pendingResolve = resolve
      })
    })
    fetchMock.mockResolvedValueOnce(makeSseResponse(body))

    const frames: Array<{ event: string; data: unknown }> = []
    const closes: string[] = []
    const stream = useChatStream(
      {
        apiBase: 'http://localhost:8010',
        threadId: 't1',
        body: { content: 'hi', context_json: { page_route: '/' } },
        idleTimeoutMs: 80,
      },
      {
        onFrame: (f) => {
          frames.push({ event: f.event, data: f.data })
        },
        onClose: (reason) => {
          closes.push(reason)
        },
      },
    )

    const startPromise = stream.start()
    await startPromise
    if (pendingResolve) (pendingResolve as () => void)()

    expect(frames.length).toBeGreaterThan(0)
    const timeoutFrame = frames.find(
      (f) => f.event === 'error' && (f.data as { code: string }).code === 'timeout',
    )
    expect(timeoutFrame).toBeDefined()
    expect(closes).toContain('error')
  }, 10_000)

  it('idleTimeoutMs=0 disables timeout (no timer fires)', async () => {
    // Stream qui done immédiatement après un message_done.
    const body = streamFromEncoder(async (controller) => {
      const enc = new TextEncoder()
      controller.enqueue(
        enc.encode('event: message_done\ndata: {"message_id":"m-1"}\n\n'),
      )
      controller.close()
    })
    fetchMock.mockResolvedValueOnce(makeSseResponse(body))

    const frames: Array<{ event: string }> = []
    const closes: string[] = []
    const stream = useChatStream(
      {
        apiBase: 'http://localhost:8010',
        threadId: 't1',
        body: { content: 'hi', context_json: { page_route: '/' } },
        idleTimeoutMs: 0,
      },
      {
        onFrame: (f) => frames.push({ event: f.event }),
        onClose: (reason) => closes.push(reason),
      },
    )

    await stream.start()

    expect(closes).toContain('done')
    // Aucun error frame émis (pas de timeout).
    const errorFrames = frames.filter((f) => f.event === 'error')
    expect(errorFrames).toHaveLength(0)
  })
})

describe('useChatStream — error frames du backend', () => {
  it('propagates explicit error event from backend to onFrame', async () => {
    const body = streamFromEncoder(async (controller) => {
      const enc = new TextEncoder()
      controller.enqueue(
        enc.encode(
          'event: error\ndata: {"code":"internal","message":"boom"}\n\n',
        ),
      )
      controller.close()
    })
    fetchMock.mockResolvedValueOnce(makeSseResponse(body))

    const frames: Array<{ event: string; data: unknown }> = []
    const stream = useChatStream(
      {
        apiBase: 'http://localhost:8010',
        threadId: 't1',
        body: { content: 'hi', context_json: { page_route: '/' } },
        idleTimeoutMs: 0,
      },
      { onFrame: (f) => frames.push({ event: f.event, data: f.data }) },
    )

    await stream.start()

    const errorFrame = frames.find((f) => f.event === 'error')
    expect(errorFrame).toBeDefined()
    expect((errorFrame?.data as { code: string }).code).toBe('internal')
  })
})
