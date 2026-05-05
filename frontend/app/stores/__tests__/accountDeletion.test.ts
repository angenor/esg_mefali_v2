// F52 US2 — Store accountDeletion (load + create + cancel).
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAccountDeletionStore } from '../accountDeletion'

declare global {
  // eslint-disable-next-line no-var
  var $fetch: unknown
  // eslint-disable-next-line no-var
  var useRuntimeConfig: unknown
}

const REQUEST = {
  id: 'r1',
  status: 'pending' as const,
  requested_at: '2026-05-01T00:00:00Z',
  scheduled_for: '2026-05-31T00:00:00Z',
  can_cancel: true,
}

describe('useAccountDeletionStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    globalThis.useRuntimeConfig = () => ({ public: { apiBase: 'http://api' } })
    globalThis.useCsrf = () => ({ withCsrf: () => ({}) })
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('load() — pas de demande active', async () => {
    globalThis.$fetch = vi.fn().mockResolvedValue({ request: null })
    const store = useAccountDeletionStore()
    await store.load()
    expect(store.request).toBeNull()
    expect(store.isPending).toBe(false)
  })

  it('create() positionne la demande pending', async () => {
    globalThis.$fetch = vi.fn().mockResolvedValue({ request: REQUEST })
    const store = useAccountDeletionStore()
    await store.create({ confirmation_text: 'ACME SARL' })
    expect(store.request?.id).toBe('r1')
    expect(store.isPending).toBe(true)
  })

  it("cancel() purge la demande", async () => {
    globalThis.$fetch = vi.fn()
      .mockResolvedValueOnce({ request: REQUEST }) // create
      .mockResolvedValueOnce(undefined) // delete
    const store = useAccountDeletionStore()
    await store.create({ confirmation_text: 'ACME SARL' })
    await store.cancel()
    expect(store.request).toBeNull()
  })

  it("create() rejette propage l'erreur", async () => {
    globalThis.$fetch = vi.fn().mockRejectedValue(new Error('confirmation_mismatch'))
    const store = useAccountDeletionStore()
    await expect(store.create({ confirmation_text: 'WRONG' })).rejects.toThrow()
    expect(store.error).toBe('confirmation_mismatch')
  })
})
