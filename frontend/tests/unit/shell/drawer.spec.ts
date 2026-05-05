// F38 T040 — Test du drawer mobile dans layouts/default.vue
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { defineComponent, h, nextTick } from 'vue'

const useHeadMock = vi.fn()
;(globalThis as { useHead?: unknown }).useHead = useHeadMock
;(globalThis as { useNotificationsStore?: unknown }).useNotificationsStore = () => ({
  unreadCount: 0,
  loadInitial: vi.fn(),
})
;(globalThis as { useAuthStore?: unknown }).useAuthStore = () => ({
  user: { email: 'a@b.c' },
  logout: vi.fn(),
})
;(globalThis as { definePageMeta?: unknown }).definePageMeta = vi.fn()
;(globalThis as { navigateTo?: unknown }).navigateTo = vi.fn(() => Promise.resolve())

let routePath = '/dashboard'
const afterEachCb: Array<(...args: unknown[]) => void> = []
vi.mock('vue-router', async () => {
  const actual = await vi.importActual<typeof import('vue-router')>('vue-router')
  return {
    ...actual,
    useRoute: () => ({ path: routePath, fullPath: routePath, meta: {} }),
    useRouter: () => ({
      afterEach: (cb: (...args: unknown[]) => void) => {
        afterEachCb.push(cb)
      },
    }),
  }
})

vi.mock('~/composables/useNotificationsStream', () => ({
  useNotificationsStream: () => ({ start: vi.fn(), stop: vi.fn(), isConnected: { value: false } }),
}))

vi.mock('~/composables/useCommandPalette', () => ({
  useCommandPalette: () => ({
    isOpen: { value: false },
    query: { value: '' },
    actions: { value: new Map() },
    results: { value: [] },
    open: vi.fn(),
    close: vi.fn(),
    toggle: vi.fn(),
    registerActions: vi.fn(),
    unregisterActions: vi.fn(),
  }),
}))

const stubAll = (name: string) =>
  defineComponent({
    name,
    inheritAttrs: false,
    setup(_, { slots }) {
      return () => h('div', { 'data-stub': name }, slots.default?.())
    },
  })

import DefaultLayout from '../../../app/layouts/default.vue'

describe('Default layout — drawer mobile', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    routePath = '/dashboard'
    afterEachCb.length = 0
  })

  it('drawer fermé par défaut puis s\'ouvre sur toggle-drawer', async () => {
    const w = mount(DefaultLayout, {
      global: {
        stubs: {
          TheSidebar: stubAll('TheSidebar'),
          TheHeader: defineComponent({
            emits: ['toggle-drawer'],
            setup(_, { emit, slots }) {
              return () =>
                h(
                  'div',
                  { 'data-stub': 'TheHeader' },
                  [
                    h('button', { 'data-testid': 'h-toggle', onClick: () => emit('toggle-drawer') }, 'm'),
                    slots.default?.(),
                  ]
                )
            },
          }),
          TheBottomNav: stubAll('TheBottomNav'),
          TheBreadcrumbs: stubAll('TheBreadcrumbs'),
          TheNotificationsBell: stubAll('TheNotificationsBell'),
          TheAvatarMenu: stubAll('TheAvatarMenu'),
          TheErrorBoundary: stubAll('TheErrorBoundary'),
          TheCommandPalette: stubAll('TheCommandPalette'),
          TheBottomNavMore: stubAll('TheBottomNavMore'),
          NuxtErrorBoundary: defineComponent({
            setup(_, { slots }) {
              return () => h('div', slots.default?.())
            },
          }),
          NuxtLink: defineComponent({
            props: ['to'],
            setup(p, { slots, attrs }) {
              return () =>
                h('a', { ...attrs, href: typeof p.to === 'string' ? p.to : '#' }, slots.default?.())
            },
          }),
          ClientOnly: defineComponent({
            setup(_, { slots }) {
              return () => h('div', slots.default?.())
            },
          }),
          Transition: defineComponent({
            setup(_, { slots }) {
              return () => h('div', slots.default?.())
            },
          }),
          Teleport: defineComponent({
            setup(_, { slots }) {
              return () => h('div', slots.default?.())
            },
          }),
        },
      },
    })

    expect(w.find('[data-testid="drawer-overlay"]').exists()).toBe(false)
    await w.find('[data-testid="h-toggle"]').trigger('click')
    await nextTick()
    expect(w.find('[data-testid="drawer-panel"]').exists()).toBe(true)

    // close on overlay click
    await w.find('[data-testid="drawer-overlay"]').trigger('click')
    await nextTick()
    expect(w.find('[data-testid="drawer-panel"]').exists()).toBe(false)

    // re-open then close on route change
    await w.find('[data-testid="h-toggle"]').trigger('click')
    await nextTick()
    expect(w.find('[data-testid="drawer-panel"]').exists()).toBe(true)
    afterEachCb.forEach((cb) => cb())
    await nextTick()
    expect(w.find('[data-testid="drawer-panel"]').exists()).toBe(false)

    // re-open then close with Esc
    await w.find('[data-testid="h-toggle"]').trigger('click')
    await nextTick()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await flushPromises()
    expect(w.find('[data-testid="drawer-panel"]').exists()).toBe(false)
    w.unmount()
  })
})
