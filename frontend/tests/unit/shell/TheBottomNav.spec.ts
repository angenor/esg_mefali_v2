// F38 T039 — Tests TheBottomNav
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'

let routePath = '/dashboard'
vi.mock('vue-router', async () => {
  const actual = await vi.importActual<typeof import('vue-router')>('vue-router')
  return { ...actual, useRoute: () => ({ path: routePath }) }
})

const NuxtLinkStub = defineComponent({
  props: ['to'],
  setup(p, { slots, attrs }) {
    return () => h('a', { ...attrs, href: typeof p.to === 'string' ? p.to : '#' }, slots.default?.())
  },
})

import TheBottomNav from '../../../app/components/shell/TheBottomNav.vue'

describe('TheBottomNav', () => {
  it('rend nav[aria-label="Navigation rapide"] avec 4 cibles', () => {
    routePath = '/dashboard'
    const w = mount(TheBottomNav, { global: { stubs: { NuxtLink: NuxtLinkStub } } })
    const nav = w.find('nav[aria-label="Navigation rapide"]')
    expect(nav.exists()).toBe(true)
    const cells = w.findAll('[data-testid^="bottom-nav-"]')
    expect(cells.length).toBe(4)
  })

  it('chaque cible a une taille minimum 48 px', () => {
    const w = mount(TheBottomNav, { global: { stubs: { NuxtLink: NuxtLinkStub } } })
    const cells = w.findAll('[data-testid^="bottom-nav-"]')
    for (const cell of cells) {
      const style = cell.attributes('style') ?? ''
      expect(style).toContain('48px')
    }
  })

  it('item dashboard actif quand route.path = /dashboard', () => {
    routePath = '/dashboard'
    const w = mount(TheBottomNav, { global: { stubs: { NuxtLink: NuxtLinkStub } } })
    const cell = w.find('[data-testid="bottom-nav-dashboard"]')
    expect(cell.attributes('data-active')).toBe('true')
  })

  it('le bouton Plus émet open-more', async () => {
    const w = mount(TheBottomNav, { global: { stubs: { NuxtLink: NuxtLinkStub } } })
    await w.find('[data-testid="bottom-nav-more"]').trigger('click')
    expect(w.emitted('open-more')).toBeTruthy()
  })

  it('a la classe lg:hidden (rendu < 1024 px uniquement)', () => {
    const w = mount(TheBottomNav, { global: { stubs: { NuxtLink: NuxtLinkStub } } })
    expect(w.find('nav').classes()).toContain('lg:hidden')
  })
})
