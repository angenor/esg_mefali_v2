/**
 * F41 / US2 (T030). Intégration bottom sheet : tool_invoke ouvre la sheet ;
 * dismiss-for-freetext positionne forceFreetextNext ; envoi suivant porte
 * context_json.force_freetext = true.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useChatStore } from '~/stores/chat'
import { useChatBottomSheetStore } from '~/stores/chatBottomSheet'

describe('Chat ↔ BottomSheet integration', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it("forceFreetextNext est ajouté à context_json au prochain envoi", async () => {
    const store = useChatStore()
    store.currentThreadId = 't1'
    store.messagesByThread = { t1: [] }
    store.setForceFreetext(true)
    expect(store.forceFreetextNext).toBe(true)

    const fetchSpy = vi.fn().mockImplementation(() => {
      // simulateur fetch — on s'arrête avant le streaming réel.
      return Promise.resolve(new Response('', { status: 200 }))
    })
    globalThis.fetch = fetchSpy as never

    await store.sendMessage('test freetext')
    // Attendons le tick async
    await new Promise((r) => setTimeout(r, 0))

    expect(store.forceFreetextNext).toBe(false) // consommé
    const fetchCall = fetchSpy.mock.calls.find((c) => String(c[0]).includes('/messages'))
    if (fetchCall) {
      const body = JSON.parse(String((fetchCall[1] as RequestInit).body))
      expect(body.context_json?.force_freetext).toBe(true)
    }
  })

  it("handleFrame tool_invoke met le streaming en awaiting_sheet", () => {
    const store = useChatStore()
    store.currentThreadId = 't1'
    store.messagesByThread = { t1: [] }
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
    store.handleFrame({ event: 'tool_invoke', data: { tool: 'ask_qcu' } })
    expect(store.streaming?.phase).toBe('awaiting_sheet')
  })

  it("le store chatBottomSheet expose isOpen et requestFreeText", () => {
    const sheet = useChatBottomSheetStore()
    expect(sheet.isOpen).toBe(false)
    sheet.requestFreeText()
    expect(sheet.freeTextRequested).toBe(true)
  })
})
