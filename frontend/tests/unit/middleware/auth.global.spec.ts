// F38 T044 — Tests middleware auth.global
import { describe, it, expect, beforeEach, vi } from 'vitest'

const navigateMock = vi.fn((arg: unknown) => arg)
const getMeMock = vi.fn(async () => null as { user_id: string } | null)
let user: { role: 'pme' | 'admin' } | null = null

;(globalThis as { defineNuxtRouteMiddleware?: unknown }).defineNuxtRouteMiddleware = (
  fn: (...a: unknown[]) => unknown
) => fn
;(globalThis as { navigateTo?: unknown }).navigateTo = navigateMock
;(globalThis as { useAuthStore?: unknown }).useAuthStore = () => ({ user })
;(globalThis as { useAuth?: unknown }).useAuth = () => ({ getMe: getMeMock })
;(globalThis as { import?: unknown }).import = { meta: { server: false } }
// Vitest exposes import.meta — we toggle via global
Object.defineProperty(globalThis, 'import', {
  configurable: true,
  value: { meta: { server: false, client: true } },
})

const middleware = (await import('../../../app/middleware/auth.global')).default as (
  to: { path: string; fullPath: string; meta?: Record<string, unknown> }
) => Promise<unknown>

describe('middleware auth.global', () => {
  beforeEach(() => {
    navigateMock.mockClear()
    getMeMock.mockReset()
    user = null
  })

  it('anonyme + route privée → /login?redirect=…', async () => {
    user = null
    getMeMock.mockResolvedValueOnce(null)
    await middleware({ path: '/dashboard', fullPath: '/dashboard', meta: {} })
    expect(navigateMock).toHaveBeenCalledWith({
      path: '/login',
      query: { redirect: '/dashboard' },
    })
  })

  it('anonyme + meta.public=true → laisse passer', async () => {
    user = null
    const result = await middleware({
      path: '/verify/abc',
      fullPath: '/verify/abc',
      meta: { public: true },
    })
    expect(navigateMock).not.toHaveBeenCalled()
    expect(result).toBeUndefined()
  })

  it('authentifié + /login → /dashboard', async () => {
    user = { role: 'pme' }
    await middleware({ path: '/login', fullPath: '/login', meta: { public: true } })
    expect(navigateMock).toHaveBeenCalledWith('/dashboard')
  })

  it('authentifié + route privée → laisse passer', async () => {
    user = { role: 'pme' }
    const result = await middleware({ path: '/scoring', fullPath: '/scoring', meta: {} })
    expect(navigateMock).not.toHaveBeenCalled()
    expect(result).toBeUndefined()
  })
})
