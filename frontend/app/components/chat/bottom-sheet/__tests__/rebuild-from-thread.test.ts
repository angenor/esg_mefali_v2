/**
 * T048 — Test reconstitution depuis le thread (Q1).
 *
 * Scénario : reload page → `rebuildFromThread(threadId)` interroge l'API,
 * reçoit le dernier message tool pending, et ouvre le sheet correspondant.
 * Cas vides (204/null) : aucun sheet ouvert.
 * Cas erreur : pas de crash, sheet reste fermé.
 */
import { describe, expect, it, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useChatBottomSheet } from '~/composables/useChatBottomSheet'

const ctx = {
  thread_id: '11111111-1111-1111-1111-111111111111',
  message_id: '22222222-2222-2222-2222-222222222222',
}

const validPending = {
  tool: 'ask_yes_no',
  payload: { question: 'Reprendre ?' },
  context: ctx,
}

beforeEach(() => {
  setActivePinia(createPinia())
})

describe('useChatBottomSheet.rebuildFromThread', () => {
  it('ouvre le sheet quand l\'API retourne un tool pending valide', async () => {
    const fetchPending = vi.fn().mockResolvedValue(validPending)
    const sheet = useChatBottomSheet({ fetchPending })

    expect(sheet.isOpen.value).toBe(false)
    await sheet.rebuildFromThread(ctx.thread_id)

    expect(fetchPending).toHaveBeenCalledWith(ctx.thread_id)
    expect(sheet.isOpen.value).toBe(true)
    expect(sheet.current.value?.tool).toBe('ask_yes_no')
  })

  it('reste fermé si l\'API retourne null (aucun pending)', async () => {
    const fetchPending = vi.fn().mockResolvedValue(null)
    const sheet = useChatBottomSheet({ fetchPending })

    await sheet.rebuildFromThread(ctx.thread_id)
    expect(sheet.isOpen.value).toBe(false)
  })

  it('ignore silencieusement une erreur réseau', async () => {
    const fetchPending = vi.fn().mockRejectedValue(new Error('network'))
    const sheet = useChatBottomSheet({ fetchPending })
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})

    await sheet.rebuildFromThread(ctx.thread_id)
    expect(sheet.isOpen.value).toBe(false)
    expect(warn).toHaveBeenCalled()
    warn.mockRestore()
  })

  it('rejette un payload invalide sans ouvrir le sheet', async () => {
    const fetchPending = vi.fn().mockResolvedValue({ tool: 'inconnu', payload: {}, context: ctx })
    const sheet = useChatBottomSheet({ fetchPending })
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})

    await sheet.rebuildFromThread(ctx.thread_id)
    expect(sheet.isOpen.value).toBe(false)
    warn.mockRestore()
  })

  it('utilise l\'URL conventionnelle /me/chat/threads/{id}/pending-tool par défaut', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    ;(globalThis as unknown as { fetch: typeof fetch }).fetch = fetchMock as unknown as typeof fetch
    const sheet = useChatBottomSheet()

    await sheet.rebuildFromThread(ctx.thread_id)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const url = fetchMock.mock.calls[0]![0] as string
    expect(url).toMatch(new RegExp(`/me/chat/threads/${ctx.thread_id}/pending-tool$`))
    expect(sheet.isOpen.value).toBe(false)
  })
})
