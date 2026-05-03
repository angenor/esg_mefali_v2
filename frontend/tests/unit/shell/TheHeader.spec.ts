// F38 T019 — Tests TheHeader
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { nextTick } from 'vue'

let mqlMatches = false
const mqlListeners = new Set<(e: MediaQueryListEvent) => void>()

beforeEach(() => {
  setActivePinia(createPinia())
  mqlMatches = false
  mqlListeners.clear()
  ;(window as { matchMedia?: unknown }).matchMedia = vi.fn().mockImplementation(() => ({
    matches: mqlMatches,
    addEventListener: (_: string, fn: (e: MediaQueryListEvent) => void) => {
      mqlListeners.add(fn)
    },
    removeEventListener: (_: string, fn: (e: MediaQueryListEvent) => void) => {
      mqlListeners.delete(fn)
    },
  }))
})

import TheHeader from '../../../app/components/shell/TheHeader.vue'
import { useAuthStore } from '../../../app/stores/auth'

describe('TheHeader', () => {
  it('affiche raison sociale depuis le store', async () => {
    const auth = useAuthStore()
    auth.setUser({
      user_id: 'u',
      account_id: 'a',
      role: 'pme',
      email: 'a@b.fr',
      raison_sociale: 'Acme SARL',
      created_at: '2026-01-01T00:00:00Z',
      last_login_at: null,
    })
    const w = mount(TheHeader)
    expect(w.find('[data-testid="header-tenant"]').text()).toBe('Acme SARL')
  })

  it('fallback email si raison_sociale absente', async () => {
    const auth = useAuthStore()
    auth.setUser({
      user_id: 'u',
      account_id: 'a',
      role: 'pme',
      email: 'a@b.fr',
      created_at: '2026-01-01T00:00:00Z',
      last_login_at: null,
    })
    const w = mount(TheHeader)
    expect(w.find('[data-testid="header-tenant"]').text()).toBe('a@b.fr')
  })

  it('hauteur fixe 56 px', () => {
    const w = mount(TheHeader)
    expect(w.find('header').attributes('style')).toContain('56px')
  })

  it('hamburger émis < 1024 px', async () => {
    mqlMatches = true
    const w = mount(TheHeader)
    await nextTick()
    const btn = w.find('[data-testid="header-hamburger"]')
    expect(btn.exists()).toBe(true)
    await btn.trigger('click')
    expect(w.emitted('toggle-drawer')).toBeTruthy()
  })

  it('pas de hamburger ≥ 1024 px', async () => {
    mqlMatches = false
    const w = mount(TheHeader)
    await nextTick()
    expect(w.find('[data-testid="header-hamburger"]').exists()).toBe(false)
  })
})
