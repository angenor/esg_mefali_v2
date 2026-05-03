// F38 T018 — Tests TheSidebar
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { defineComponent, h } from 'vue'

const NuxtLinkStub = defineComponent({
  props: ['to'],
  setup(_, { slots, attrs }) {
    return () => h('a', { ...attrs, href: typeof _.to === 'string' ? _.to : '#' }, slots.default?.())
  },
})

const UiBadgeStub = defineComponent({
  setup(_, { slots, attrs }) {
    return () => h('span', { ...attrs, 'data-testid': 'badge' }, slots.default?.())
  },
})
const UiTooltipStub = defineComponent({
  props: ['label'],
  setup(p) {
    return () => h('span', { 'data-tooltip': p.label }, p.label)
  },
})

let routePath = '/dashboard'
vi.mock('vue-router', async () => {
  const actual = await vi.importActual<typeof import('vue-router')>('vue-router')
  return { ...actual, useRoute: () => ({ path: routePath }) }
})

;(globalThis as { useNotificationsStore?: unknown }).useNotificationsStore = () => ({
  unreadCount: 3,
})

import TheSidebar from '../../../app/components/shell/TheSidebar.vue'

const stubs = { NuxtLink: NuxtLinkStub, UiBadge: UiBadgeStub, UiTooltip: UiTooltipStub }

describe('TheSidebar', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    routePath = '/dashboard'
  })

  it("nav avec aria-label='Navigation principale' et 11+ items", () => {
    const w = mount(TheSidebar, { global: { stubs } })
    const nav = w.find('nav[aria-label="Navigation principale"]')
    expect(nav.exists()).toBe(true)
    const links = w.findAll('a')
    expect(links.length).toBeGreaterThanOrEqual(11)
  })

  it("item dashboard est actif quand route.path = /dashboard", () => {
    routePath = '/dashboard'
    const w = mount(TheSidebar, { global: { stubs } })
    const active = w.find('a[data-active="true"]')
    expect(active.exists()).toBe(true)
    expect(active.attributes('href')).toBe('/dashboard')
  })

  it('badge unread visible sur item Notifications', () => {
    const w = mount(TheSidebar, { global: { stubs } })
    expect(w.find('[data-testid="sidebar-unread-badge"]').text()).toContain('3')
  })

  it('mode collapsed masque les libellés', () => {
    const w = mount(TheSidebar, {
      props: { collapsed: true },
      global: { stubs },
    })
    expect(w.classes()).toContain('w-16')
  })

  it('toggle émet update:collapsed', async () => {
    const w = mount(TheSidebar, { global: { stubs } })
    await w.find('button[aria-label*="Replier"]').trigger('click')
    expect(w.emitted('update:collapsed')).toEqual([[true]])
  })
})
