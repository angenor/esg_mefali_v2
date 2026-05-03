/**
 * useChatStream — consommation SSE depuis POST /me/chat/threads/{id}/messages.
 *
 * Référence : specs/041-chat-conversational-layer/research.md R1 + R6.
 * Implémentation : fetch + ReadableStream + TextDecoderStream + parse manuel
 * des frames SSE (event:, data:, id:, ligne vide). Dedup via Set<sequence_id>.
 * Backoff reconnect exponentiel 1/2/4/8 s, max 5 essais.
 */
import type { StreamFrame, SendMessageBody } from '~/types/chat'

export interface ChatStreamHandlers {
  onFrame: (frame: StreamFrame) => void
  onOpen?: () => void
  onClose?: (reason: 'done' | 'aborted' | 'error', error?: unknown) => void
  onReconnect?: (attempt: number, delayMs: number) => void
}

export interface ChatStreamOptions {
  apiBase: string
  threadId: string
  body: SendMessageBody
  signal?: AbortSignal
  /** Header Authorization optionnel (JWT). Cookies session-cookie sont envoyés via credentials. */
  authHeader?: string
}

const MAX_RETRIES = 5
const BACKOFF_MS = [1000, 2000, 4000, 8000, 8000]

interface ParsedFrame {
  event: string
  data: string
  id?: number
}

function* extractFrames(buffer: string): Generator<{ raw: string; rest: string }> {
  let rest = buffer
  while (true) {
    const sep = rest.indexOf('\n\n')
    if (sep < 0) {
      yield { raw: '', rest }
      return
    }
    const raw = rest.slice(0, sep)
    rest = rest.slice(sep + 2)
    yield { raw, rest }
  }
}

function parseFrame(raw: string): ParsedFrame | null {
  if (!raw.trim()) return null
  let event = 'message'
  const dataLines: string[] = []
  let id: number | undefined
  for (const line of raw.split('\n')) {
    if (line.startsWith(':')) continue
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).replace(/^ /, ''))
    } else if (line.startsWith('id:')) {
      const n = Number(line.slice(3).trim())
      if (!Number.isNaN(n)) id = n
    }
  }
  return { event, data: dataLines.join('\n'), id }
}

function toStreamFrame(parsed: ParsedFrame): StreamFrame | null {
  const allowed = new Set([
    'token', 'message_done', 'tool_invoke', 'mutation', 'error', 'memory_updated',
  ])
  if (!allowed.has(parsed.event)) return null
  let data: unknown
  try {
    data = parsed.data ? JSON.parse(parsed.data) : {}
  } catch {
    return null
  }
  return { event: parsed.event as StreamFrame['event'], id: parsed.id, data: data as never } as StreamFrame
}

export interface ChatStreamController {
  start: () => Promise<void>
  abort: () => void
}

export function useChatStream(
  options: ChatStreamOptions,
  handlers: ChatStreamHandlers,
): ChatStreamController {
  const seenSeq = new Set<number>()
  let attempt = 0
  const ownController = new AbortController()
  const externalSignal = options.signal
  if (externalSignal) {
    if (externalSignal.aborted) ownController.abort()
    else externalSignal.addEventListener('abort', () => ownController.abort(), { once: true })
  }

  function sleep(ms: number, signal: AbortSignal): Promise<void> {
    return new Promise((resolve) => {
      const t = setTimeout(resolve, ms)
      signal.addEventListener('abort', () => {
        clearTimeout(t)
        resolve()
      }, { once: true })
    })
  }

  async function streamOnce(): Promise<'done' | 'retry'> {
    const url = `${options.apiBase.replace(/\/$/, '')}/me/chat/threads/${options.threadId}/messages`
    const headers: Record<string, string> = {
      'content-type': 'application/json',
      accept: 'text/event-stream',
    }
    if (options.authHeader) headers.authorization = options.authHeader

    const res = await fetch(url, {
      method: 'POST',
      headers,
      credentials: 'include',
      body: JSON.stringify(options.body),
      signal: ownController.signal,
    })
    if (!res.ok || !res.body) {
      if (res.status >= 500 || res.status === 0) return 'retry'
      handlers.onFrame({
        event: 'error',
        data: { code: res.status === 403 ? 'forbidden' : 'validation', message: `HTTP ${res.status}` },
      })
      return 'done'
    }
    handlers.onOpen?.()
    const reader = res.body.pipeThrough(new TextDecoderStream()).getReader()
    let buffer = ''
    try {
      while (true) {
        const { value, done } = await reader.read()
        if (done) return 'done'
        buffer += value
        let lastRest = buffer
        for (const { raw, rest } of extractFrames(buffer)) {
          lastRest = rest
          if (!raw) break
          const parsed = parseFrame(raw)
          if (!parsed) continue
          if (parsed.id !== undefined) {
            if (seenSeq.has(parsed.id)) continue
            seenSeq.add(parsed.id)
          }
          const frame = toStreamFrame(parsed)
          if (frame) handlers.onFrame(frame)
        }
        buffer = lastRest
      }
    } finally {
      try { await reader.cancel() } catch { /* ignore */ }
    }
  }

  async function start(): Promise<void> {
    while (attempt <= MAX_RETRIES) {
      try {
        const result = await streamOnce()
        if (result === 'done') {
          handlers.onClose?.('done')
          return
        }
        // retry path
      } catch (err) {
        if (ownController.signal.aborted) {
          handlers.onClose?.('aborted')
          return
        }
        if (attempt >= MAX_RETRIES) {
          handlers.onClose?.('error', err)
          return
        }
      }
      attempt += 1
      const delay = BACKOFF_MS[Math.min(attempt - 1, BACKOFF_MS.length - 1)] ?? 8000
      handlers.onReconnect?.(attempt, delay)
      await sleep(delay, ownController.signal)
      if (ownController.signal.aborted) {
        handlers.onClose?.('aborted')
        return
      }
    }
    handlers.onClose?.('error', new Error('max retries exceeded'))
  }

  function abort(): void {
    ownController.abort()
  }

  return { start, abort }
}
