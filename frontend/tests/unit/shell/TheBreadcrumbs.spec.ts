// F38 T066 — Tests TheBreadcrumbs
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h, computed } from 'vue'

let crumbs: Array<{ label: string; to?: string }> = []
vi.mock('~/composables/useBreadcrumbs', () => ({
  useBreadcrumbs: () => computed(() => crumbs),
}))

const NuxtLinkStub = defineComponent({
  props: ['to'],
  setup(p, { slots, attrs }) {
    return () =>
      h('a', { ...attrs, href: typeof p.to === 'string' ? p.to : '#' }, slots.default?.())
  },
})

import TheBreadcrumbs from '../../../app/components/shell/TheBreadcrumbs.vue'

describe('TheBreadcrumbs', () => {
  it('rend liens sauf pour le dernier segment', () => {
    crumbs = [
      { label: 'Accueil', to: '/dashboard' },
      { label: 'Projets', to: '/projets' },
      { label: 'Détail', to: '/projets/abc' },
    ]
    const w = mount(TheBreadcrumbs, { global: { stubs: { NuxtLink: NuxtLinkStub } } })
    const links = w.findAll('a')
    expect(links.length).toBe(2)
    const last = w.find('[aria-current="page"]')
    expect(last.exists()).toBe(true)
    expect(last.text()).toBe('Détail')
  })

  it('aucun rendu si crumbs vide', () => {
    crumbs = []
    const w = mount(TheBreadcrumbs, { global: { stubs: { NuxtLink: NuxtLinkStub } } })
    expect(w.find('nav').exists()).toBe(false)
  })

  it('tronque les libellés > 40 caractères', () => {
    crumbs = [
      { label: 'A'.repeat(80), to: '/x' },
      { label: 'fin' },
    ]
    const w = mount(TheBreadcrumbs, { global: { stubs: { NuxtLink: NuxtLinkStub } } })
    expect(w.find('a').text().length).toBeLessThanOrEqual(40)
    expect(w.find('a').text()).toContain('…')
  })
})
