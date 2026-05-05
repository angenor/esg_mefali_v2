// F52 US2 — Store sessions (load + revoke).
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useSessionsStore } from '../sessions'

declare global {
  // eslint-disable-next-line no-var
  var $fetch: unknown
  // eslint-disable-next-line no-var
  var useRuntimeConfig: unknown
}

const SESSIONS = {
  items: [
    {
      id: 's1',
      device_label: 'Mac',
      ip_country: 'CI',
      user_agent_summary: 'Safari',
      created_at: '2026-05-01',
      last_seen_at: '2026-05-05',
      is_current: true,
    },
    {
      id: 's2',
      device_label: 'PC',
      ip_country: 'FR',
      user_agent_summary: 'Chrome',
      created_at: '2026-05-02',
      last_seen_at: '2026-05-04',
      is_current: false,
    },
  ],
}

describe('useSessionsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    globalThis.useRuntimeConfig = () => ({ public: { apiBase: 'http://api' } })
    globalThis.useCsrf = () => ({ withCsrf: () => ({}) })
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('load() peuple items', async () => {
    globalThis.$fetch = vi.fn().mockResolvedValue(SESSIONS)
    const store = useSessionsStore()
    await store.load()
    expect(store.items.length).toBe(2)
    expect(store.items[0].is_current).toBe(true)
  })

  it("revoke() retire la session de la liste", async () => {
    globalThis.$fetch = vi.fn()
      .mockResolvedValueOnce(SESSIONS)
      .mockResolvedValueOnce(undefined)
    const store = useSessionsStore()
    await store.load()
    await store.revoke('s2')
    expect(store.items.find((s) => s.id === 's2')).toBeUndefined()
  })
})
