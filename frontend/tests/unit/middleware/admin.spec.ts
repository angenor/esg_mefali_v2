// F38 T045 — Tests middleware admin
import { describe, it, expect, beforeEach, vi } from 'vitest'

const abortMock = vi.fn((opts: unknown) => ({ aborted: opts }))
let user: { role: 'pme' | 'admin' } | null = null

;(globalThis as { defineNuxtRouteMiddleware?: unknown }).defineNuxtRouteMiddleware = (
  fn: (...a: unknown[]) => unknown
) => fn
;(globalThis as { abortNavigation?: unknown }).abortNavigation = abortMock
;(globalThis as { useAuthStore?: unknown }).useAuthStore = () => ({ user })

const middleware = (await import('../../../app/middleware/admin')).default as () => unknown

describe('middleware admin', () => {
  beforeEach(() => {
    abortMock.mockClear()
  })

  it('admin → laisse passer', () => {
    user = { role: 'admin' }
    const r = middleware()
    expect(abortMock).not.toHaveBeenCalled()
    expect(r).toBeUndefined()
  })

  it('PME → abortNavigation 404', () => {
    user = { role: 'pme' }
    middleware()
    expect(abortMock).toHaveBeenCalledWith(
      expect.objectContaining({ statusCode: 404 })
    )
  })

  it('anonyme → abortNavigation 404', () => {
    user = null
    middleware()
    expect(abortMock).toHaveBeenCalled()
  })
})
