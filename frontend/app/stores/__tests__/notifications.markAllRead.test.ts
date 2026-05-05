// F52 US1 — Tests vitest store notifications : markAllReadOptimistic + rollback.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useNotificationsStore } from '../notifications'

declare global {
  // eslint-disable-next-line no-var
  var $fetch: unknown
  // eslint-disable-next-line no-var
  var useRuntimeConfig: unknown
}

function fixture() {
  return [
    {
      id: 'n1',
      kind: 'deadline_j_minus_30' as const,
      title: 'A',
      created_at: '2026-05-01T10:00:00Z',
      read_at: null,
    },
    {
      id: 'n2',
      kind: 'offre_recommandee' as const,
      title: 'B',
      created_at: '2026-05-02T10:00:00Z',
      read_at: null,
    },
    {
      id: 'n3',
      kind: 'system' as const,
      title: 'C',
      created_at: '2026-05-03T10:00:00Z',
      read_at: '2026-05-03T11:00:00Z',
    },
  ]
}

describe('useNotificationsStore — markAllReadOptimistic', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    globalThis.useRuntimeConfig = () => ({ public: { apiBase: 'http://api' } })
    globalThis.useCsrf = () => ({ withCsrf: () => ({}) })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("met immédiatement read_at sur toutes les non-lues (optimistic)", async () => {
    globalThis.$fetch = vi.fn().mockResolvedValue({
      updated_count: 2,
      unread_count_after: 0,
    })
    const store = useNotificationsStore()
    store.items = fixture()
    expect(store.unreadCount).toBe(2)

    const promise = store.markAllReadOptimistic()
    // pendant l'attente, l'optimistic update est déjà appliqué
    expect(store.unreadCount).toBe(0)
    const resp = await promise
    expect(resp.updated_count).toBe(2)
    expect(store.unreadCount).toBe(0)
  })

  it("rollback en cas d'échec serveur", async () => {
    globalThis.$fetch = vi.fn().mockRejectedValue(new Error('boom'))
    const store = useNotificationsStore()
    store.items = fixture()

    await expect(store.markAllReadOptimistic()).rejects.toThrow('boom')
    // rollback : les non-lues restent non-lues
    expect(store.unreadCount).toBe(2)
    expect(store.loadError?.message).toBe('boom')
  })

  it("filtre par kinds limite la mutation", async () => {
    globalThis.$fetch = vi.fn().mockResolvedValue({
      updated_count: 1,
      unread_count_after: 1,
    })
    const store = useNotificationsStore()
    store.items = fixture()
    await store.markAllReadOptimistic(['deadline_j_minus_30'])
    expect(store.items.find((n) => n.id === 'n1')?.read_at).not.toBeNull()
    expect(store.items.find((n) => n.id === 'n2')?.read_at).toBeNull()
  })

  it("applyBulkReadFromStream (autre onglet) met read_at sans HTTP", () => {
    const store = useNotificationsStore()
    store.items = fixture()
    store.applyBulkReadFromStream({ kinds: null, count: 2 })
    expect(store.unreadCount).toBe(0)
  })
})
