// F38 T069 — Tests TheAvatarMenu
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'

const logoutMock = vi.fn(() => Promise.resolve())
const userState = {
  email: 'pme@example.com',
  raison_sociale: 'Acme PME',
  role: 'pme' as const,
}
vi.mock('~/stores/auth', () => ({
  useAuthStore: () => ({ user: userState, logout: logoutMock }),
}))

const NuxtLinkStub = defineComponent({
  props: ['to'],
  setup(p, { slots, attrs }) {
    return () =>
      h('a', { ...attrs, href: typeof p.to === 'string' ? p.to : '#' }, slots.default?.())
  },
})

import TheAvatarMenu from '../../../app/components/shell/TheAvatarMenu.vue'

describe('TheAvatarMenu', () => {
  beforeEach(() => {
    logoutMock.mockClear()
  })

  it('clic ouvre le popover', async () => {
    const w = mount(TheAvatarMenu, { global: { stubs: { NuxtLink: NuxtLinkStub } } })
    expect(w.find('[data-testid="avatar-popover"]').exists()).toBe(false)
    await w.find('[data-testid="avatar-button"]').trigger('click')
    expect(w.find('[data-testid="avatar-popover"]').exists()).toBe(true)
  })

  it('liens Mon compte / Paramètres / Déconnexion présents', async () => {
    const w = mount(TheAvatarMenu, { global: { stubs: { NuxtLink: NuxtLinkStub } } })
    await w.find('[data-testid="avatar-button"]').trigger('click')
    const text = w.find('[data-testid="avatar-popover"]').text()
    expect(text).toContain('Mon compte')
    expect(text).toContain('Paramètres')
    expect(text).toContain('Déconnexion')
  })

  it('sélecteur EN désactivé, FR sélectionné', async () => {
    const w = mount(TheAvatarMenu, { global: { stubs: { NuxtLink: NuxtLinkStub } } })
    await w.find('[data-testid="avatar-button"]').trigger('click')
    const select = w.find('[data-testid="avatar-lang-select"]')
    expect(select.attributes('disabled')).toBeDefined()
    const enOpt = select.findAll('option').find((o) => o.attributes('value') === 'en')
    expect(enOpt?.attributes('disabled')).toBeDefined()
  })

  it('clic Déconnexion appelle store.logout', async () => {
    const w = mount(TheAvatarMenu, { global: { stubs: { NuxtLink: NuxtLinkStub } } })
    await w.find('[data-testid="avatar-button"]').trigger('click')
    await w.find('[data-testid="avatar-logout"]').trigger('click')
    await flushPromises()
    expect(logoutMock).toHaveBeenCalled()
  })
})
