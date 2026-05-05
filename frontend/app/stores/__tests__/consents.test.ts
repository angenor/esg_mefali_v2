// F52 US2 — Store consents (load + withdraw).
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useConsentsStore } from '../consents'

declare global {
  // eslint-disable-next-line no-var
  var $fetch: unknown
  // eslint-disable-next-line no-var
  var useRuntimeConfig: unknown
}

describe('useConsentsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    globalThis.useRuntimeConfig = () => ({ public: { apiBase: 'http://api' } })
    globalThis.useCsrf = () => ({ withCsrf: () => ({}) })
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('load() accepte payload tableau OU objet { items }', async () => {
    globalThis.$fetch = vi.fn().mockResolvedValueOnce([
      { id: 'c1', category: 'cookies', label: 'Cookies', given_at: '2026-01-01', withdrawn_at: null },
    ])
    const store = useConsentsStore()
    await store.load()
    expect(store.items.length).toBe(1)

    globalThis.$fetch = vi.fn().mockResolvedValueOnce({
      items: [
        { id: 'c2', category: 'analytics', label: 'Analytics', given_at: '2026-02-01', withdrawn_at: null },
      ],
    })
    await store.load()
    expect(store.items[0].id).toBe('c2')
  })

  it("withdraw() rappelle load après succès", async () => {
    const fetch = vi.fn()
      .mockResolvedValueOnce([{ id: 'c1', category: 'cookies', label: 'Cookies', given_at: '2026-01-01', withdrawn_at: null }])
      .mockResolvedValueOnce(undefined) // POST withdraw
      .mockResolvedValueOnce([{ id: 'c1', category: 'cookies', label: 'Cookies', given_at: '2026-01-01', withdrawn_at: '2026-05-05' }])
    globalThis.$fetch = fetch
    const store = useConsentsStore()
    await store.load()
    await store.withdraw('c1')
    expect(fetch).toHaveBeenCalledTimes(3)
    expect(store.items[0].withdrawn_at).toBe('2026-05-05')
  })
})
