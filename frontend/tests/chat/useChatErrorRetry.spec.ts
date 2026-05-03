/**
 * F41 / US7 (T049). Erreur LLM → bulle erreur ; retry resend même contenu.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useChatStore } from '~/stores/chat'

describe('Chat error + retry', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it("handleFrame error transforme la bulle en erreur + remplit errors", () => {
    const store = useChatStore()
    store.currentThreadId = 't1'
    store.messagesByThread = {
      t1: [
        { id: 'u1', threadId: 't1', role: 'user', content: 'hello', payload: null, createdAt: '' },
        { id: 'a1', threadId: 't1', role: 'assistant', content: '', payload: null, createdAt: '', streaming: true },
      ],
    }
    store.streaming = {
      threadId: 't1',
      userMessageId: 'u1',
      assistantMessageId: 'a1',
      abortController: new AbortController(),
      seqSeen: new Set(),
      partialContent: '',
      startedAt: 0,
      firstTokenAt: null,
      retryCount: 0,
      phase: 'streaming',
    }
    store.handleFrame({ event: 'error', data: { code: 'timeout', message: 'slow' } })
    expect(store.errors.a1).toBeTruthy()
    expect(store.errors.a1?.code).toBe('timeout')
    const msg = store.messagesByThread.t1?.find((m) => m.id === 'a1')
    expect(msg?.payload?.kind).toBe('error')
  })

  it("retry retire la bulle erreur et relance sendMessage avec le contenu original", () => {
    const store = useChatStore()
    store.currentThreadId = 't1'
    store.messagesByThread = {
      t1: [
        { id: 'u1', threadId: 't1', role: 'user', content: 'question', payload: null, createdAt: '' },
        { id: 'a1', threadId: 't1', role: 'assistant', content: '', payload: { kind: 'error', code: 'timeout', message: 'x', retryOf: 'a1' }, createdAt: '' },
      ],
    }
    store.errors = {
      a1: { messageId: 'a1', retryOf: { content: 'question', payload: null }, code: 'timeout', message: 'x' },
    }
    let captured: string | null = null
    const orig = store.sendMessage.bind(store)
    store.sendMessage = ((content: string) => {
      captured = content
      return Promise.resolve()
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    }) as any
    store.retry('a1')
    expect(store.errors.a1).toBeUndefined()
    expect(captured).toBe('question')
    store.sendMessage = orig
  })
})
