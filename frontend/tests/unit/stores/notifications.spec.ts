// F38 T012 — Tests store notifications
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

const fetchMock = vi.fn()
;(globalThis as { $fetch?: unknown }).$fetch = fetchMock
;(globalThis as { useRuntimeConfig?: unknown }).useRuntimeConfig = () => ({
  public: { apiBase: 'http://api' },
})
;(globalThis as { useCsrf?: unknown }).useCsrf = () => ({
  withCsrf: () => ({ 'x-csrf-token': 'tok' }),
})

import {
  useNotificationsStore,
  type Notification,
} from '../../../app/stores/notifications'

function makeNotif(over: Partial<Notification> = {}): Notification {
  return {
    id: over.id ?? '1',
    kind: over.kind ?? 'system',
    title: over.title ?? 'Hello',
    body: over.body,
    link: over.link,
    created_at: over.created_at ?? '2026-05-03T10:00:00Z',
    read_at: over.read_at ?? null,
  }
}

describe('useNotificationsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    fetchMock.mockReset()
  })

  it('loadInitial remplit items et calcule unreadCount', async () => {
    fetchMock.mockResolvedValueOnce([
      makeNotif({ id: 'a' }),
      makeNotif({ id: 'b', read_at: '2026-05-03T11:00:00Z' }),
    ])
    const s = useNotificationsStore()
    await s.loadInitial()
    expect(s.items).toHaveLength(2)
    expect(s.unreadCount).toBe(1)
    expect(s.latestUnread.map((n) => n.id)).toEqual(['a'])
  })

  it('rejette les payloads invalides', async () => {
    fetchMock.mockResolvedValueOnce([
      { id: 'x' }, // incomplet
      makeNotif({ id: 'ok', kind: 'system' }),
      makeNotif({ id: 'bad', kind: 'unknown' as unknown as Notification['kind'] }),
    ])
    const s = useNotificationsStore()
    await s.loadInitial()
    expect(s.items.map((n) => n.id)).toEqual(['ok'])
  })

  it('markRead idempotent (no-op si déjà lu)', async () => {
    const s = useNotificationsStore()
    s.$patch({
      items: [makeNotif({ id: 'a', read_at: '2026-05-03T12:00:00Z' })],
    })
    await s.markRead('a')
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('markRead met à jour read_at localement', async () => {
    fetchMock.mockResolvedValueOnce(undefined)
    const s = useNotificationsStore()
    s.$patch({ items: [makeNotif({ id: 'a' })] })
    await s.markRead('a')
    expect(s.items[0].read_at).toBeTruthy()
    expect(s.unreadCount).toBe(0)
  })

  it('reset() vide tout', () => {
    const s = useNotificationsStore()
    s.$patch({ items: [makeNotif()], isStreamConnected: true })
    s.reset()
    expect(s.items).toEqual([])
    expect(s.isStreamConnected).toBe(false)
    expect(s.lastSyncedAt).toBeNull()
  })

  it('pushFromStream insère ou met à jour', () => {
    const s = useNotificationsStore()
    s.pushFromStream(makeNotif({ id: 'a', title: 'v1' }))
    s.pushFromStream(makeNotif({ id: 'a', title: 'v2' }))
    s.pushFromStream(makeNotif({ id: 'b' }))
    expect(s.items).toHaveLength(2)
    expect(s.items.find((n) => n.id === 'a')?.title).toBe('v2')
  })

  it('plafonne items à 50 (FIFO)', () => {
    const s = useNotificationsStore()
    for (let i = 0; i < 60; i++) {
      s.pushFromStream(
        makeNotif({
          id: String(i),
          created_at: `2026-05-${String(i + 1).padStart(2, '0')}T00:00:00Z`,
        })
      )
    }
    expect(s.items).toHaveLength(50)
  })
})
