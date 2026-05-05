// F38 T014 — Tests auth store (logout + isAuthenticated)
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

const fetchMock = vi.fn()
const navigateMock = vi.fn()
const resetMock = vi.fn()

;(globalThis as { $fetch?: unknown }).$fetch = fetchMock
;(globalThis as { useRuntimeConfig?: unknown }).useRuntimeConfig = () => ({
  public: { apiBase: 'http://api' },
})
;(globalThis as { useCsrf?: unknown }).useCsrf = () => ({
  withCsrf: () => ({ 'x-csrf-token': 'tok' }),
})
;(globalThis as { navigateTo?: unknown }).navigateTo = navigateMock
;(globalThis as { useNotificationsStore?: unknown }).useNotificationsStore = () => ({
  reset: resetMock,
})

import { useAuthStore } from '../../../app/stores/auth'

describe('useAuthStore (F38)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    fetchMock.mockReset()
    navigateMock.mockReset()
    resetMock.mockReset()
  })

  it('isAuthenticated true si user présent', () => {
    const s = useAuthStore()
    expect(s.isAuthenticated).toBe(false)
    s.setUser({
      user_id: 'u',
      account_id: 'a',
      role: 'pme',
      email: 'a@b.fr',
      created_at: '2026-01-01T00:00:00Z',
      last_login_at: null,
    })
    expect(s.isAuthenticated).toBe(true)
  })

  it('logout appelle endpoint, vide store, reset notifications, redirige', async () => {
    fetchMock.mockResolvedValueOnce(undefined)
    const s = useAuthStore()
    s.setUser({
      user_id: 'u',
      account_id: 'a',
      role: 'pme',
      email: 'a@b.fr',
      created_at: '2026-01-01T00:00:00Z',
      last_login_at: null,
    })
    await s.logout()
    expect(fetchMock).toHaveBeenCalledWith(
      'http://api/auth/logout',
      expect.objectContaining({ method: 'POST', credentials: 'include' })
    )
    expect(s.user).toBeNull()
    expect(resetMock).toHaveBeenCalled()
    expect(navigateMock).toHaveBeenCalledWith('/login')
  })

  it('logout absorbe une erreur réseau et nettoie quand même', async () => {
    fetchMock.mockRejectedValueOnce(new Error('net'))
    const s = useAuthStore()
    s.setUser({
      user_id: 'u',
      account_id: 'a',
      role: 'pme',
      email: 'a@b.fr',
      created_at: '2026-01-01T00:00:00Z',
      last_login_at: null,
    })
    await s.logout()
    expect(s.user).toBeNull()
    expect(navigateMock).toHaveBeenCalledWith('/login')
  })
})
