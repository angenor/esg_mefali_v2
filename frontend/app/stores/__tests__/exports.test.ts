// F52 US3 — Tests Pinia store exports : load, create, refreshOne.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useExportsStore } from '../exports'

declare global {
  // eslint-disable-next-line no-var
  var $fetch: unknown
  // eslint-disable-next-line no-var
  var useRuntimeConfig: unknown
  // eslint-disable-next-line no-var
  var useCsrf: unknown
}

const ITEM = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  type: 'rgpd_full' as const,
  format: 'json' as const,
  size_bytes: 1024,
  status: 'ready' as const,
  created_at: '2026-05-05T12:00:00Z',
  ready_at: '2026-05-05T12:00:30Z',
  signed_url: 'https://eu/exp',
  signed_url_expires_at: '2026-05-12T12:00:00Z',
  delivered_via: 'inapp' as const,
}

describe('useExportsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    globalThis.useRuntimeConfig = () => ({ public: { apiBase: 'http://api' } })
    globalThis.useCsrf = () => ({ withCsrf: () => ({}) })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('load() peuple items et nextCursor', async () => {
    globalThis.$fetch = vi
      .fn()
      .mockResolvedValue({ items: [ITEM], next_cursor: 'cur1' })
    const store = useExportsStore()
    await store.load()
    expect(store.items).toHaveLength(1)
    expect(store.nextCursor).toBe('cur1')
    expect(store.loading).toBe(false)
  })

  it('load() append en mode cursor', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ items: [ITEM], next_cursor: 'cur1' })
      .mockResolvedValueOnce({
        items: [{ ...ITEM, id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb' }],
        next_cursor: null,
      })
    globalThis.$fetch = fetchMock
    const store = useExportsStore()
    await store.load()
    await store.load({ cursor: 'cur1' })
    expect(store.items).toHaveLength(2)
    expect(store.nextCursor).toBeNull()
  })

  it("create() insère l'export en tête de liste", async () => {
    globalThis.$fetch = vi.fn().mockResolvedValue(ITEM)
    const store = useExportsStore()
    const result = await store.create({ type: 'rgpd_full', format: 'json' })
    expect(result?.id).toBe(ITEM.id)
    expect(store.items[0]?.id).toBe(ITEM.id)
  })

  it('create() expose error en cas d\'échec', async () => {
    globalThis.$fetch = vi.fn().mockRejectedValue(new Error('boom'))
    const store = useExportsStore()
    const result = await store.create({ type: 'rgpd_full', format: 'json' })
    expect(result).toBeNull()
    expect(store.error).toBe('boom')
  })

  it('handleSseSystemEvent rafraîchit l\'export ciblé', async () => {
    const updated = { ...ITEM, status: 'ready' as const }
    globalThis.$fetch = vi.fn().mockResolvedValue(updated)
    const store = useExportsStore()
    store.items = [{ ...ITEM, status: 'pending' as const, signed_url: null }]
    store.handleSseSystemEvent({ export_id: ITEM.id })
    // Laisse passer la microtask
    await Promise.resolve()
    await Promise.resolve()
    expect(store.items[0]?.status).toBe('ready')
  })
})
