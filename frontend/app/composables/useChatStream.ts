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
  /**
   * Idle timeout en ms : si aucun frame SSE n'arrive pendant cette durée,
   * le stream est avorté et un frame ``error`` (code='timeout') est émis.
   *
   * Défaut : 45 s — légèrement supérieur au ``LLM_AGENT_TIMEOUT_S`` backend
   * (30 s par défaut) pour laisser le backend émettre lui-même un error
   * timeout avant que le client ne décide. Set à 0 pour désactiver
   * (utile en tests).
   */
  idleTimeoutMs?: number
}

const MAX_RETRIES = 5
const BACKOFF_MS = [1000, 2000, 4000, 8000, 8000]
const DEFAULT_IDLE_TIMEOUT_MS = 45_000

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
  // Backend (cf. backend/app/chat/llm_stream.py + sse-envelope.schema.json) émet :
  //   text_delta {delta}, message_done {message_id}, error {code, detail},
  //   tool_call_started, tool_call_completed, entity_updated.
  // Frontend StreamFrame utilise des conventions camelCase. On normalise ici.
  const allowedBackend = new Set([
    'text_delta', 'message_done', 'error', 'entity_updated',
    'tool_call_started', 'tool_call_completed',
    // Conventions historiques préservées (fallback) :
    'token', 'tool_invoke', 'mutation', 'memory_updated',
  ])
  if (!allowedBackend.has(parsed.event)) return null
  let raw: Record<string, unknown> = {}
  try {
    raw = parsed.data ? (JSON.parse(parsed.data) as Record<string, unknown>) : {}
  } catch {
    return null
  }

  switch (parsed.event) {
    case 'text_delta':
    case 'token': {
      const content = (raw.delta as string | undefined) ?? (raw.content as string | undefined) ?? ''
      return { event: 'token', id: parsed.id, data: { content } } as StreamFrame
    }
    case 'message_done': {
      const messageId = (raw.message_id as string | undefined) ?? (raw.messageId as string | undefined) ?? ''
      // Backend ne renvoie pas systématiquement `content` (cf. llm_stream.py).
      // Laisser undefined permet au store d'utiliser partialContent accumulé.
      const content = raw.content as string | undefined
      const payload = (raw.payload as never) ?? null
      const data: { messageId: string; content?: string; payload: never } = { messageId, payload }
      if (content !== undefined) data.content = content
      return { event: 'message_done', id: parsed.id, data } as StreamFrame
    }
    case 'error': {
      const code = (raw.code as string | undefined) ?? 'unknown'
      const message = (raw.message as string | undefined) ?? (raw.detail as string | undefined) ?? 'Erreur'
      return { event: 'error', id: parsed.id, data: { code: code as never, message } } as StreamFrame
    }
    case 'entity_updated':
    case 'mutation': {
      return { event: 'mutation', id: parsed.id, data: raw as never } as StreamFrame
    }
    case 'tool_call_started':
    case 'tool_invoke': {
      return { event: 'tool_invoke', id: parsed.id, data: raw as never } as StreamFrame
    }
    case 'tool_call_completed':
    case 'memory_updated': {
      return { event: 'memory_updated', id: parsed.id, data: raw as never } as StreamFrame
    }
    default:
      return null
  }
}

function csrfHeaderForStream(): Record<string, string> {
  if (typeof document === 'undefined') return {}
  const m = document.cookie.match(/(?:^|;\s*)mefali_csrf=([^;]+)/)
  return m ? { 'X-CSRF-Token': decodeURIComponent(m[1]!) } : {}
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
  const idleTimeoutMs = options.idleTimeoutMs ?? DEFAULT_IDLE_TIMEOUT_MS
  let attempt = 0
  let timedOut = false
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
      ...csrfHeaderForStream(),
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
    // Idle timeout : reset à chaque frame reçue. Si dépasse ``idleTimeoutMs``
    // sans event, on aborte le fetch + ``reader.cancel()`` (l'abort fetch
    // seul ne propage PAS sur le reader d'une response déjà reçue).
    let idleTimer: ReturnType<typeof setTimeout> | null = null
    function armIdleTimer(): void {
      if (idleTimeoutMs <= 0) return
      if (idleTimer !== null) clearTimeout(idleTimer)
      idleTimer = setTimeout(() => {
        timedOut = true
        try { ownController.abort() } catch { /* ignore */ }
        // ``reader.cancel()`` propage AbortError dans ``reader.read()`` en
        // attente — sans cela, le stream resterait suspendu.
        reader.cancel(new Error('idle_timeout')).catch(() => {})
      }, idleTimeoutMs)
    }
    function disarmIdleTimer(): void {
      if (idleTimer !== null) {
        clearTimeout(idleTimer)
        idleTimer = null
      }
    }
    armIdleTimer()
    try {
      while (true) {
        const { value, done } = await reader.read()
        if (done) {
          // ``reader.cancel()`` (déclenché par le timeout) résout aussi avec
          // ``done=true``. Il faut distinguer une fin normale d'un cancel
          // forcé pour propager une erreur ``timeout`` à ``start()``.
          if (timedOut) throw new Error('idle_timeout')
          return 'done'
        }
        armIdleTimer()
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
      disarmIdleTimer()
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
        // Idle timeout : on a aborté nous-mêmes après ``idleTimeoutMs`` sans
        // frame. On émet un error frame explicite pour que l'UI puisse
        // afficher un message clair et ré-activer le bouton « Envoyer ».
        if (timedOut) {
          handlers.onFrame({
            event: 'error',
            data: {
              code: 'timeout',
              message:
                "Pas de réponse de l'assistant après "
                + `${Math.round(idleTimeoutMs / 1000)} s. Merci de réessayer.`,
            },
          })
          handlers.onClose?.('error', err)
          return
        }
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
