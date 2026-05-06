/**
 * useChatStore — store unique du domaine Chat (F41).
 *
 * Référence : specs/041-chat-conversational-layer/research.md R8 +
 * data-model.md §1.4. Gère threads, messages, état de stream, erreurs et
 * flag de re-classification freetext.
 */
import { defineStore } from 'pinia'
import type {
  ChatError,
  ChatMessage,
  ChatThreadSummary,
  MemorySnapshot,
  MessagePayload,
  StreamingState,
  StreamingPhase,
  SendMessageBody,
  StreamFrame,
} from '~/types/chat'
import { useChatStream } from '~/composables/useChatStream'
import { useChatEventBus } from '~/composables/useChatEventBus'

interface ApiThreadRow {
  id: string
  title: string
  archived: boolean
  created_at: string
  updated_at: string
}
interface ApiMessageRow {
  id: string
  thread_id: string
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  payload_json: MessagePayload | null
  context_json?: Record<string, unknown> | null
  created_at: string
}
interface ApiThreadList {
  threads: ApiThreadRow[]
}
interface ApiMessageList {
  messages: ApiMessageRow[]
}

function mapThread(row: ApiThreadRow): ChatThreadSummary {
  return {
    id: row.id,
    title: row.title,
    archived: row.archived,
    createdAt: row.created_at,
    lastMessageAt: row.updated_at,
  }
}

function mapMessage(row: ApiMessageRow): ChatMessage {
  return {
    id: row.id,
    threadId: row.thread_id,
    role: row.role === 'tool' ? 'system' : row.role,
    content: row.content,
    payload: row.payload_json ?? null,
    createdAt: row.created_at,
  }
}

function csrfHeader(): Record<string, string> {
  if (typeof document === 'undefined') return {}
  const m = document.cookie.match(/(?:^|;\s*)mefali_csrf=([^;]+)/)
  return m ? { 'X-CSRF-Token': decodeURIComponent(m[1]!) } : {}
}

interface ChatState {
  threads: ChatThreadSummary[]
  currentThreadId: string | null
  messagesByThread: Record<string, ChatMessage[]>
  streaming: StreamingState | null
  forceFreetextNext: boolean
  errors: Record<string, ChatError>
  memorySnapshots: Record<string, MemorySnapshot>
  loaded: boolean
}

function apiBase(): string {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const cfg = (globalThis as any).useRuntimeConfig?.()
  return String(cfg?.public?.apiBase ?? 'http://localhost:8010').replace(/\/$/, '')
}

function uuid(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID()
  return `tmp-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

export const useChatStore = defineStore('chat', {
  state: (): ChatState => ({
    threads: [],
    currentThreadId: null,
    messagesByThread: {},
    streaming: null,
    forceFreetextNext: false,
    errors: {},
    memorySnapshots: {},
    loaded: false,
  }),
  getters: {
    currentMessages(state): ChatMessage[] {
      if (!state.currentThreadId) return []
      return state.messagesByThread[state.currentThreadId] ?? []
    },
    currentThread(state): ChatThreadSummary | null {
      if (!state.currentThreadId) return null
      return state.threads.find((t) => t.id === state.currentThreadId) ?? null
    },
    isStreaming(state): boolean {
      return state.streaming !== null
        && state.streaming.phase !== 'idle'
        && state.streaming.phase !== 'cancelled'
    },
    streamingPhase(state): StreamingPhase {
      return state.streaming?.phase ?? 'idle'
    },
  },
  actions: {
    async loadThreads(): Promise<void> {
      try {
        const res = await fetch(`${apiBase()}/me/chat/threads`, {
          credentials: 'include',
          headers: { accept: 'application/json' },
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = (await res.json()) as ApiThreadList
        this.threads = (data.threads ?? []).map(mapThread)
        this.loaded = true
      } catch (err) {
        // eslint-disable-next-line no-console
        console.warn('[chat] loadThreads failed', err)
        this.threads = []
        this.loaded = true
      }
    },

    async selectThread(threadId: string): Promise<void> {
      this.currentThreadId = threadId
      if (!this.messagesByThread[threadId]) {
        await this.loadMessages(threadId)
      }
    },

    async loadMessages(threadId: string): Promise<void> {
      try {
        const res = await fetch(`${apiBase()}/me/chat/threads/${threadId}/messages`, {
          credentials: 'include',
          headers: { accept: 'application/json' },
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = (await res.json()) as ApiMessageList
        const items = (data.messages ?? []).map(mapMessage)
        this.messagesByThread = { ...this.messagesByThread, [threadId]: items }
      } catch (err) {
        // eslint-disable-next-line no-console
        console.warn('[chat] loadMessages failed', err)
        this.messagesByThread = { ...this.messagesByThread, [threadId]: [] }
      }
    },

    async newThread(): Promise<ChatThreadSummary | null> {
      try {
        const res = await fetch(`${apiBase()}/me/chat/threads`, {
          method: 'POST',
          credentials: 'include',
          headers: {
            'content-type': 'application/json',
            accept: 'application/json',
            ...csrfHeader(),
          },
          body: JSON.stringify({ title: 'Nouveau chat' }),
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const raw = (await res.json()) as ApiThreadRow
        const thread = mapThread(raw)
        this.threads = [thread, ...this.threads]
        this.messagesByThread = { ...this.messagesByThread, [thread.id]: [] }
        this.currentThreadId = thread.id
        return thread
      } catch (err) {
        // eslint-disable-next-line no-console
        console.warn('[chat] newThread failed', err)
        return null
      }
    },

    appendMessage(threadId: string, message: ChatMessage): void {
      const current = this.messagesByThread[threadId] ?? []
      this.messagesByThread = { ...this.messagesByThread, [threadId]: [...current, message] }
    },

    updateMessage(threadId: string, messageId: string, patch: Partial<ChatMessage>): void {
      const current = this.messagesByThread[threadId]
      if (!current) return
      this.messagesByThread = {
        ...this.messagesByThread,
        [threadId]: current.map((m) => (m.id === messageId ? { ...m, ...patch } : m)),
      }
    },

    removeMessage(threadId: string, messageId: string): void {
      const current = this.messagesByThread[threadId]
      if (!current) return
      this.messagesByThread = {
        ...this.messagesByThread,
        [threadId]: current.filter((m) => m.id !== messageId),
      }
    },

    clearForceFreetext(): void {
      this.forceFreetextNext = false
    },

    setForceFreetext(value: boolean): void {
      this.forceFreetextNext = value
    },

    cancelStream(): void {
      if (!this.streaming) return
      try { this.streaming.abortController.abort() } catch { /* ignore */ }
      this.streaming = { ...this.streaming, phase: 'cancelled' }
    },

    async sendMessage(content: string, opts: { payload?: unknown; contextExtra?: Record<string, unknown> } = {}): Promise<void> {
      if (!this.currentThreadId) {
        await this.newThread()
      }
      const threadId = this.currentThreadId
      if (!threadId) return
      if (this.streaming) this.cancelStream()

      const userId = uuid()
      const assistantId = uuid()
      const nowIso = new Date().toISOString()

      this.appendMessage(threadId, {
        id: userId,
        threadId,
        role: 'user',
        content,
        payload: opts.payload != null ? { kind: 'sheet_result', sheetId: '', selection: opts.payload } : null,
        createdAt: nowIso,
      })
      this.appendMessage(threadId, {
        id: assistantId,
        threadId,
        role: 'assistant',
        content: '',
        payload: null,
        createdAt: new Date().toISOString(),
        streaming: true,
      })

      const ctx: Record<string, unknown> = { ...(opts.contextExtra ?? {}) }
      if (this.forceFreetextNext) {
        ctx.force_freetext = true
        this.clearForceFreetext()
      }
      // ContextJson backend exige extra='forbid' et ne tolère que page/entity_type/
      // entity_id/selection. On ne propage que les champs whitelistés.
      const safeCtx: Record<string, unknown> = {}
      for (const k of ['page', 'entity_type', 'entity_id', 'selection'] as const) {
        if (ctx[k] !== undefined) safeCtx[k] = ctx[k]
      }
      const body: SendMessageBody = {
        content,
        context_json: safeCtx,
        payload_json: opts.payload as Record<string, unknown> | null | undefined,
      }

      const ac = new AbortController()
      const streamingState: StreamingState = {
        threadId,
        userMessageId: userId,
        assistantMessageId: assistantId,
        abortController: ac,
        seqSeen: new Set<number>(),
        partialContent: '',
        startedAt: performance.now(),
        firstTokenAt: null,
        retryCount: 0,
        phase: 'streaming',
      }
      this.streaming = streamingState

      const stream = useChatStream(
        { apiBase: apiBase(), threadId, body, signal: ac.signal },
        {
          onFrame: (frame: StreamFrame) => this.handleFrame(frame),
          onClose: (reason) => {
            if (this.streaming?.assistantMessageId === assistantId) {
              const phase: StreamingPhase = reason === 'done' ? 'idle' : reason === 'aborted' ? 'cancelled' : 'error'
              this.streaming = { ...this.streaming, phase }
              if (reason !== 'done') {
                this.updateMessage(threadId, assistantId, { streaming: false })
              }
              if (phase === 'idle' || phase === 'cancelled') this.streaming = null
            }
          },
          onReconnect: (att) => {
            if (this.streaming) this.streaming = { ...this.streaming, retryCount: att }
          },
        },
      )

      void stream.start()
    },

    handleFrame(frame: StreamFrame): void {
      const s = this.streaming
      if (!s) return
      const threadId = s.threadId
      const assistantId = s.assistantMessageId

      switch (frame.event) {
        case 'token': {
          if (s.firstTokenAt === null) s.firstTokenAt = performance.now()
          const next = s.partialContent + (frame.data.content ?? '')
          this.streaming = { ...s, partialContent: next }
          this.updateMessage(threadId, assistantId, { content: next, streaming: true })
          break
        }
        case 'message_done': {
          // F56 — sources agrégées (FR-011) + unsourced_claims précédemment
          // accumulés pour cette assistantId restent attachés.
          this.updateMessage(threadId, assistantId, {
            id: frame.data.messageId || assistantId,
            content: frame.data.content ?? s.partialContent,
            payload: frame.data.payload ?? null,
            streaming: false,
            sources: frame.data.sources ?? undefined,
          })
          break
        }
        case 'unsourced_claim': {
          // F56 — append claim non sourcé sur le message courant (rollup admin)
          const claim = frame.data
          const msgs = this.messagesByThread[threadId] ?? []
          const idx = msgs.findIndex((m) => m.id === assistantId)
          if (idx >= 0) {
            const cur = msgs[idx]
            const next = [...msgs]
            next[idx] = {
              ...cur,
              unsourcedClaims: [...(cur.unsourcedClaims ?? []), claim],
            }
            this.messagesByThread = {
              ...this.messagesByThread,
              [threadId]: next,
            }
          }
          break
        }
        case 'tool_invoke': {
          this.streaming = { ...s, phase: 'awaiting_sheet' }
          // Le plugin/composant écoute tool_invoke via dispatch dédié — ici on
          // l'expose via un événement DOM pour découpler le store de F39.
          if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent('chat:tool-invoke', { detail: frame.data }))
          }
          break
        }
        case 'mutation': {
          const bus = useChatEventBus()
          const evt = frame.data
          bus.emit(evt.eventType ?? 'entity_updated', {
            eventType: evt.eventType ?? 'entity_updated',
            entityType: evt.entityType,
            entityId: evt.entityId,
            fieldsUpdated: evt.fieldsUpdated,
            source: 'llm',
            ts: evt.ts ?? new Date().toISOString(),
          })
          this.updateMessage(threadId, assistantId, { hasMutation: true })
          break
        }
        case 'memory_updated': {
          if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent('chat:memory-updated', { detail: frame.data }))
          }
          break
        }
        case 'error': {
          const errorPayload: MessagePayload = {
            kind: 'error',
            code: frame.data.code,
            message: frame.data.message,
            retryOf: assistantId,
          }
          this.updateMessage(threadId, assistantId, {
            payload: errorPayload,
            streaming: false,
          })
          this.errors = {
            ...this.errors,
            [assistantId]: {
              messageId: assistantId,
              retryOf: { content: this.lastUserContent(threadId, assistantId), payload: null },
              code: frame.data.code,
              message: frame.data.message,
            },
          }
          this.streaming = { ...s, phase: 'error' }
          break
        }
      }
    },

    lastUserContent(threadId: string, beforeMessageId: string): string {
      const msgs = this.messagesByThread[threadId] ?? []
      const idx = msgs.findIndex((m) => m.id === beforeMessageId)
      for (let i = idx - 1; i >= 0; i -= 1) {
        const msg = msgs[i]
        if (msg && msg.role === 'user') return msg.content
      }
      return ''
    },

    retry(messageId: string): void {
      const err = this.errors[messageId]
      if (!err) return
      const threadId = this.currentThreadId
      if (!threadId) return
      this.removeMessage(threadId, messageId)
      const next = { ...this.errors }
      delete next[messageId]
      this.errors = next
      void this.sendMessage(err.retryOf.content, { payload: err.retryOf.payload })
    },

    async fetchMemorySnapshot(threadId: string): Promise<MemorySnapshot | null> {
      try {
        const res = await fetch(`${apiBase()}/me/chat/threads/${threadId}/memory`, {
          credentials: 'include',
          headers: { accept: 'application/json' },
        })
        if (!res.ok) return null
        const snapshot = (await res.json()) as MemorySnapshot
        this.memorySnapshots = { ...this.memorySnapshots, [threadId]: snapshot }
        return snapshot
      } catch {
        return null
      }
    },
  },
})
