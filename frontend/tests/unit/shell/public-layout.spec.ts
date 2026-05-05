// F38 T026 — Tests layout public
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'

import PublicLayout from '../../../app/layouts/public.vue'

const NuxtLinkStub = defineComponent({
  props: ['to'],
  setup(_, { slots, attrs }) {
    return () => h('a', { ...attrs, href: typeof _.to === 'string' ? _.to : '#' }, slots.default?.())
  },
})

describe('layouts/public.vue', () => {
  it('header minimal logo seulement, footer mentions', () => {
    const w = mount(PublicLayout, {
      slots: { default: '<p data-testid="content">Hello</p>' },
      global: { stubs: { NuxtLink: NuxtLinkStub } },
    })
    expect(w.find('[data-testid="public-logo"]').text()).toContain('ESG Mefali')
    const footer = w.find('[data-testid="public-footer"]')
    expect(footer.exists()).toBe(true)
    expect(footer.html()).toContain('Mentions légales')
    expect(footer.html()).toContain('Confidentialité')
    expect(footer.html()).toContain('Contact')
    expect(w.html()).toContain('Hello')
  })

  it("ne contient ni sidebar ni cloche", () => {
    const w = mount(PublicLayout, {
      global: { stubs: { NuxtLink: NuxtLinkStub } },
    })
    expect(w.find('[data-testid="the-sidebar"]').exists()).toBe(false)
    expect(w.find('nav[aria-label="Navigation principale"]').exists()).toBe(false)
  })
})
