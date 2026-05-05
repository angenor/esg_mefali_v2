// F38 T025 — Tests layout auth
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'

import AuthLayout from '../../../app/layouts/auth.vue'

const NuxtLinkStub = defineComponent({
  props: ['to'],
  setup(_, { slots, attrs }) {
    return () => h('a', { ...attrs, href: typeof _.to === 'string' ? _.to : '#' }, slots.default?.())
  },
})

describe('layouts/auth.vue', () => {
  it('rend une grille 2 colonnes avec illustration et main', () => {
    const w = mount(AuthLayout, {
      slots: { default: '<p data-testid="form">Formulaire</p>' },
      global: { stubs: { NuxtLink: NuxtLinkStub } },
    })
    const root = w.find('[data-testid="layout-auth"]')
    expect(root.exists()).toBe(true)
    expect(root.classes()).toContain('lg:grid-cols-2')
    expect(w.find('[data-testid="auth-illustration"]').exists()).toBe(true)
    expect(w.find('[data-testid="auth-main"]').exists()).toBe(true)
    expect(w.html()).toContain('Formulaire')
  })

  it('illustration cachée < 1024 px (classe hidden lg:flex)', () => {
    const w = mount(AuthLayout, {
      global: { stubs: { NuxtLink: NuxtLinkStub } },
    })
    const aside = w.find('[data-testid="auth-illustration"]')
    expect(aside.classes()).toContain('hidden')
    expect(aside.classes()).toContain('lg:flex')
  })

  it('aucune sidebar/cloche', () => {
    const w = mount(AuthLayout, {
      global: { stubs: { NuxtLink: NuxtLinkStub } },
    })
    expect(w.find('[data-testid="the-sidebar"]').exists()).toBe(false)
    expect(w.find('nav[aria-label="Navigation principale"]').exists()).toBe(false)
  })
})
