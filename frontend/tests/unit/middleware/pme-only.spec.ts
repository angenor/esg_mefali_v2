// F38 T016 — Tests middleware pme-only
import { describe, it, expect, beforeEach, vi } from 'vitest'

const navigateMock = vi.fn((p: string) => ({ to: p }))
let user: { role: 'pme' | 'admin' } | null = null

;(globalThis as { defineNuxtRouteMiddleware?: unknown }).defineNuxtRouteMiddleware = (
  fn: (...a: unknown[]) => unknown
) => fn
;(globalThis as { navigateTo?: unknown }).navigateTo = navigateMock
;(globalThis as { useAuthStore?: unknown }).useAuthStore = () => ({ user })

const middleware = (await import('../../../app/middleware/pme-only')).default as () => unknown

describe('middleware pme-only', () => {
  beforeEach(() => {
    navigateMock.mockClear()
  })

  it('redirige les admins vers /admin', () => {
    user = { role: 'admin' }
    const result = middleware()
    expect(navigateMock).toHaveBeenCalledWith('/admin')
    expect(result).toEqual({ to: '/admin' })
  })

  it('laisse passer les PME', () => {
    user = { role: 'pme' }
    const result = middleware()
    expect(navigateMock).not.toHaveBeenCalled()
    expect(result).toBeUndefined()
  })

  it('laisse passer si pas d\'utilisateur (auth.global gère)', () => {
    user = null
    const result = middleware()
    expect(navigateMock).not.toHaveBeenCalled()
    expect(result).toBeUndefined()
  })
})
